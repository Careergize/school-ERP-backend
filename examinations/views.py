from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class ExamListAPIView(RecordListAPIView):
    module = 'exams'
    model = models.Exam
    serializer_class = serializers.ExamSerializer


class ExamDetailAPIView(RecordDetailAPIView):
    module = 'exams'
    model = models.Exam
    serializer_class = serializers.ExamSerializer


class ExamExportAPIView(RecordExportAPIView):
    module = 'exams'
    model = models.Exam
    serializer_class = serializers.ExamSerializer


class ResultListAPIView(RecordListAPIView):
    module = 'results'
    model = models.Result
    serializer_class = serializers.ResultSerializer


class ResultDetailAPIView(RecordDetailAPIView):
    module = 'results'
    model = models.Result
    serializer_class = serializers.ResultSerializer


class ResultExportAPIView(RecordExportAPIView):
    module = 'results'
    model = models.Result
    serializer_class = serializers.ResultSerializer
