from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class BatchSerializer(RecordSerializer):
    teacher_id = serializers.PrimaryKeyRelatedField(source='teacher', queryset=apps.get_model('hr.Staff').objects.all(), required=True, allow_null=False)
    room_id = serializers.PrimaryKeyRelatedField(source='room', queryset=apps.get_model('academics.Classroom').objects.all(), required=False, allow_null=True)
    course_id = serializers.PrimaryKeyRelatedField(source='course', queryset=apps.get_model('academics.Course').objects.all(), required=False, allow_null=True)
    academic_year_id = serializers.PrimaryKeyRelatedField(source='academic_year', queryset=apps.get_model('academics.AcademicYear').objects.all(), required=False, allow_null=True)

    class Meta:
        model = models.Batch
        fields = ['id', 'version', 'name', 'year', 'teacher_id', 'capacity', 'room_id', 'course_id', 'academic_year_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class SubjectSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    teacher_id = serializers.PrimaryKeyRelatedField(source='teacher', queryset=apps.get_model('hr.Staff').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Subject
        fields = ['id', 'version', 'name', 'code', 'class_id', 'teacher_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AssignmentSerializer(RecordSerializer):
    class_id = serializers.PrimaryKeyRelatedField(source='school_class', queryset=apps.get_model('academics.Batch').objects.all(), required=True, allow_null=False)
    subject_id = serializers.PrimaryKeyRelatedField(source='subject', queryset=apps.get_model('academics.Subject').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Assignment
        fields = ['id', 'version', 'name', 'class_id', 'subject_id', 'due', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class SubmissionSerializer(RecordSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)
    assignment_id = serializers.PrimaryKeyRelatedField(source='assignment', queryset=apps.get_model('academics.Assignment').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Submission
        fields = ['id', 'version', 'student_id', 'assignment_id', 'content', 'feedback', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ClassroomSerializer(RecordSerializer):
    class Meta:
        model = models.Classroom
        fields = ['id', 'version', 'name', 'building', 'capacity', 'type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ActivitySerializer(RecordSerializer):
    class Meta:
        model = models.Activity
        fields = ['id', 'version', 'name', 'date', 'location', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class CourseSerializer(RecordSerializer):
    class Meta:
        model = models.Course
        fields = ['id', 'version', 'name', 'code', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AcademicYearSerializer(RecordSerializer):
    class Meta:
        model = models.AcademicYear
        fields = ['id', 'version', 'name', 'start_date', 'end_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
