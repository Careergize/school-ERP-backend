from django.urls import path
from .views import (
    InvoiceListAPIView,
    InvoiceDetailAPIView,
    InvoiceExportAPIView,
    ReceiptListAPIView,
    ReceiptDetailAPIView,
    ReceiptExportAPIView
)

app_name = 'finance'
urlpatterns = [
    path('invoices/', InvoiceListAPIView.as_view(), name='fees-list'),
    path('invoices/export/', InvoiceExportAPIView.as_view(), name='fees-export'),
    path('invoices/<int:rid>/', InvoiceDetailAPIView.as_view(), name='fees-detail'),
    path('receipts/', ReceiptListAPIView.as_view(), name='payments-list'),
    path('receipts/export/', ReceiptExportAPIView.as_view(), name='payments-export'),
    path('receipts/<int:rid>/', ReceiptDetailAPIView.as_view(), name='payments-detail'),
]
