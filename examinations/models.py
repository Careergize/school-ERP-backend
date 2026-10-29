from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Exam(RecordModel):
    name = models.CharField('Exam title', max_length=255)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='exams')
    subject = models.ForeignKey('academics.Subject', verbose_name='Subject', on_delete=models.PROTECT, related_name='exams_subject')
    date = models.DateField('Exam date')
    max_marks = models.PositiveIntegerField('Maximum marks')
    pass_marks = models.PositiveIntegerField('Pass marks')

    class Meta:
        indexes = [models.Index(fields=['date'])]
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(max_marks__gt=0) & Q(pass_marks__lte=F("max_marks")), name='examinations_exam_valid_marks'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.subject_id and self.school_class_id and self.subject.school_class_id != self.school_class_id:
            raise ValidationError({'subject': 'Subject does not belong to this class.'})
        if self.max_marks is not None and self.pass_marks is not None and (self.max_marks <= 0 or self.pass_marks > self.max_marks):
            raise ValidationError({'pass_marks': 'Pass marks must not exceed positive maximum marks.'})
        if self.pk and self.results.filter(marks__gt=self.max_marks).exists():
            raise ValidationError('Maximum marks cannot be lower than existing results.', code='conflict')


class Result(RecordModel):
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='results_student')
    exam = models.ForeignKey('examinations.Exam', verbose_name='Exam', on_delete=models.PROTECT, related_name='results')
    marks = models.PositiveIntegerField('Marks')
    remarks = models.CharField('Remarks', max_length=255, blank=True, default='')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=['student', 'exam'], name='examinations_result_unique'),
        ]

    def __str__(self):
        return f"Result #{self.pk}"

    def clean(self):
        super().clean()
        if self.exam_id and self.marks is not None and self.marks > self.exam.max_marks:
            raise ValidationError({'marks': 'Marks exceed maximum.'})
        if self.student_id and self.exam_id:
            from students.models import Enrollment
            enrolled = self.student.school_class_id == self.exam.school_class_id or Enrollment.objects.filter(student_id=self.student_id, school_class_id=self.exam.school_class_id).exists()
            if not enrolled:
                raise ValidationError({'student': 'Student is not enrolled in the exam class.'})
