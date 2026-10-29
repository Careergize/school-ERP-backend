from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Staff(RecordModel):
    name = models.CharField('Full name', max_length=255)
    email = models.EmailField('Email', max_length=254)
    phone = models.CharField('Phone', max_length=32)
    designation = models.CharField('Designation', max_length=255)
    department = models.CharField('Department', max_length=255)
    salary = models.DecimalField('Monthly salary', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    joined = models.DateField('Joining date')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(salary__gte=0), name='hr_staff_salary_nonnegative'),
        ]

    def __str__(self):
        return self.name


class Payslip(RecordModel):
    staff = models.ForeignKey('hr.Staff', verbose_name='Staff', on_delete=models.PROTECT, related_name='payroll_staff')
    month = models.CharField('Month (YYYY-MM)', max_length=255)
    basic = models.DecimalField('Basic pay', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    allowances = models.DecimalField('Allowances', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    deductions = models.DecimalField('Deductions', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    status = models.CharField('Status', max_length=32, choices=[('Draft', 'Draft'), ('Approved', 'Approved'), ('Paid', 'Paid')], default='Draft')

    class Meta:
        indexes = [models.Index(fields=['month', 'status'])]
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(basic__gte=0), name='hr_payslip_basic_nonnegative'),
            models.CheckConstraint(condition=Q(allowances__gte=0), name='hr_payslip_allowances_nonnegative'),
            models.CheckConstraint(condition=Q(deductions__gte=0), name='hr_payslip_deductions_nonnegative'),
            models.UniqueConstraint(fields=['staff', 'month'], name='hr_payslip_unique'),
            models.CheckConstraint(condition=Q(deductions__lte=F("basic") + F("allowances")), name='hr_payslip_valid_deductions'),
        ]

    def __str__(self):
        return self.month

    def clean(self):
        super().clean()
        from datetime import date
        try:
            date.fromisoformat(self.month + '-01')
        except (ValueError, TypeError):
            raise ValidationError({'month': 'Month must use YYYY-MM.'})
        if self.basic is not None and self.allowances is not None and self.deductions is not None and self.deductions > self.basic + self.allowances:
            raise ValidationError({'deductions': 'Deductions exceed gross pay.'})

    @property
    def net_pay(self):
        return self.basic + self.allowances - self.deductions


class PerformanceReview(RecordModel):
    staff = models.ForeignKey('hr.Staff', verbose_name='Staff', on_delete=models.PROTECT, related_name='reviews_staff')
    date = models.DateField('Review date')
    rating = models.PositiveIntegerField('Rating (0–5)')
    description = models.TextField('Review notes')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(rating__lte=5), name='hr_performancereview_rating_range'),
        ]

    def __str__(self):
        return f"PerformanceReview #{self.pk}"

    def clean(self):
        super().clean()
        if self.rating is not None and self.rating > 5:
            raise ValidationError({'rating': 'Rating must be between 0 and 5.'})
