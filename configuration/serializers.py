from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class SchoolSettingsSerializer(RecordSerializer):
    class Meta:
        model = models.SchoolSettings
        fields = ['id', 'version', 'name', 'email', 'phone', 'address', 'currency', 'timezone', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
