from rest_framework import serializers


class ChatInput(serializers.Serializer):
    message=serializers.CharField(max_length=2000,trim_whitespace=True)
    conversation_id=serializers.UUIDField(required=False,allow_null=True)
    request_id=serializers.UUIDField(required=False)


class ReportInput(serializers.Serializer):
    result_id=serializers.UUIDField()
    mode=serializers.ChoiceField(choices=['summary','detailed'],default='detailed')
