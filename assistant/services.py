"""Conversation ownership, minimal audit, bounded snapshots, and authorization."""
import hashlib,json,time,uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction,IntegrityError
from django.utils import timezone
from django.utils.module_loading import import_string
from .models import Conversation,QueryResult,UsageBucket,QueryAudit
from .registry import registry,public_registry
from .plans import QueryProblem
from .engine import QueryEngine
from core.services import queryset_for
from .guidance import module_guidance


def rate_limit(user,kind,limit):
    minute=timezone.now().replace(second=0,microsecond=0)
    with transaction.atomic():
        bucket,_=UsageBucket.objects.get_or_create(user_id=user['id'],minute=minute,kind=kind)
        bucket=UsageBucket.objects.select_for_update().get(pk=bucket.pk)
        if bucket.count>=limit:
            from core.services import HTTPException
            raise HTTPException(429,'Too many assistant requests. Try again in a minute.')
        bucket.count+=1;bucket.save(update_fields=['count'])


def fingerprint(user):
    value={key:user.get(key) for key in ['id','role','student_id','staff_id','parent_id']}
    value['policy']=settings.ASSISTANT_POLICY_VERSION
    value['fields']={key:sorted(spec.fields) for key,spec in registry(user).items()}
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def owned_conversation(user,identifier=None):
    from core.services import HTTPException
    if identifier:
        try:item=Conversation.objects.get(pk=identifier,owner_id=user['id'])
        except (Conversation.DoesNotExist,ValueError):raise HTTPException(404,'Conversation not found.')
        if item.expires_at<=timezone.now():raise HTTPException(410,'This conversation expired. Start a new conversation.')
        return item
    return Conversation.objects.create(owner_id=user['id'],expires_at=timezone.now()+timedelta(hours=8))


def accessible_result(user,identifier):
    from core.services import HTTPException
    try:result=QueryResult.objects.select_related('conversation').get(pk=identifier,conversation__owner_id=user['id'])
    except (QueryResult.DoesNotExist,ValueError):raise HTTPException(404,'Result not found.')
    if result.expires_at<=timezone.now():raise HTTPException(410,'This result expired. Run the query again.')
    if result.access_fingerprint!=fingerprint(user):raise HTTPException(403,'Your access has changed. Run the query again.')
    resources=registry(user)
    for module,ids in result.source_refs.items():
        if module not in resources:raise HTTPException(403,'This result is no longer available to your account.')
        count=0
        for start in range(0,len(ids),500):count+=queryset_for(module,user).filter(pk__in=ids[start:start+500]).count()
        if count!=len(set(ids)):raise HTTPException(403,'Some source records are no longer available to your account. Run the query again.')
    return result


def present(result,page=1,page_size=25):
    data=dict(result.payload);rows=data.pop('rows',[])
    start=(page-1)*page_size
    return {**data,'result_id':str(result.pk),'conversation_id':str(result.conversation_id),'rows':rows[start:start+page_size],
            'stored_rows':len(rows),'page':page,'page_size':page_size,'next':page+1 if start+page_size<len(rows) else None,
            'expires_at':result.expires_at.isoformat()}


def chat(user,message,conversation_id=None,request_id=None):
    started=time.monotonic();rate_limit(user,'chat',settings.ASSISTANT_CHAT_RATE)
    conversation=owned_conversation(user,conversation_id)
    request_id=uuid.UUID(str(request_id)) if request_id else uuid.uuid4()
    existing=conversation.results.filter(request_id=request_id).first()
    if existing:return present(accessible_result(user,existing.pk))
    base_version=conversation.version
    raw={}
    try:
        planner=import_string(settings.ASSISTANT_PLANNER)()
        raw=planner.plan(message,conversation.context,registry(user))
        if raw.get('module_help'):
            if raw['module_help']=='all':
                return {'kind':'help','answer':'Choose a module to see the details and questions I can help with. I can read school records, summarize results, and generate PDF reports.',
                        'suggestions':['Help with '+spec.aliases[0] for spec in registry(user).values()],
                        'conversation_id':str(conversation.pk),'reportable':False,'mode':'local','rows':[],'columns':[],'summary':[]}
            guide=module_guidance(registry(user)[raw['module_help']])
            return {'kind':'help','answer':f'Here is what I can help you find in {guide["label"]}.','guidance':guide,
                    'conversation_id':str(conversation.pk),'reportable':False,'mode':'local','rows':[],'columns':[],'summary':[]}
        if raw.get('report_current'):
            last=conversation.results.first()
            if not last:raise QueryProblem('There is no reportable result yet. Ask a data question first.')
            last=accessible_result(user,last.pk)
            from .reports import create_report
            report=create_report(user,last.pk,'detailed')
            return {**present(last),'report_requested':True,'report':report}
        answer=QueryEngine(user).execute(raw)
        plan=answer.pop('plan');refs=answer.pop('source_refs');student_ids=answer.pop('student_ids')
        answer['guidance']=module_guidance(registry(user)[plan['resource']])
        answer['mode']='local';answer['kind']='answer'
        if len(json.dumps(answer,ensure_ascii=False).encode('utf-8'))>settings.ASSISTANT_MAX_SNAPSHOT_BYTES:raise QueryProblem('The result is too large to store safely. Narrow the filters or request a summary.','limit')
        with transaction.atomic():
            locked=Conversation.objects.select_for_update().get(pk=conversation.pk)
            if locked.version!=base_version:
                from core.services import HTTPException
                raise HTTPException(409,'Another question changed this conversation. Send your follow-up again.')
            result=QueryResult.objects.create(conversation=locked,request_id=request_id,plan=plan,payload=answer,source_refs=refs,
                access_fingerprint=fingerprint(user),expires_at=timezone.now()+timedelta(seconds=settings.ASSISTANT_RESULT_TTL_SECONDS))
            locked.context={'plan':plan,'student_ids':student_ids};locked.version+=1;locked.expires_at=timezone.now()+timedelta(hours=8)
            locked.save(update_fields=['context','version','expires_at','updated_at'])
        QueryAudit.objects.create(user_id=user['id'],resource=plan['resource'],operation=plan['operation'],outcome='success',row_count=answer['total_rows'],elapsed_ms=int((time.monotonic()-started)*1000))
        return present(result)
    except QueryProblem as exc:
        QueryAudit.objects.create(user_id=user['id'],resource='',operation='',outcome=exc.kind,elapsed_ms=int((time.monotonic()-started)*1000))
        spec=registry(user).get(getattr(exc,'resource',None) or (raw.get('resource') if exc.kind!='forbidden' else None))
        return {'kind':exc.kind,'answer':exc.message,'guidance':module_guidance(spec) if spec else None,'conversation_id':str(conversation.pk),'reportable':False,'mode':'local','rows':[],'columns':[],'summary':[]}
