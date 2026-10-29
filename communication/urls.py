from django.urls import path
from .views import (
    NoticeListAPIView,
    NoticeDetailAPIView,
    NoticeExportAPIView,
    MessageListAPIView,
    MessageDetailAPIView,
    MessageExportAPIView
)

app_name = 'communication'
urlpatterns = [
    path('notices/', NoticeListAPIView.as_view(), name='notices-list'),
    path('notices/export/', NoticeExportAPIView.as_view(), name='notices-export'),
    path('notices/<int:rid>/', NoticeDetailAPIView.as_view(), name='notices-detail'),
    path('messages/', MessageListAPIView.as_view(), name='messages-list'),
    path('messages/export/', MessageExportAPIView.as_view(), name='messages-export'),
    path('messages/<int:rid>/', MessageDetailAPIView.as_view(), name='messages-detail'),
]
