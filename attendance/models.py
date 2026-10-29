from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Attendance(RecordModel):
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='attendance_student')
    date = models.DateField('Date')
    status = models.CharField('Status', max_length=32, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late'), ('Excused', 'Excused')], default='Present')
    note = models.CharField('Note', max_length=255, blank=True, default='')

    class Meta:
        indexes = [models.Index(fields=['date', 'status'])]
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=['student', 'date'], name='attendance_attendance_unique'),
        ]

    def __str__(self):
        return f"Attendance #{self.pk}"

    def clean(self):
        super().clean()
        if self.date and self.date > timezone.localdate():
            raise ValidationError({'date': 'Cannot record future attendance.'})
