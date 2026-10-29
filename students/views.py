from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class StudentListAPIView(RecordListAPIView):
    module = 'students'
    model = models.Student
    serializer_class = serializers.StudentSerializer


class StudentDetailAPIView(RecordDetailAPIView):
    module = 'students'
    model = models.Student
    serializer_class = serializers.StudentSerializer


class StudentExportAPIView(RecordExportAPIView):
    module = 'students'
    model = models.Student
    serializer_class = serializers.StudentSerializer


class GuardianListAPIView(RecordListAPIView):
    module = 'parents'
    model = models.Guardian
    serializer_class = serializers.GuardianSerializer


class GuardianDetailAPIView(RecordDetailAPIView):
    module = 'parents'
    model = models.Guardian
    serializer_class = serializers.GuardianSerializer


class GuardianExportAPIView(RecordExportAPIView):
    module = 'parents'
    model = models.Guardian
    serializer_class = serializers.GuardianSerializer


class EnrollmentListAPIView(RecordListAPIView):
    module = 'enrollments'
    model = models.Enrollment
    serializer_class = serializers.EnrollmentSerializer


class EnrollmentDetailAPIView(RecordDetailAPIView):
    module = 'enrollments'
    model = models.Enrollment
    serializer_class = serializers.EnrollmentSerializer


class EnrollmentExportAPIView(RecordExportAPIView):
    module = 'enrollments'
    model = models.Enrollment
    serializer_class = serializers.EnrollmentSerializer
