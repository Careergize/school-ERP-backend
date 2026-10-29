from django.urls import path
from . import views

app_name='assistant'
urlpatterns=[
    path('capabilities/',views.CapabilitiesAPIView.as_view(),name='capabilities'),
    path('conversations/',views.ConversationAPIView.as_view(),name='conversation-list'),
    path('conversations/<uuid:identifier>/',views.ConversationDetailAPIView.as_view(),name='conversation-detail'),
    path('chat/',views.ChatAPIView.as_view(),name='chat'),
    path('results/<uuid:identifier>/',views.ResultAPIView.as_view(),name='result'),
    path('reports/',views.ReportAPIView.as_view(),name='report-create'),
    path('reports/<uuid:identifier>/',views.ReportStatusAPIView.as_view(),name='report-status'),
    path('reports/<uuid:identifier>/download/',views.ReportDownloadAPIView.as_view(),name='report-download'),
]
