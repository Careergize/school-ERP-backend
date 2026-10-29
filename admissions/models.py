from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Application(RecordModel):
    name = models.CharField('Applicant name', max_length=255)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Requested class', on_delete=models.PROTECT, related_name='admissions_school_class')
    email = models.EmailField('Guardian email', max_length=254)
    phone = models.CharField('Phone', max_length=32)
    dob = models.DateField('Date of birth')
    status = models.CharField('Status', max_length=32, choices=[('Applied', 'Applied'), ('Under review', 'Under review'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')], default='Applied')
    enrolled_student = models.OneToOneField('students.Student', null=True, blank=True, on_delete=models.PROTECT, related_name='admission_application')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name
