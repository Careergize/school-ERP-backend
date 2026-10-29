from django.urls import path
from .views import SummaryAPIView, WorkspaceSnapshotAPIView, AuditLogAPIView

app_name = 'reporting'
urlpatterns = [
    path('summary/', SummaryAPIView.as_view(), name='summary'),
    path('snapshot/', WorkspaceSnapshotAPIView.as_view(), name='snapshot'),
    path('audit/', AuditLogAPIView.as_view(), name='audit'),
]
