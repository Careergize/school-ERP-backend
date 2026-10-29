"""ORM queries and atomic record operations shared by domain APIViews."""
import csv
import io
from importlib import import_module
from django.apps import apps
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, CharField, TextField
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from core.registry import MODULES
from core.models import AuditEvent


class HTTPException(Exception):
    def __init__(self, status_code, detail, errors=None):
        self.status_code, self.detail, self.errors = status_code, detail, errors


def model_for(module):
    if module not in MODULES:
        raise HTTPException(404, 'Unknown module.')
    return apps.get_model(MODULES[module]['model'])


def serializer_for(module):
    config = MODULES[module]
    return getattr(import_module(config['app']+'.serializers'), model_for(module).__name__+'Serializer')


def allowed_students(user):
    Student = apps.get_model('students.Student')
    role = user['role']
    if role == 'student': return Student.objects.filter(pk=user['student_id'])
    if role == 'parent': return Student.objects.filter(parent_id=user['parent_id'])
    if role == 'teacher':
        return Student.objects.filter(Q(school_class__teacher_id=user['staff_id']) | Q(school_class__subjects__teacher_id=user['staff_id'])).distinct()
    return Student.objects.all()


def allowed_classes(user):
    Batch = apps.get_model('academics.Batch')
    students = allowed_students(user)
    result = Q(students__in=students) | Q(enrollments_school_class__student__in=students)
    if user['role'] == 'teacher':
        result |= Q(teacher_id=user['staff_id']) | Q(subjects__teacher_id=user['staff_id'])
    return Batch.objects.filter(result).distinct()


def queryset_for(module, user, search=''):
    model = model_for(module)
    qs = model.objects.all()
    role = user['role']
    if role != 'admin':
        if module in ['staff', 'payroll', 'reviews']:
            if module == 'staff' and role == 'teacher': qs=qs.filter(pk=user['staff_id'])
            elif role != 'accountant' or module == 'reviews': qs=qs.none()
        elif module == 'admissions': qs=qs.none()
        elif module == 'parents': qs=qs.filter(pk=user['parent_id']) if role == 'parent' else qs.none()
        elif module in ['notices','messages']:
            audience={'teacher':'Staff','accountant':'Staff','librarian':'Staff','parent':'Parents','student':'Students'}[role]
            qs=qs.filter(Q(audience__in=['Everyone',audience]) | Q(author_id=user['id']))
        elif role in ['student','parent','teacher']:
            students=allowed_students(user)
            fields={f.name for f in model._meta.fields}
            if module=='students': qs=qs.filter(pk__in=students)
            elif 'student' in fields: qs=qs.filter(student__in=students)
            elif module=='payments': qs=qs.filter(invoice__student__in=students)
            elif 'school_class' in fields: qs=qs.filter(school_class__in=allowed_classes(user))
            elif module=='classes': qs=qs.filter(pk__in=allowed_classes(user))
            elif module not in ['books','rooms','activities','transport','hostels','courses','academic_years','school_settings']: qs=qs.none()
        elif role=='librarian' and module not in ['books','loans','students','classes']: qs=qs.none()
        elif role=='accountant' and module not in ['fees','payments','payroll','staff','students','classes']: qs=qs.none()
    if search:
        expression=Q()
        for field in model._meta.fields:
            if isinstance(field,(CharField,TextField)): expression |= Q(**{field.name+'__icontains':search})
        qs=qs.filter(expression)
    return qs.order_by('-id')


def audit(user, action, module, record_id):
    return AuditEvent.objects.create(user_id=user['id'] if user else None, action=action, module=module, record_id=record_id)


def check_write_role(module, user):
    model_for(module)
    if user['role'] not in MODULES[module]['roles']:
        raise HTTPException(403, 'Your role cannot modify this module.')


def check_write_scope(module, user, values):
    role=user['role']
    if role=='teacher':
        if module in ['messages','notices']:
            if values.get('audience') not in ['Students','Parents']:
                raise HTTPException(403,'Teachers can publish to students and parents only.')
        elif values.get('student') and not allowed_students(user).filter(pk=values['student'].pk).exists():
            raise HTTPException(403,'Student is outside your assigned classes.')
        elif values.get('school_class') and not allowed_classes(user).filter(pk=values['school_class'].pk).exists():
            raise HTTPException(403,'Class is outside your assigned scope.')
        elif values.get('exam') and not allowed_classes(user).filter(pk=values['exam'].school_class_id).exists():
            raise HTTPException(403,'Exam is outside your assigned scope.')
    if role=='student' and (not values.get('student') or values['student'].pk!=user['student_id'] or values.get('feedback')):
        raise HTTPException(403,'Students may submit only their own work without feedback.')


def validation_failure(exc):
    if hasattr(exc, 'error_dict'):
        errors={key:[item.message % item.params if item.params else item.message for item in items] for key,items in exc.error_dict.items()}
        codes=[item.code for items in exc.error_dict.values() for item in items]
    else:
        errors={'non_field_errors':exc.messages};codes=[item.code for item in exc.error_list]
    status=409 if any(code in ['conflict','unique','unique_together'] for code in codes) else 422
    raise HTTPException(status, ' '.join(str(message) for messages in errors.values() for message in messages), errors)


