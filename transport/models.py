from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Route(RecordModel):
    name = models.CharField('Route name', max_length=255)
    vehicle = models.CharField('Vehicle number', max_length=255)
    driver = models.CharField('Driver name', max_length=255)
    phone = models.CharField('Driver phone', max_length=32)
    capacity = models.PositiveIntegerField('Capacity', validators=[MinValueValidator(1)])
    stops = models.TextField('Stops')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='transport_route_capacity_positive'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.pk and self.allocations.count() > self.capacity:
            raise ValidationError('Capacity is lower than existing route allocations.', code='conflict')


class TransportAllocation(RecordModel):
    student = models.OneToOneField('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='transport_allocations_student')
    route = models.ForeignKey('transport.Route', verbose_name='Route', on_delete=models.PROTECT, related_name='allocations')
    stop = models.CharField('Pickup stop', max_length=255)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"TransportAllocation #{self.pk}"

    def clean(self):
        super().clean()
        if self.route_id and TransportAllocation.objects.filter(route_id=self.route_id).exclude(pk=self.pk).count() >= self.route.capacity:
            raise ValidationError('Route is full.', code='conflict')
