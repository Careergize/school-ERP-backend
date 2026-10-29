from django.urls import path
from .views import (
    StaffListAPIView,
    StaffDetailAPIView,
    StaffExportAPIView,
    PayslipListAPIView,
    PayslipDetailAPIView,
    PayslipExportAPIView,
    PerformanceReviewListAPIView,
    PerformanceReviewDetailAPIView,
    PerformanceReviewExportAPIView
)

app_name = 'hr'
urlpatterns = [
    path('staff/', StaffListAPIView.as_view(), name='staff-list'),
    path('staff/export/', StaffExportAPIView.as_view(), name='staff-export'),
    path('staff/<int:rid>/', StaffDetailAPIView.as_view(), name='staff-detail'),
    path('payroll/', PayslipListAPIView.as_view(), name='payroll-list'),
    path('payroll/export/', PayslipExportAPIView.as_view(), name='payroll-export'),
    path('payroll/<int:rid>/', PayslipDetailAPIView.as_view(), name='payroll-detail'),
    path('reviews/', PerformanceReviewListAPIView.as_view(), name='reviews-list'),
    path('reviews/export/', PerformanceReviewExportAPIView.as_view(), name='reviews-export'),
    path('reviews/<int:rid>/', PerformanceReviewDetailAPIView.as_view(), name='reviews-detail'),
]
