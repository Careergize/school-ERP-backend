from django.urls import path
from .api import HealthAPIView

app_name = 'core'
urlpatterns = [path('health/', HealthAPIView.as_view(), name='health')]
