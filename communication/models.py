from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Notice(RecordModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='notices')
    name = models.CharField('Title', max_length=255)
    date = models.DateField('Date')
    audience = models.CharField('Audience', max_length=32, choices=[('Everyone', 'Everyone'), ('Staff', 'Staff'), ('Parents', 'Parents'), ('Students', 'Students')], default='Everyone')
    description = models.TextField('Message')

    class Meta:
        indexes = [models.Index(fields=['date', 'audience'])]
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Message(RecordModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='messages')
    name = models.CharField('Subject', max_length=255)
    date = models.DateField('Date')
    audience = models.CharField('Audience', max_length=32, choices=[('Everyone', 'Everyone'), ('Staff', 'Staff'), ('Parents', 'Parents'), ('Students', 'Students')], default='Everyone')
    description = models.TextField('Message')

    class Meta:
        indexes = [models.Index(fields=['date', 'audience'])]
        ordering = ["-id"]

    def __str__(self):
        return self.name
