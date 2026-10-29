"""Bounded, read-only ORM execution. Values from records remain plain data."""
import calendar
import json
import re
import time as clock
from contextlib import contextmanager
from copy import deepcopy
from datetime import date,datetime,timedelta
from decimal import Decimal
from django.apps import apps
from django.conf import settings
from django.db import connection,transaction,OperationalError,models
from django.db.models import Avg,Count,Sum,F,Q,Value,DecimalField,FloatField,ExpressionWrapper,OuterRef,Subquery
from django.db.models.functions import Coalesce,TruncMonth
from django.utils import timezone
from core.registry import MODULES
from core.services import queryset_for
from .registry import registry,scoped
from .plans import QueryProblem,validate_plan


def plain(value):
    if isinstance(value,Decimal):return format(value.quantize(Decimal('.01')),'.2f')
    if isinstance(value,(date,datetime)):return value.isoformat()
    if isinstance(value,dict):return {str(key):plain(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [plain(item) for item in value]
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)


def period_bounds(plan):
    today=timezone.localdate();period=plan.get('period','all');year_label=None
    if period=='all':return None,None,None
    if period=='today':return today,today,None
    if period=='yesterday':return today-timedelta(days=1),today-timedelta(days=1),None
    if period=='this_month':return today.replace(day=1),today,None
    if period=='last_month':
        end=today.replace(day=1)-timedelta(days=1);return end.replace(day=1),end,None
    if period=='this_year':return today.replace(month=1,day=1),today,None
    if period=='custom':return date.fromisoformat(plan['start']),date.fromisoformat(plan['end']),None
    Year=apps.get_model('academics.AcademicYear')
    if plan.get('academic_year'):
        name=plan['academic_year'].replace('–','-')
        candidates=list(Year.objects.all())
        current=next((item for item in candidates if item.name.replace('–','-').replace('/','-')==name),None)
    else:current=Year.objects.filter(start_date__lte=today,end_date__gte=today).order_by('-start_date').first()
    if not current:raise QueryProblem('No matching academic year is configured. Select a configured academic year or give an explicit date range.','unavailable')
    if period=='previous_academic_year':
        current=Year.objects.filter(end_date__lt=current.start_date).order_by('-end_date').first()
        if not current:raise QueryProblem('The previous academic year is not configured in the ERP.','unavailable')
    return current.start_date,current.end_date,current.name


@contextmanager
def query_budget():
    seconds=settings.ASSISTANT_QUERY_TIMEOUT_SECONDS
    deadline=clock.monotonic()+seconds
    connection.ensure_connection()
    try:
        with transaction.atomic():
            if connection.vendor=='sqlite':connection.connection.set_progress_handler(lambda:int(clock.monotonic()>deadline),1000)
            elif connection.vendor=='postgresql':
                with connection.cursor() as cursor:cursor.execute("SELECT set_config('statement_timeout', %s, true)",[str(int(seconds*1000))])
            yield deadline
    except OperationalError as exc:
        if 'interrupt' in str(exc).lower() or 'timeout' in str(exc).lower() or 'canceling statement' in str(exc).lower():
            raise QueryProblem('The query exceeded the time limit. Narrow the class, date range, or filters.','limit') from exc
        raise
    finally:
        if connection.vendor=='sqlite' and connection.connection:connection.connection.set_progress_handler(None,0)


class QueryEngine:
    def __init__(self,user):
        self.user=user;self.resources=registry(user);self.refs={};self.labels={};self.notes=[];self.filter_labels=[];self.deadline=None
        self.related_modules={value['model'].lower():key for key,value in MODULES.items()}

    def checkpoint(self):
        if self.deadline and clock.monotonic()>self.deadline:raise QueryProblem('The query took too long. Please narrow the requested records.','limit')

    def capture(self,resource,qs):
        self.checkpoint()
        ids=list(qs.order_by().values_list('pk',flat=True).distinct()[:settings.ASSISTANT_MAX_SOURCE_ROWS+1])
        merged=set(self.refs.get(resource,[]))|set(ids)
        if len(merged)>settings.ASSISTANT_MAX_SOURCE_ROWS:raise QueryProblem('This query covers too many source records. Narrow the date range or class before reporting.','limit')
        self.refs[resource]=sorted(merged)

    def related(self,resource,pk):
        if not pk:return None
        key=(resource,pk)
        if key not in self.labels:
            if resource not in self.resources:self.labels[key]='Restricted record'
            else:
                obj=queryset_for(resource,self.user).filter(pk=pk).first()
                if obj:
                    self.refs.setdefault(resource,[])
                    if pk not in self.refs[resource]:self.refs[resource].append(pk)
                    self.labels[key]=getattr(obj,'name',None) or getattr(obj,'month',None) or f'{self.resources[resource].label} #{pk}'
                else:self.labels[key]='Restricted record'
        return self.labels[key]

    def scope(self,plan):
        spec=self.resources[plan['resource']];qs=scoped(spec.key,self.user)
        grade,section=plan.get('grade'),plan.get('section')
        if grade or section:
            if spec.class_path is None:raise QueryProblem(f'{spec.label} has no configured class relationship.')
            classes=scoped('classes',self.user)
            if grade:classes=classes.filter(name__iregex=rf'(class|grade|standard)\s*0?{grade}(\s|$)')
            if section:classes=classes.filter(name__iregex=rf'\b{re.escape(section)}$')
            if not classes.exists():raise QueryProblem(f'No permitted Class {grade or ""} Section {section or "(any)"} exists. Check the class and section.')
            self.capture('classes',classes)
            path=(spec.class_path+'__in') if spec.class_path else 'pk__in'
            qs=qs.filter(**{path:classes})
            self.filter_labels.append(f'Class {grade or "all"}, section {section or "all"}')
        start,end,academic=period_bounds(plan)
        if start:
            path=spec.date_path
            if not path:raise QueryProblem(f'{spec.label} does not have a configured reporting date. Remove the date filter or choose another module.')
            if path=='month':qs=qs.filter(month__gte=start.strftime('%Y-%m'),month__lte=end.strftime('%Y-%m'))
            elif path=='created_at':qs=qs.filter(created_at__date__gte=start,created_at__date__lte=end)
            else:qs=qs.filter(**{path+'__gte':start,path+'__lte':end})
            self.filter_labels.append(f'Date range: {start.isoformat()} to {end.isoformat()} ({path.replace("__"," / ")})')
        if academic:self.filter_labels.append(f'Academic year: {academic}')
        for item in plan['filters']:
            field=spec.fields[item['field']];op=item['op'];value=item['value'];lookup={'eq':'exact','contains':'icontains'}.get(op,op)
            try:
                if op=='isnull':parsed=value
                elif op=='in':parsed=[int(part) if isinstance(field,models.ForeignKey) else field.to_python(part) for part in value]
                elif isinstance(field,models.ForeignKey):parsed=int(value)
                else:parsed=field.to_python(value)
            except (ValueError,TypeError,__import__('django.core.exceptions',fromlist=['ValidationError']).ValidationError):raise QueryProblem(f'Invalid value for {field.verbose_name}.')
            qs=qs.filter(**{field.attname+'__'+lookup:parsed})
            self.filter_labels.append(f'{field.verbose_name}: {op} {str(value)[:120]}')
        if plan.get('student_ids'):
            names={field.name for field in spec.model._meta.fields}
            if spec.key=='students':qs=qs.filter(pk__in=plan['student_ids'])
            elif 'student' in names:qs=qs.filter(student_id__in=plan['student_ids'])
            elif spec.key=='payments':qs=qs.filter(invoice__student_id__in=plan['student_ids'])
            elif spec.key=='parents':qs=qs.filter(students__pk__in=plan['student_ids'])
            else:raise QueryProblem('This module cannot be restricted to the previous student set.')
            self.filter_labels.append('Student set from the previous result')
        return qs.distinct(),spec

    def metric(self,spec,plan):
        metric=plan.get('metric')
        if metric=='net_pay':return ExpressionWrapper(F('basic')+F('allowances')-F('deductions'),output_field=DecimalField(max_digits=18,decimal_places=2))
        return metric

    def execute(self,raw):
        plan=validate_plan(raw,self.resources)
        with query_budget() as deadline:
            self.deadline=deadline
            result=self.comparison(plan) if plan.get('compare') else self.run(plan)
            self.checkpoint()
        result.update(filters=list(dict.fromkeys(self.filter_labels)),notes=list(dict.fromkeys(self.notes)),as_of=timezone.now().isoformat(),plan=plan)
        result['rows']=plain(result.get('rows',[]));result['summary']=plain(result.get('summary',[]))
        result['source_refs']=self.refs
        result.setdefault('student_ids',[])
        result['reportable']=True
        return plain(result)

    def base_result(self,spec,title,answer,rows=None,columns=None,summary=None,total=None,student_ids=None):
        rows=rows or []
        return {'title':title,'answer':answer,'rows':rows,'columns':columns or [],'summary':summary or [],'total_rows':len(rows) if total is None else total,'student_ids':student_ids or []}

    def run(self,plan):
        qs,spec=self.scope(plan);operation=plan['operation']
        if operation=='incomplete':
            qs=qs.filter(Q(parent__isnull=True)|Q(email='')|Q(phone='')|Q(address='')|Q(admission_application__isnull=True))
            self.notes.append('Incomplete means missing guardian, email, phone, address, or linked admission application. Document uploads are not implemented.')
        if operation in ['exam_average','exam_failures','exam_ranking']:
            return self.exams(qs,spec,plan)
        if operation in ['attendance_rate','attendance_below']:return self.attendance(qs,spec,plan)
        if operation=='outstanding':return self.outstanding(qs,spec,plan)
        self.capture(spec.key,qs)
        if spec.key=='staff':self.notes.append('Staff records do not include employment status; figures describe registered staff, not verified active employment contracts.')
        count=qs.count()
        if operation=='count':return self.base_result(spec,f'{spec.label} count',f'{count:,} matching {spec.label.lower()} records.',summary=[{'label':'Records','value':count}],total=0)
        if operation=='net_pay':plan={**plan,'aggregation':'sum','metric':'net_pay'};operation='aggregate'
        if operation in ['aggregate','group']:
            agg=plan.get('aggregation','count');metric=self.metric(spec,plan)
            if agg!='count' and not metric:raise QueryProblem('Which numeric field should I total or average?')
            expression=Count('pk',distinct=True) if agg=='count' else (Sum(metric) if agg=='sum' else Avg(metric))
            if operation=='aggregate' or not plan['groups']:
                value=qs.aggregate(value=expression)['value']
                if value is None and agg=='sum':value=Decimal('0')
                if value is None:return self.base_result(spec,f'{spec.label} summary','No matching records are available for that average.',summary=[{'label':'Average '+plan.get('metric','value').replace('_',' '),'value':None},{'label':'Matching records','value':0}],total=0)
                field=plan.get('metric','records');unit='INR' if field in ['amount','salary','basic','allowances','deductions','net_pay'] else ''
                label=f'{"Average" if agg=="avg" else "Total"} {field.replace("_"," ")}'
                return self.base_result(spec,f'{spec.label} summary',f'{label}: {plain(value)}{(" "+unit) if unit else ""}, from {count:,} records.',summary=[{'label':label,'value':value,'unit':unit},{'label':'Matching records','value':count}],total=0)
            annotations={}
            for index,group in enumerate(plan['groups']):
                if group=='month':
                    if not spec.date_path:raise QueryProblem('Monthly grouping is unavailable for this resource.')
                    annotations[f'g{index}']=F('month') if spec.date_path=='month' else TruncMonth(spec.date_path)
                else:annotations[f'g{index}']=F(spec.groups[group])
            grouped=qs.order_by().annotate(**annotations).values(*annotations).annotate(value=expression).order_by(*annotations)
            rows=list(grouped[:settings.ASSISTANT_MAX_RESULT_ROWS+1]);total=grouped.count();rows=rows[:settings.ASSISTANT_MAX_RESULT_ROWS]
            columns=[{'key':f'g{i}','label':group.title(),'type':'text'} for i,group in enumerate(plan['groups'])]+[{'key':'value','label':agg.title()+' '+(plan.get('metric') or 'records'),'type':'number'}]
            return self.base_result(spec,f'{spec.label} grouped summary',f'{total:,} groups from {count:,} matching records.',rows,columns,[{'label':'Matching records','value':count}],total)
        # Lists are bounded, while total_rows always describes the complete filtered set.
        display=plan.get('columns') or spec.display
        columns=[{'key':name,'label':str(spec.fields[name].verbose_name),'type':'money' if isinstance(spec.fields[name],models.DecimalField) else 'text'} for name in display]
        requested=plan.get('limit',settings.ASSISTANT_MAX_RESULT_ROWS)
        cap=min(requested,settings.ASSISTANT_MAX_RESULT_ROWS)
        rows=[];student_ids=[];row_bytes=0
        for instance in qs.order_by('pk')[:cap]:
            self.checkpoint();row={}
            for name in display:
                field=spec.fields[name];value=getattr(instance,field.attname)
                if isinstance(field,models.ForeignKey):
                    target=self.related_modules.get(field.related_model._meta.label_lower)
                    value=self.related(target,value) if target else 'Restricted record'
                row[name]=plain(value)
            row_bytes+=len(json.dumps(row,ensure_ascii=False).encode('utf-8'))
            if row_bytes>settings.ASSISTANT_MAX_SNAPSHOT_BYTES:raise QueryProblem('The result text is too large. Narrow the records or request a count or grouped summary.','limit')
            rows.append(row)
            if spec.key=='students':student_ids.append(instance.pk)
            elif hasattr(instance,'student_id'):student_ids.append(instance.student_id)
        if count>cap:self.notes.append(f'Detailed output is limited to the first {cap:,} of {count:,} records. Totals refer to the full filtered set; narrow the filters for a complete detailed report.')
        answer=f'Found {count:,} matching {spec.label.lower()} records.' if count else 'No matching records were found for these filters.'
        return self.base_result(spec,f'{spec.label} report',answer,rows,columns,[{'label':'Matching records','value':count}],count,student_ids if count<=cap else [])

    def attendance(self,qs,spec,plan):
        self.capture('attendance',qs)
        self.notes.append('Attendance percentage = Present / recorded attendance. Late, Absent, and Excused remain in the denominator. Students without records are not assigned 0% attendance.')
        count=qs.count();present=qs.filter(status='Present').count()
        percent=(Decimal(present)*100/count).quantize(Decimal('.01')) if count else None
        summary=[{'label':'Recorded attendance','value':count},{'label':'Present','value':present},{'label':'Attendance','value':percent,'unit':'%'}]
        if plan['operation']=='attendance_below':
            grouped=qs.order_by().values('student_id','student__name','student__school_class__name').annotate(recorded=Count('pk',distinct=True),present=Count('pk',filter=Q(status='Present'),distinct=True))
            threshold=Decimal(str(plan.get('threshold',75)));rows=[];student_ids=[]
            for row in grouped:
                self.checkpoint();rate=(Decimal(row['present'])*100/row['recorded']).quantize(Decimal('.01'))
                if rate<threshold:
                    student_ids.append(row['student_id']);rows.append({'student':row['student__name'],'class':row['student__school_class__name'],'recorded':row['recorded'],'present':row['present'],'attendance':rate})
            self.capture('students',scoped('students',self.user).filter(pk__in=student_ids))
            total=len(rows)
            if total>settings.ASSISTANT_MAX_RESULT_ROWS:self.notes.append('The detailed student list is truncated; narrow the class filters.')
            return self.base_result(spec,'Students below attendance threshold',f'{total:,} students with recorded attendance are below {threshold}%.',rows[:settings.ASSISTANT_MAX_RESULT_ROWS],[{'key':key,'label':label,'type':'number' if key in ['recorded','present','attendance'] else 'text'} for key,label in [('student','Student'),('class','Class'),('recorded','Recorded'),('present','Present'),('attendance','Attendance %')]],summary,total,student_ids if total<=settings.ASSISTANT_MAX_RESULT_ROWS else [])
        if plan['groups']:
            annotations={}
            for index,group in enumerate(plan['groups']):
                annotations[f'g{index}']=TruncMonth('date') if group=='month' else F(spec.groups[group])
            grouped=qs.order_by().annotate(**annotations).values(*annotations).annotate(recorded=Count('pk',distinct=True),present=Count('pk',filter=Q(status='Present'),distinct=True)).order_by(*annotations)
            rows=list(grouped[:settings.ASSISTANT_MAX_RESULT_ROWS])
            for row in rows:row['attendance']=(Decimal(row['present'])*100/row['recorded']).quantize(Decimal('.01')) if row['recorded'] else None
            return self.base_result(spec,'Grouped attendance percentages',f'Attendance percentages for {grouped.count()} groups with recorded attendance.',rows,[{'key':f'g{i}','label':group.title(),'type':'text'} for i,group in enumerate(plan['groups'])]+[{'key':'recorded','label':'Recorded','type':'number'},{'key':'present','label':'Present','type':'number'},{'key':'attendance','label':'Attendance %','type':'number'}],summary,grouped.count())
        return self.base_result(spec,'Attendance summary',f'Attendance is {percent}% from {present:,} present of {count:,} recorded entries.' if count else 'No attendance is recorded for this period; a percentage is unavailable.',summary=summary,total=0)

    def outstanding(self,qs,spec,plan):
        receipts=scoped('payments',self.user).filter(invoice_id__in=qs.values('pk'))
        self.capture('fees',qs);self.capture('payments',receipts)
        paid=receipts.filter(invoice_id=OuterRef('pk')).order_by().values('invoice_id').annotate(value=Sum('amount')).values('value')
        balance_qs=qs.annotate(received=Coalesce(Subquery(paid,output_field=DecimalField(max_digits=18,decimal_places=2)),Value(Decimal('0')))).annotate(balance=F('amount')-F('received')).filter(balance__gt=0)
        total=balance_qs.aggregate(value=Sum('balance'))['value'] or Decimal('0')
        grouped=balance_qs.order_by().values('student_id','student__name','student__roll','student__school_class__name').annotate(balance_total=Sum('balance'),invoices=Count('pk',distinct=True)).order_by('-balance_total','student_id')
        count=grouped.count();rows=[];student_ids=[]
        for row in grouped[:settings.ASSISTANT_MAX_RESULT_ROWS]:
            student_ids.append(row['student_id']);rows.append({'student':row['student__name'],'admission':row['student__roll'],'class':row['student__school_class__name'],'invoices':row['invoices'],'outstanding':row['balance_total']})
        self.capture('students',scoped('students',self.user).filter(pk__in=student_ids))
        self.notes.append('Outstanding balances use recorded manual receipts. Unpaid future-due invoices are included unless a due-date filter is specified. A period filters invoice due dates, not receipt dates.')
        if count>len(rows):self.notes.append(f'Details show the first {len(rows)} students; totals cover all {count} matching students.')
        return self.base_result(spec,'Students with outstanding fees',f'{count:,} students have outstanding balances totaling INR {plain(total)}.',rows,[{'key':key,'label':label,'type':'money' if key=='outstanding' else 'text'} for key,label in [('student','Student'),('admission','Admission no.'),('class','Class'),('invoices','Invoices'),('outstanding','Outstanding (INR)')]],[{'label':'Students with outstanding fees','value':count},{'label':'Outstanding fees','value':total,'unit':'INR'}],count,student_ids if count<=len(rows) else [])

    def exams(self,qs,spec,plan):
        if plan.get('latest'):
            latest=qs.filter(exam__date__lte=timezone.localdate()).order_by('-exam__date').values_list('exam__date',flat=True).first()
            if latest:
                qs=qs.filter(exam__date=latest)
                if qs.values('exam_id').distinct().count()>1:raise QueryProblem('Multiple examinations share the latest recorded date. Specify a class or subject so the ranking is meaningful.')
                self.filter_labels.append(f'Latest completed examination date: {latest}')
        if plan['operation']=='exam_failures':qs=qs.filter(marks__lt=F('exam__pass_marks'))
        self.capture('results',qs)
        count=qs.count()
        if not count:return self.base_result(spec,'Examination analysis','No recorded marks match these filters; an average or ranking is unavailable.',summary=[{'label':'Matching result records','value':0}],total=0)
        if plan['operation']=='exam_average':
            groups=plan['groups'] or ['class'];annotations={f'g{i}':F(spec.groups[group]) for i,group in enumerate(groups)}
            grouped=qs.order_by().annotate(**annotations).values(*annotations).annotate(average_marks=Avg('marks'),average_percentage=Avg(ExpressionWrapper(F('marks')*100.0/F('exam__max_marks'),output_field=FloatField())),records=Count('pk',distinct=True)).order_by(*annotations)
            rows=list(grouped[:settings.ASSISTANT_MAX_RESULT_ROWS]);total=grouped.count()
            for row in rows:row['average_percentage']=format(row['average_percentage'],'.2f');row['average_marks']=format(row['average_marks'],'.2f')
            self.notes.append('Average marks are raw marks; average percentage normalizes each result against its exam maximum. Groups without recorded marks are not treated as zero.')
            return self.base_result(spec,'Academic performance by group',f'{total} groups summarized from {count} recorded results.',rows,[{'key':f'g{i}','label':group.title(),'type':'text'} for i,group in enumerate(groups)]+[{'key':'average_marks','label':'Average marks','type':'number'},{'key':'average_percentage','label':'Average %','type':'number'},{'key':'records','label':'Results','type':'number'}],[{'label':'Recorded results','value':count}],total)
        ranked=qs.select_related('student','exam','exam__school_class','exam__subject').annotate(percentage=ExpressionWrapper(F('marks')*100.0/F('exam__max_marks'),output_field=FloatField()))
        if plan['operation']=='exam_ranking':
            ranked=ranked.order_by('percentage','student_id') if plan.get('aggregation')=='avg' else ranked.order_by('-percentage','student_id')
            cap=plan.get('limit',10)
        else:ranked=ranked.order_by('student_id','exam_id');cap=settings.ASSISTANT_MAX_RESULT_ROWS
        rows=[];student_ids=[]
        for result in ranked[:cap]:
            student_ids.append(result.student_id);rows.append({'student':result.student.name,'class':result.exam.school_class.name,'exam':result.exam.name,'subject':result.exam.subject.name,'marks':result.marks,'maximum':result.exam.max_marks,'pass_marks':result.exam.pass_marks,'percentage':format(result.percentage,'.2f')})
        self.capture('students',scoped('students',self.user).filter(pk__in=student_ids))
        title='Results below the pass mark' if plan['operation']=='exam_failures' else 'Ranked examination results'
        if plan['operation']=='exam_ranking':self.notes.append('Ranking is by normalized result percentage, not a combined student GPA. A student may have multiple results if multiple exams are selected.')
        return self.base_result(spec,title,f'{len(rows)} result records shown from {count} matching recorded results.',rows,[{'key':key,'label':label,'type':'text'} for key,label in [('student','Student'),('class','Class'),('exam','Exam'),('subject','Subject'),('marks','Marks'),('maximum','Maximum'),('pass_marks','Pass mark'),('percentage','Percentage')]],[{'label':'Matching result records','value':count}],len(rows) if plan['operation']=='exam_ranking' else count,student_ids if count<=cap or plan['operation']=='exam_ranking' else [])

    def comparison(self,plan):
        if plan.get('period') not in ['this_month','last_month','current_academic_year']:
            raise QueryProblem('For a comparison, choose this month versus last month, or the current versus previous academic year.')
        original={**plan,'compare':False};current=self.run(original)
        previous={**original,'period':'previous_academic_year' if plan['period']=='current_academic_year' else 'last_month'}
        before=self.run(previous)
        metrics={item['label']:item for item in before['summary']}
        rows=[]
        for item in current['summary']:
            old=metrics.get(item['label'])
            if old is None:continue
            left,right=old['value'],item['value']
            difference=None if left is None or right is None else Decimal(str(right))-Decimal(str(left))
            rows.append({'measure':item['label'],'previous':left,'current':right,'change':difference,'unit':item.get('unit','')})
        if not rows:raise QueryProblem('This result is a record list without comparable summary measures. Ask for a count, total, average, or attendance percentage.')
        self.notes.append('Current-month figures are month-to-date; the previous month covers its full calendar month. Both date ranges are shown in the filters.')
        return self.base_result(self.resources[plan['resource']],'Period comparison','Comparison calculated from the recorded data for both displayed periods.',rows,[{'key':key,'label':label,'type':'text'} for key,label in [('measure','Measure'),('previous','Previous period'),('current','Current period'),('change','Change'),('unit','Unit')]],[],len(rows))
