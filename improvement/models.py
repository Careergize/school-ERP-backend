from django.db import models
from django.db.models import Q
from core.models import RecordModel


class ImprovementPlan(RecordModel):
    id = models.BigAutoField(primary_key=True)
    baseline = models.ForeignKey('examinations.Result', on_delete=models.PROTECT, related_name='improvement_plans')
    baseline_percent = models.FloatField()
    target = models.PositiveSmallIntegerField()
    topic = models.CharField(max_length=255)
    teacher = models.ForeignKey('hr.Staff', on_delete=models.PROTECT)
    due = models.DateField()
    feedback = models.TextField(blank=True)
    reassessment = models.ForeignKey('examinations.Result', null=True, blank=True, on_delete=models.PROTECT, related_name='reassessed_plans')
    reassessment_percent = models.FloatField(null=True, blank=True)
    closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(condition=Q(target__gte=1, target__lte=100), name='improvement_target_range'),
            models.UniqueConstraint(fields=['baseline'], condition=Q(closed=False), name='improvement_active_baseline'),
        ]


class LearningTask(RecordModel):
    id = models.BigAutoField(primary_key=True)
    plan = models.ForeignKey(ImprovementPlan, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    instructions = models.TextField()
    due = models.DateField()
    completed = models.BooleanField(default=False)
    evidence = models.TextField(blank=True)

    class Meta:
        ordering = ['due', 'id']
