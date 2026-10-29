from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class SchoolSettings(RecordModel):
    name = models.CharField('School name', max_length=255)
    email = models.EmailField('Contact email', max_length=254)
    phone = models.CharField('Phone', max_length=32, blank=True, default='')
    address = models.TextField('Address', blank=True, default='')
    currency = models.CharField('Currency', max_length=255)
    timezone = models.CharField('Timezone', max_length=255)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name
