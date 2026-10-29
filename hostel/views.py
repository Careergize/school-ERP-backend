from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class HostelRoomListAPIView(RecordListAPIView):
    module = 'hostels'
    model = models.HostelRoom
    serializer_class = serializers.HostelRoomSerializer


class HostelRoomDetailAPIView(RecordDetailAPIView):
    module = 'hostels'
    model = models.HostelRoom
    serializer_class = serializers.HostelRoomSerializer


class HostelRoomExportAPIView(RecordExportAPIView):
    module = 'hostels'
    model = models.HostelRoom
    serializer_class = serializers.HostelRoomSerializer


class HostelAllocationListAPIView(RecordListAPIView):
    module = 'hostel_allocations'
    model = models.HostelAllocation
    serializer_class = serializers.HostelAllocationSerializer


class HostelAllocationDetailAPIView(RecordDetailAPIView):
    module = 'hostel_allocations'
    model = models.HostelAllocation
    serializer_class = serializers.HostelAllocationSerializer


class HostelAllocationExportAPIView(RecordExportAPIView):
    module = 'hostel_allocations'
    model = models.HostelAllocation
    serializer_class = serializers.HostelAllocationSerializer
