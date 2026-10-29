"""Keep a student's current class and academic history consistent atomically."""
from django.db.models import F
from django.utils import timezone
from .models import Enrollment


def record_enrollment(student,previous_class_id=None):
    today=timezone.localdate()
    active=Enrollment.objects.filter(student=student,status='Active')
    if student.status!='Active':
        state='Completed' if student.status=='Graduated' else 'Withdrawn'
        active.update(status=state,to_date=today,version=F('version')+1,updated_at=timezone.now())
        return
    active.exclude(school_class_id=student.school_class_id).update(status='Transferred',to_date=today,version=F('version')+1,updated_at=timezone.now())
    if active.filter(school_class_id=student.school_class_id).exists(): return
    history=Enrollment.objects.filter(student=student,school_class=student.school_class,from_date=today).first()
    if history:
        history.status='Active';history.to_date=None;history.version+=1
    else:
        history=Enrollment(student=student,school_class=student.school_class,from_date=today,status='Active')
    history.full_clean();history.save()
