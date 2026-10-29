from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Lesson(RecordModel):
    name = models.CharField('Lesson title', max_length=255)
    school_class = models.ForeignKey('academics.Batch', verbose_name='Class', on_delete=models.PROTECT, related_name='timetable_school_class')
    subject = models.ForeignKey('academics.Subject', verbose_name='Subject', on_delete=models.PROTECT, related_name='timetable_subject')
    teacher = models.ForeignKey('hr.Staff', verbose_name='Teacher', on_delete=models.PROTECT, related_name='timetable_teacher')
    day = models.CharField('Day', max_length=32, choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday')], default='Monday')
    start = models.TimeField('Start time')
    end = models.TimeField('End time')
    room = models.ForeignKey('academics.Classroom', verbose_name='Room', on_delete=models.PROTECT, related_name='timetable_room')

    class Meta:
        indexes = [models.Index(fields=['day', 'start'])]
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=F("start")), name='timetable_lesson_valid_times'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.subject_id and self.school_class_id and self.subject.school_class_id != self.school_class_id:
            raise ValidationError({'subject': 'Subject does not belong to this class.'})
        if self.start and self.end:
            if self.start >= self.end:
                raise ValidationError({'end': 'End time must be after start time.'})
            conflicts = Lesson.objects.filter(day=self.day, start__lt=self.end, end__gt=self.start).exclude(pk=self.pk)
            if conflicts.filter(Q(school_class_id=self.school_class_id) | Q(teacher_id=self.teacher_id) | Q(room_id=self.room_id)).exists():
                raise ValidationError('Class, teacher, or room has a timetable conflict.', code='conflict')
