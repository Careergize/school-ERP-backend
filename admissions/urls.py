from django.urls import path
from .views import (
    ApplicationListAPIView,
    ApplicationDetailAPIView,
    ApplicationExportAPIView,
    EnrollAPIView
)

app_name = 'admissions'
urlpatterns = [
    path('', ApplicationListAPIView.as_view(), name='admissions-list'),
    path('export/', ApplicationExportAPIView.as_view(), name='admissions-export'),
    path('<int:rid>/', ApplicationDetailAPIView.as_view(), name='admissions-detail'),
    path('<int:rid>/enroll/', EnrollAPIView.as_view(), name='enroll'),
]
