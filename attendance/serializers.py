from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class AttendanceSerializer(RecordSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Attendance
        fields = ['id', 'version', 'student_id', 'date', 'status', 'note', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
