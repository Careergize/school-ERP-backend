from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class BatchListAPIView(RecordListAPIView):
    module = 'classes'
    model = models.Batch
    serializer_class = serializers.BatchSerializer


class BatchDetailAPIView(RecordDetailAPIView):
    module = 'classes'
    model = models.Batch
    serializer_class = serializers.BatchSerializer


class BatchExportAPIView(RecordExportAPIView):
    module = 'classes'
    model = models.Batch
    serializer_class = serializers.BatchSerializer


class SubjectListAPIView(RecordListAPIView):
    module = 'subjects'
    model = models.Subject
    serializer_class = serializers.SubjectSerializer


class SubjectDetailAPIView(RecordDetailAPIView):
    module = 'subjects'
    model = models.Subject
    serializer_class = serializers.SubjectSerializer


class SubjectExportAPIView(RecordExportAPIView):
    module = 'subjects'
    model = models.Subject
    serializer_class = serializers.SubjectSerializer


class AssignmentListAPIView(RecordListAPIView):
    module = 'assignments'
    model = models.Assignment
    serializer_class = serializers.AssignmentSerializer


class AssignmentDetailAPIView(RecordDetailAPIView):
    module = 'assignments'
    model = models.Assignment
    serializer_class = serializers.AssignmentSerializer


class AssignmentExportAPIView(RecordExportAPIView):
    module = 'assignments'
    model = models.Assignment
    serializer_class = serializers.AssignmentSerializer


class SubmissionListAPIView(RecordListAPIView):
    module = 'submissions'
    model = models.Submission
    serializer_class = serializers.SubmissionSerializer


class SubmissionDetailAPIView(RecordDetailAPIView):
    module = 'submissions'
    model = models.Submission
    serializer_class = serializers.SubmissionSerializer


class SubmissionExportAPIView(RecordExportAPIView):
    module = 'submissions'
    model = models.Submission
    serializer_class = serializers.SubmissionSerializer


class ClassroomListAPIView(RecordListAPIView):
    module = 'rooms'
    model = models.Classroom
    serializer_class = serializers.ClassroomSerializer


class ClassroomDetailAPIView(RecordDetailAPIView):
    module = 'rooms'
    model = models.Classroom
    serializer_class = serializers.ClassroomSerializer


class ClassroomExportAPIView(RecordExportAPIView):
    module = 'rooms'
    model = models.Classroom
    serializer_class = serializers.ClassroomSerializer


class ActivityListAPIView(RecordListAPIView):
    module = 'activities'
    model = models.Activity
    serializer_class = serializers.ActivitySerializer


class ActivityDetailAPIView(RecordDetailAPIView):
    module = 'activities'
    model = models.Activity
    serializer_class = serializers.ActivitySerializer


class ActivityExportAPIView(RecordExportAPIView):
    module = 'activities'
    model = models.Activity
    serializer_class = serializers.ActivitySerializer


class CourseListAPIView(RecordListAPIView):
    module = 'courses'
    model = models.Course
    serializer_class = serializers.CourseSerializer


class CourseDetailAPIView(RecordDetailAPIView):
    module = 'courses'
    model = models.Course
    serializer_class = serializers.CourseSerializer


class CourseExportAPIView(RecordExportAPIView):
    module = 'courses'
    model = models.Course
    serializer_class = serializers.CourseSerializer


class AcademicYearListAPIView(RecordListAPIView):
    module = 'academic_years'
    model = models.AcademicYear
    serializer_class = serializers.AcademicYearSerializer


class AcademicYearDetailAPIView(RecordDetailAPIView):
    module = 'academic_years'
    model = models.AcademicYear
    serializer_class = serializers.AcademicYearSerializer


class AcademicYearExportAPIView(RecordExportAPIView):
    module = 'academic_years'
    model = models.AcademicYear
    serializer_class = serializers.AcademicYearSerializer
