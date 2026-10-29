"""Admission acceptance and student creation are one database transaction."""
from django.db import transaction
from core import services
from .models import Application
from academics.models import Batch


@transaction.atomic
def enroll(rid,u=None):
    if u['role']!='admin': raise services.HTTPException(403,'Administrator access required.')
    try: application=Application.objects.select_for_update().get(pk=rid)
    except Application.DoesNotExist: raise services.HTTPException(404,'Application not found.')
    if application.status in ['Accepted','Rejected']: raise services.HTTPException(409,'Application has already been decided.')
    Batch.objects.select_for_update().get(pk=application.school_class_id)
    student=services.create('students',{'name':application.name,'roll':f'ADM-{application.pk:05d}', 'class_id':application.school_class_id,'dob':application.dob.isoformat(),'gender':'Other','email':application.email,'phone':application.phone,'status':'Active'},u)
    application.status='Accepted';application.enrolled_student_id=student['id'];application.version+=1
    application.full_clean();application.save()
    services.audit(u,'enroll','admissions',application.pk)
    return student
