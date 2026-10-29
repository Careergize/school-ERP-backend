from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class NoticeListAPIView(RecordListAPIView):
    module = 'notices'
    model = models.Notice
    serializer_class = serializers.NoticeSerializer


class NoticeDetailAPIView(RecordDetailAPIView):
    module = 'notices'
    model = models.Notice
    serializer_class = serializers.NoticeSerializer


class NoticeExportAPIView(RecordExportAPIView):
    module = 'notices'
    model = models.Notice
    serializer_class = serializers.NoticeSerializer


class MessageListAPIView(RecordListAPIView):
    module = 'messages'
    model = models.Message
    serializer_class = serializers.MessageSerializer


class MessageDetailAPIView(RecordDetailAPIView):
    module = 'messages'
    model = models.Message
    serializer_class = serializers.MessageSerializer


class MessageExportAPIView(RecordExportAPIView):
    module = 'messages'
    model = models.Message
    serializer_class = serializers.MessageSerializer
