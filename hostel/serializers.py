from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class HostelRoomSerializer(RecordSerializer):
    class Meta:
        model = models.HostelRoom
        fields = ['id', 'version', 'name', 'building', 'capacity', 'warden', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class HostelAllocationSerializer(RecordSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)
    hostel_id = serializers.PrimaryKeyRelatedField(source='hostel', queryset=apps.get_model('hostel.HostelRoom').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.HostelAllocation
        fields = ['id', 'version', 'student_id', 'hostel_id', 'from_date', 'to_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
