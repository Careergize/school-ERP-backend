from django.urls import path
from .views import (
    HostelRoomListAPIView,
    HostelRoomDetailAPIView,
    HostelRoomExportAPIView,
    HostelAllocationListAPIView,
    HostelAllocationDetailAPIView,
    HostelAllocationExportAPIView
)

app_name = 'hostel'
urlpatterns = [
    path('rooms/', HostelRoomListAPIView.as_view(), name='hostels-list'),
    path('rooms/export/', HostelRoomExportAPIView.as_view(), name='hostels-export'),
    path('rooms/<int:rid>/', HostelRoomDetailAPIView.as_view(), name='hostels-detail'),
    path('allocations/', HostelAllocationListAPIView.as_view(), name='hostel_allocations-list'),
    path('allocations/export/', HostelAllocationExportAPIView.as_view(), name='hostel_allocations-export'),
    path('allocations/<int:rid>/', HostelAllocationDetailAPIView.as_view(), name='hostel_allocations-detail'),
]
