from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class AttendanceListAPIView(RecordListAPIView):
    module = 'attendance'
    model = models.Attendance
    serializer_class = serializers.AttendanceSerializer


class AttendanceDetailAPIView(RecordDetailAPIView):
    module = 'attendance'
    model = models.Attendance
    serializer_class = serializers.AttendanceSerializer


class AttendanceExportAPIView(RecordExportAPIView):
    module = 'attendance'
    model = models.Attendance
    serializer_class = serializers.AttendanceSerializer
