from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class LessonSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    subject_id = serializers.PrimaryKeyRelatedField(source='subject', queryset=apps.get_model('academics.Subject').objects.all(), required=True, allow_null=False)
    teacher_id = serializers.PrimaryKeyRelatedField(source='teacher', queryset=apps.get_model('hr.Staff').objects.all(), required=True, allow_null=False)
    room_id = serializers.PrimaryKeyRelatedField(source='room', queryset=apps.get_model('academics.Classroom').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Lesson
        fields = ['id', 'version', 'name', 'class_id', 'subject_id', 'teacher_id', 'day', 'start', 'end', 'room_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
