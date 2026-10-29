from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class RouteListAPIView(RecordListAPIView):
    module = 'transport'
    model = models.Route
    serializer_class = serializers.RouteSerializer


class RouteDetailAPIView(RecordDetailAPIView):
    module = 'transport'
    model = models.Route
    serializer_class = serializers.RouteSerializer


class RouteExportAPIView(RecordExportAPIView):
    module = 'transport'
    model = models.Route
    serializer_class = serializers.RouteSerializer


class TransportAllocationListAPIView(RecordListAPIView):
    module = 'transport_allocations'
    model = models.TransportAllocation
    serializer_class = serializers.TransportAllocationSerializer


class TransportAllocationDetailAPIView(RecordDetailAPIView):
    module = 'transport_allocations'
    model = models.TransportAllocation
    serializer_class = serializers.TransportAllocationSerializer


class TransportAllocationExportAPIView(RecordExportAPIView):
    module = 'transport_allocations'
    model = models.TransportAllocation
    serializer_class = serializers.TransportAllocationSerializer
