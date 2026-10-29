from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Invoice(RecordModel):
    name = models.CharField('Invoice title', max_length=255)
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='fees_student')
    amount = models.DecimalField('Amount (INR)', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    due = models.DateField('Due date')

    class Meta:
        indexes = [models.Index(fields=['due'])]
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name='finance_invoice_amount_nonnegative'),
            models.CheckConstraint(condition=Q(amount__gt=0), name='finance_invoice_positive_amount'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        paid = self.receipts.aggregate(total=Sum('amount'))['total'] or Decimal('0') if self.pk else Decimal('0')
        if self.amount is not None and (self.amount <= 0 or self.amount < paid):
            raise ValidationError({'amount': 'Invoice must be positive and cannot be less than receipts.'})


class Receipt(RecordModel):
    invoice = models.ForeignKey('finance.Invoice', verbose_name='Invoice', on_delete=models.PROTECT, related_name='receipts')
    amount = models.DecimalField('Amount received (INR)', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    date = models.DateField('Received on')
    method = models.CharField('Method', max_length=32, choices=[('Cash', 'Cash'), ('Bank transfer', 'Bank transfer'), ('Cheque', 'Cheque')], default='Cash')
    reference = models.CharField('Reference / cheque number', max_length=255, blank=True, default='')

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name='finance_receipt_amount_nonnegative'),
            models.CheckConstraint(condition=Q(amount__gt=0), name='finance_receipt_positive_amount'),
        ]

    def __str__(self):
        return f"Receipt #{self.pk}"

    def clean(self):
        super().clean()
        if self.invoice_id and self.amount is not None:
            paid = Receipt.objects.filter(invoice_id=self.invoice_id).exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            if self.amount <= 0 or paid + self.amount > self.invoice.amount:
                raise ValidationError('Receipt exceeds the outstanding balance or is zero.', code='conflict')
