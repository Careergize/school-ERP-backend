from django.urls import path
from .views import (
    LessonListAPIView,
    LessonDetailAPIView,
    LessonExportAPIView
)

app_name = 'timetable'
urlpatterns = [
    path('', LessonListAPIView.as_view(), name='timetable-list'),
    path('export/', LessonExportAPIView.as_view(), name='timetable-export'),
    path('<int:rid>/', LessonDetailAPIView.as_view(), name='timetable-detail'),
]
