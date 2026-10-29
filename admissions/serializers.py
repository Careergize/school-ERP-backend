from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class ApplicationSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    enrolled_student_id = serializers.PrimaryKeyRelatedField(source='enrolled_student', read_only=True)

    class Meta:
        model = models.Application
        fields = ['id', 'version', 'name', 'class_id', 'email', 'phone', 'dob', 'status', 'enrolled_student_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
