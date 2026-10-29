from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Student(RecordModel):
    name = models.CharField('Full name', max_length=255)
    roll = models.CharField('Admission number', max_length=255, unique=True)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='students')
    parent = models.ForeignKey('students.Guardian', verbose_name='Parent', on_delete=models.PROTECT, related_name='students', null=True, blank=True)
    dob = models.DateField('Date of birth')
    gender = models.CharField('Gender', max_length=32, choices=[('Female', 'Female'), ('Male', 'Male'), ('Other', 'Other')], default='Female')
    email = models.EmailField('Email', max_length=254, blank=True, default='')
    phone = models.CharField('Phone', max_length=32, blank=True, default='')
    address = models.TextField('Address', blank=True, default='')
    status = models.CharField('Status', max_length=32, choices=[('Active', 'Active'), ('Graduated', 'Graduated'), ('Withdrawn', 'Withdrawn')], default='Active')

    class Meta:
        indexes = [models.Index(fields=['status'])]
        ordering = ["-id"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.dob and self.dob > timezone.localdate():
            raise ValidationError({'dob': 'Birth date cannot be in the future.'})
        if self.school_class_id and self.status == 'Active':
            peers = Student.objects.filter(school_class_id=self.school_class_id, status='Active').exclude(pk=self.pk)
            if peers.count() >= self.school_class.capacity:
                raise ValidationError('Class is full.', code='conflict')


class Guardian(RecordModel):
    name = models.CharField('Full name', max_length=255)
    email = models.EmailField('Email', max_length=254)
    phone = models.CharField('Phone', max_length=32)
    relationship = models.CharField('Relationship', max_length=32, choices=[('Mother', 'Mother'), ('Father', 'Father'), ('Guardian', 'Guardian')], default='Mother')
    address = models.TextField('Address', blank=True, default='')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Enrollment(RecordModel):
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='enrollments_student')
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='enrollments_school_class')
    from_date = models.DateField('From date')
    to_date = models.DateField('Until', null=True, blank=True)
    status = models.CharField('Status', max_length=32, choices=[('Active', 'Active'), ('Completed', 'Completed'), ('Transferred', 'Transferred'), ('Withdrawn', 'Withdrawn')], default='Active')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=['student', 'school_class', 'from_date'], name='students_enrollment_unique'),
            models.UniqueConstraint(fields=['student'], condition=Q(status='Active'), name='students_one_active_enrollment'),
            models.CheckConstraint(condition=Q(to_date__isnull=True) | Q(to_date__gte=F("from_date")), name='students_enrollment_valid_dates'),
        ]

    def __str__(self):
        return f"Enrollment #{self.pk}"

    def clean(self):
        super().clean()
        if self.to_date and self.from_date and self.to_date < self.from_date:
            raise ValidationError({'to_date': 'End date cannot precede the start date.'})
        if self.status == 'Active' and self.student_id and self.school_class_id != self.student.school_class_id:
            raise ValidationError({'school_class': 'Active enrollment must match the student current class.'})
        if self.status == 'Active' and self.student_id and Enrollment.objects.filter(student_id=self.student_id, status='Active').exclude(pk=self.pk).exists():
            raise ValidationError('Student already has an active enrollment.', code='conflict')
