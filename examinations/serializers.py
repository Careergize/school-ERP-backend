from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class ExamSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    subject_id = serializers.PrimaryKeyRelatedField(source='subject', queryset=apps.get_model('academics.Subject').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Exam
        fields = ['id', 'version', 'name', 'class_id', 'subject_id', 'date', 'max_marks', 'pass_marks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ResultSerializer(RecordSerializer):
    percentage = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()

    def get_percentage(self, instance):
        from decimal import Decimal
        return format(Decimal(instance.marks) * 100 / instance.exam.max_marks, '.2f')

    def get_outcome(self, instance):
        return 'Pass' if instance.marks >= instance.exam.pass_marks else 'Fail'

    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)
    exam_id = serializers.PrimaryKeyRelatedField(source='exam', queryset=apps.get_model('examinations.Exam').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Result
        fields = ['id', 'version', 'student_id', 'exam_id', 'marks', 'percentage', 'outcome', 'remarks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
