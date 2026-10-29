from django.urls import path
from .views import (
    RouteListAPIView,
    RouteDetailAPIView,
    RouteExportAPIView,
    TransportAllocationListAPIView,
    TransportAllocationDetailAPIView,
    TransportAllocationExportAPIView
)

app_name = 'transport'
urlpatterns = [
    path('routes/', RouteListAPIView.as_view(), name='transport-list'),
    path('routes/export/', RouteExportAPIView.as_view(), name='transport-export'),
    path('routes/<int:rid>/', RouteDetailAPIView.as_view(), name='transport-detail'),
    path('allocations/', TransportAllocationListAPIView.as_view(), name='transport_allocations-list'),
    path('allocations/export/', TransportAllocationExportAPIView.as_view(), name='transport_allocations-export'),
    path('allocations/<int:rid>/', TransportAllocationDetailAPIView.as_view(), name='transport_allocations-detail'),
]
