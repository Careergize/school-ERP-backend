from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class NoticeSerializer(RecordSerializer):
    author_id = serializers.PrimaryKeyRelatedField(source="author", read_only=True)

    class Meta:
        model = models.Notice
        fields = ['id', 'version', 'name', 'date', 'audience', 'description', 'author_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class MessageSerializer(RecordSerializer):
    author_id = serializers.PrimaryKeyRelatedField(source="author", read_only=True)

    class Meta:
        model = models.Message
        fields = ['id', 'version', 'name', 'date', 'audience', 'description', 'author_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
