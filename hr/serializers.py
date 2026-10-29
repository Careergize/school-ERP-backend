from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class StaffSerializer(RecordSerializer):
    class Meta:
        model = models.Staff
        fields = ['id', 'version', 'name', 'email', 'phone', 'designation', 'department', 'salary', 'joined', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class PayslipSerializer(RecordSerializer):
    net_pay = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    staff_id = serializers.PrimaryKeyRelatedField(source='staff', queryset=apps.get_model('hr.Staff').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Payslip
        fields = ['id', 'version', 'staff_id', 'month', 'basic', 'allowances', 'deductions', 'net_pay', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class PerformanceReviewSerializer(RecordSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(source='staff', queryset=apps.get_model('hr.Staff').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.PerformanceReview
        fields = ['id', 'version', 'staff_id', 'date', 'rating', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
