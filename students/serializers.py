from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class StudentSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    parent_id = serializers.PrimaryKeyRelatedField(source='parent', queryset=apps.get_model('students.Guardian').objects.all(), required=False, allow_null=True)

    class Meta:
        model = models.Student
        fields = ['id', 'version', 'name', 'roll', 'class_id', 'parent_id', 'dob', 'gender', 'email', 'phone', 'address', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class GuardianSerializer(RecordSerializer):
    class Meta:
        model = models.Guardian
        fields = ['id', 'version', 'name', 'email', 'phone', 'relationship', 'address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class EnrollmentSerializer(RecordSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Enrollment
        fields = ['id', 'version', 'student_id', 'class_id', 'from_date', 'to_date', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
