from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class RouteSerializer(RecordSerializer):
    class Meta:
        model = models.Route
        fields = ['id', 'version', 'name', 'vehicle', 'driver', 'phone', 'capacity', 'stops', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class TransportAllocationSerializer(RecordSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)
    route_id = serializers.PrimaryKeyRelatedField(source='route', queryset=apps.get_model('transport.Route').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.TransportAllocation
        fields = ['id', 'version', 'student_id', 'route_id', 'stop', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
