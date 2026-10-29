"""Shared typed infrastructure. Domain records are stored in their own tables."""
from django.conf import settings
from django.db import models


class RecordModel(models.Model):
    version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='audit_events')
    action = models.CharField(max_length=32)
    module = models.CharField(max_length=64, db_index=True)
    record_id = models.PositiveBigIntegerField()
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-id']
