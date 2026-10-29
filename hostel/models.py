from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class HostelRoom(RecordModel):
    name = models.CharField('Room name', max_length=255)
    building = models.CharField('Hostel building', max_length=255)
    capacity = models.PositiveIntegerField('Beds', validators=[MinValueValidator(1)])
    warden = models.CharField('Warden', max_length=255)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='hostel_hostelroom_capacity_positive'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.pk:
            allocations = list(self.allocations.all())
            for allocation in allocations:
                occupied = sum(other.from_date <= allocation.from_date <= other.to_date for other in allocations)
                if occupied > self.capacity:
                    raise ValidationError('Capacity is lower than existing hostel allocations.', code='conflict')


class HostelAllocation(RecordModel):
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='hostel_allocations_student')
    hostel = models.ForeignKey('hostel.HostelRoom', verbose_name='Room', on_delete=models.PROTECT, related_name='allocations')
    from_date = models.DateField('From date')
    to_date = models.DateField('Until')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(to_date__gte=F("from_date")), name='hostel_hostelallocation_valid_dates'),
        ]

    def __str__(self):
        return f"HostelAllocation #{self.pk}"

    def clean(self):
        super().clean()
        if not self.from_date or not self.to_date:
            return
        if self.from_date > self.to_date:
            raise ValidationError('Invalid allocation dates.')
        overlaps = HostelAllocation.objects.filter(from_date__lte=self.to_date, to_date__gte=self.from_date).exclude(pk=self.pk)
        if self.student_id and overlaps.filter(student_id=self.student_id).exists():
            raise ValidationError('Student already has an overlapping hostel allocation.', code='conflict')
        if self.hostel_id:
            # Count occupancy at every change point, rather than adding non-overlapping stays.
            stays = list(overlaps.filter(hostel_id=self.hostel_id).values_list('from_date','to_date'))
            points = {self.from_date} | {start for start, end in stays if self.from_date <= start <= self.to_date}
            if any(sum(start <= point <= end for start, end in stays) >= self.hostel.capacity for point in points):
                raise ValidationError('Hostel room is full for these dates.', code='conflict')
