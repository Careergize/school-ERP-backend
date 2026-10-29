from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class LessonListAPIView(RecordListAPIView):
    module = 'timetable'
    model = models.Lesson
    serializer_class = serializers.LessonSerializer


class LessonDetailAPIView(RecordDetailAPIView):
    module = 'timetable'
    model = models.Lesson
    serializer_class = serializers.LessonSerializer


class LessonExportAPIView(RecordExportAPIView):
    module = 'timetable'
    model = models.Lesson
    serializer_class = serializers.LessonSerializer
