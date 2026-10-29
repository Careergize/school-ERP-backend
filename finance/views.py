from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class InvoiceListAPIView(RecordListAPIView):
    module = 'fees'
    model = models.Invoice
    serializer_class = serializers.InvoiceSerializer


class InvoiceDetailAPIView(RecordDetailAPIView):
    module = 'fees'
    model = models.Invoice
    serializer_class = serializers.InvoiceSerializer


class InvoiceExportAPIView(InvoiceListAPIView):
    module = 'fees'
    model = models.Invoice
    serializer_class = serializers.InvoiceSerializer

    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        from core.services import export
        return export(self.module, self.erp_user, queryset=self.get_queryset())


class ReceiptListAPIView(RecordListAPIView):
    module = 'payments'
    model = models.Receipt
    serializer_class = serializers.ReceiptSerializer


class ReceiptDetailAPIView(RecordDetailAPIView):
    module = 'payments'
    model = models.Receipt
    serializer_class = serializers.ReceiptSerializer


class ReceiptExportAPIView(RecordExportAPIView):
    module = 'payments'
    model = models.Receipt
    serializer_class = serializers.ReceiptSerializer
