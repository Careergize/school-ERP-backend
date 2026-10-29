from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Batch(RecordModel):
    name = models.CharField('Class / section', max_length=255)
    year = models.CharField('Academic year', max_length=255)
    teacher = models.ForeignKey('hr.Staff', verbose_name='Class teacher', on_delete=models.PROTECT, related_name='batches')
    capacity = models.PositiveIntegerField('Capacity', validators=[MinValueValidator(1)])
    room = models.ForeignKey('academics.Classroom', verbose_name='Classroom', on_delete=models.PROTECT, related_name='batches', null=True, blank=True)
    course = models.ForeignKey('academics.Course', verbose_name='Course', on_delete=models.PROTECT, related_name='classes_course', null=True, blank=True)
    academic_year = models.ForeignKey('academics.AcademicYear', verbose_name='Academic year record', on_delete=models.PROTECT, related_name='classes_academic_year', null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='academics_batch_capacity_positive'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.pk and self.students.filter(status='Active').count() > self.capacity:
            raise ValidationError('Capacity cannot be lower than active enrollment.', code='conflict')


class Subject(RecordModel):
    name = models.CharField('Subject name', max_length=255)
    code = models.CharField('Subject code', max_length=255, unique=True)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='subjects')
    teacher = models.ForeignKey('hr.Staff', verbose_name='Faculty', on_delete=models.PROTECT, related_name='subjects_teacher')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Assignment(RecordModel):
    name = models.CharField('Assignment title', max_length=255)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='assignments_school_class')
    subject = models.ForeignKey('academics.Subject', verbose_name='Subject', on_delete=models.PROTECT, related_name='assignments_subject')
    due = models.DateField('Due date')
    description = models.TextField('Instructions')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.subject_id and self.school_class_id and self.subject.school_class_id != self.school_class_id:
            raise ValidationError({'subject': 'Subject does not belong to this class.'})


class Submission(RecordModel):
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='submissions_student')
    assignment = models.ForeignKey('academics.Assignment', verbose_name='Assignment', on_delete=models.PROTECT, related_name='submissions_assignment')
    content = models.TextField('Submission text / link')
    feedback = models.CharField('Teacher feedback', max_length=255, blank=True, default='')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=['student', 'assignment'], name='academics_submission_unique'),
        ]

    def __str__(self):
        return f"Submission #{self.pk}"

    def clean(self):
        super().clean()
        if self.student_id and self.assignment_id and self.student.school_class_id != self.assignment.school_class_id:
            raise ValidationError({'assignment': 'Assignment belongs to another class.'})


class Classroom(RecordModel):
    name = models.CharField('Room name', max_length=255)
    building = models.CharField('Building', max_length=255)
    capacity = models.PositiveIntegerField('Capacity', validators=[MinValueValidator(1)])
    type = models.CharField('Type', max_length=32, choices=[('Classroom', 'Classroom'), ('Laboratory', 'Laboratory'), ('Sports', 'Sports'), ('Auditorium', 'Auditorium')], default='Classroom')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='academics_classroom_capacity_positive'),
        ]

    def __str__(self):
        return self.name


class Activity(RecordModel):
    name = models.CharField('Activity name', max_length=255)
    date = models.DateField('Date')
    location = models.CharField('Location', max_length=255)
    description = models.TextField('Description')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Course(RecordModel):
    name = models.CharField('Course name', max_length=255)
    code = models.CharField('Course code', max_length=255, unique=True)
    description = models.TextField('Description', blank=True, default='')

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class AcademicYear(RecordModel):
    name = models.CharField('Academic year', max_length=255)
    start_date = models.DateField('Starts')
    end_date = models.DateField('Ends')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")), name='academics_academicyear_valid_dates'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date must be after the start date.'})
