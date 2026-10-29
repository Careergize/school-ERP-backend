from django.urls import path
from .views import (
    StudentListAPIView,
    StudentDetailAPIView,
    StudentExportAPIView,
    GuardianListAPIView,
    GuardianDetailAPIView,
    GuardianExportAPIView,
    EnrollmentListAPIView,
    EnrollmentDetailAPIView,
    EnrollmentExportAPIView
)

app_name = 'students'
urlpatterns = [
    path('', StudentListAPIView.as_view(), name='students-list'),
    path('export/', StudentExportAPIView.as_view(), name='students-export'),
    path('<int:rid>/', StudentDetailAPIView.as_view(), name='students-detail'),
    path('guardians/', GuardianListAPIView.as_view(), name='parents-list'),
    path('guardians/export/', GuardianExportAPIView.as_view(), name='parents-export'),
    path('guardians/<int:rid>/', GuardianDetailAPIView.as_view(), name='parents-detail'),
    path('enrollments/', EnrollmentListAPIView.as_view(), name='enrollments-list'),
    path('enrollments/export/', EnrollmentExportAPIView.as_view(), name='enrollments-export'),
    path('enrollments/<int:rid>/', EnrollmentDetailAPIView.as_view(), name='enrollments-detail'),
]
