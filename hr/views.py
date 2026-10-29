from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class StaffListAPIView(RecordListAPIView):
    module = 'staff'
    model = models.Staff
    serializer_class = serializers.StaffSerializer


class StaffDetailAPIView(RecordDetailAPIView):
    module = 'staff'
    model = models.Staff
    serializer_class = serializers.StaffSerializer


class StaffExportAPIView(RecordExportAPIView):
    module = 'staff'
    model = models.Staff
    serializer_class = serializers.StaffSerializer


class PayslipListAPIView(RecordListAPIView):
    module = 'payroll'
    model = models.Payslip
    serializer_class = serializers.PayslipSerializer


class PayslipDetailAPIView(RecordDetailAPIView):
    module = 'payroll'
    model = models.Payslip
    serializer_class = serializers.PayslipSerializer


class PayslipExportAPIView(RecordExportAPIView):
    module = 'payroll'
    model = models.Payslip
    serializer_class = serializers.PayslipSerializer


class PerformanceReviewListAPIView(RecordListAPIView):
    module = 'reviews'
    model = models.PerformanceReview
    serializer_class = serializers.PerformanceReviewSerializer


class PerformanceReviewDetailAPIView(RecordDetailAPIView):
    module = 'reviews'
    model = models.PerformanceReview
    serializer_class = serializers.PerformanceReviewSerializer


class PerformanceReviewExportAPIView(RecordExportAPIView):
    module = 'reviews'
    model = models.PerformanceReview
    serializer_class = serializers.PerformanceReviewSerializer