def validate_serializer(serializer):
    if not serializer.is_valid():
        def codes(value):
            if isinstance(value,dict): return [code for child in value.values() for code in codes(child)]
            if isinstance(value,list): return [code for child in value for code in codes(child)]
            return [getattr(value,'code','invalid')]
        status=409 if 'unique' in codes(serializer.errors) else 422
        raise HTTPException(status,'Validation failed.',serializer.errors)


def lock_relations(values):
    references=sorted((value for value in values.values() if hasattr(value,'_meta')), key=lambda value:(value._meta.label_lower,value.pk))
    for instance in references:
        type(instance).objects.select_for_update().get(pk=instance.pk)


def instance_for(module, rid, user, lock=False):
    qs=queryset_for(module,user)
    if lock: qs=qs.select_for_update()
    try: return qs.get(pk=rid)
    except model_for(module).DoesNotExist: raise HTTPException(404,'Record not found.')


def create(module, body, u=None):
    check_write_role(module,u)
    try:
        with transaction.atomic():
            serializer=serializer_for(module)(data=body)
            validate_serializer(serializer)
            values=serializer.validated_data
            check_write_scope(module,u,values)
            lock_relations(values)
            if module=='admissions' and values.get('status')=='Accepted': raise HTTPException(422,'Use Enroll to accept an application.')
            candidate=model_for(module)(**values)
            candidate.full_clean()
            instance=serializer.save(**({"author_id":u["id"]} if module in ["notices","messages"] else {}))
            if module=='students':
                from students.services import record_enrollment
                record_enrollment(instance)
            audit(u,'create',module,instance.pk)
            return serializer_for(module)(instance).data
    except ModelValidationError as exc: validation_failure(exc)
    except IntegrityError: raise HTTPException(409,'A database constraint prevents this change.')


def update(module, rid, body, u=None):
    check_write_role(module,u)
    try:
        with transaction.atomic():
            instance=instance_for(module,rid,u,lock=True)
            if u['role']=='teacher' and module in ['notices','messages'] and instance.author_id!=u['id']:
                raise HTTPException(403,'Teachers may modify only their own communications.')
            if body.get('version')!=instance.version: raise HTTPException(409,'Record changed. Refresh and try again.')
            if module=='admissions' and (instance.status=='Accepted' or body.get('status')=='Accepted'):
                raise HTTPException(422,'Enrolled applications cannot be edited; use Enroll for acceptance.')
            previous_class_id=instance.school_class_id if module=='students' else None
            serializer=serializer_for(module)(instance,data=body)
            validate_serializer(serializer)
            check_write_scope(module,u,serializer.validated_data)
            lock_relations(serializer.validated_data)
            for key,value in serializer.validated_data.items(): setattr(instance,key,value)
            instance.full_clean()
            instance=serializer.save(version=instance.version+1)
            if module=='students':
                from students.services import record_enrollment
                record_enrollment(instance,previous_class_id)
            audit(u,'update',module,instance.pk)
            return serializer_for(module)(instance).data
    except ModelValidationError as exc: validation_failure(exc)
    except IntegrityError: raise HTTPException(409,'A database constraint prevents this change.')


def delete(module, rid, u=None):
    check_write_role(module,u)
    try:
        with transaction.atomic():
            instance=instance_for(module,rid,u,lock=True)
            if u['role']=='teacher' and module in ['notices','messages'] and instance.author_id!=u['id']:
                raise HTTPException(403,'Teachers may modify only their own communications.')
            if module=='admissions' and instance.status=='Accepted': raise HTTPException(409,'Enrolled applications are retained for history.')
            instance.delete()
            audit(u,'delete',module,rid)
    except ProtectedError: raise HTTPException(409,'This record is referenced by another record and cannot be deleted.')
    return {'ok':True}


def data(u=None):
    return {key:list_records(key,u) for key in MODULES}


def list_records(module,u,search=''):
    return serializer_for(module)(queryset_for(module,u,search),many=True).data


def catalog(u=None):
    from configuration.services import module_catalog
    return module_catalog(u)


def export(module,u=None):
    rows=list_records(module,u)
    keys=[key for key in serializer_for(module)().fields if key not in ['created_at','updated_at']]
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=keys,extrasaction='ignore');writer.writeheader()
    for row in rows:
        writer.writerow({key:("'"+str(value) if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')) else value) for key,value in row.items()})
    return HttpResponse(out.getvalue(),content_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{module}.csv"'})


def audit_log(u=None):
    return [{'id':event.pk,'name':event.user.name if event.user else None,'user_id':event.user_id,'action':event.action,'module':event.module,'record_id':event.record_id,'at':event.at.isoformat()} for event in AuditEvent.objects.select_related('user')[:500]]


def health(): return {'status':'ok','storage':'django-orm'}
