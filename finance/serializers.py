from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class InvoiceSerializer(RecordSerializer):
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    def get_paid_amount(self, instance):
        from django.db.models import Sum
        from decimal import Decimal
        if not hasattr(instance, '_received_total'):
            instance._received_total = instance.receipts.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return format(instance._received_total, '.2f')

    def get_balance(self, instance):
        from decimal import Decimal
        return format(instance.amount - Decimal(self.get_paid_amount(instance)), '.2f')

    def get_payment_status(self, instance):
        from decimal import Decimal
        paid = Decimal(self.get_paid_amount(instance))
        return 'Paid' if paid >= instance.amount else 'Partial' if paid else 'Unpaid'

    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Invoice
        fields = ['id', 'version', 'name', 'student_id', 'amount', 'due', 'paid_amount', 'balance', 'payment_status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ReceiptSerializer(RecordSerializer):
    invoice_id = serializers.PrimaryKeyRelatedField(source='invoice', queryset=apps.get_model('finance.Invoice').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Receipt
        fields = ['id', 'version', 'invoice_id', 'amount', 'date', 'method', 'reference', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
