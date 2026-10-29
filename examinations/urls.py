from django.urls import path
from .views import (
    ExamListAPIView,
    ExamDetailAPIView,
    ExamExportAPIView,
    ResultListAPIView,
    ResultDetailAPIView,
    ResultExportAPIView
)

app_name = 'examinations'
urlpatterns = [
    path('exams/', ExamListAPIView.as_view(), name='exams-list'),
    path('exams/export/', ExamExportAPIView.as_view(), name='exams-export'),
    path('exams/<int:rid>/', ExamDetailAPIView.as_view(), name='exams-detail'),
    path('results/', ResultListAPIView.as_view(), name='results-list'),
    path('results/export/', ResultExportAPIView.as_view(), name='results-export'),
    path('results/<int:rid>/', ResultDetailAPIView.as_view(), name='results-detail'),
]
