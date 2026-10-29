from django.urls import path
from .views import (
    AttendanceListAPIView,
    AttendanceDetailAPIView,
    AttendanceExportAPIView
)

app_name = 'attendance'
urlpatterns = [
    path('', AttendanceListAPIView.as_view(), name='attendance-list'),
    path('export/', AttendanceExportAPIView.as_view(), name='attendance-export'),
    path('<int:rid>/', AttendanceDetailAPIView.as_view(), name='attendance-detail'),
]
