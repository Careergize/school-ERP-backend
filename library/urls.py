from django.urls import path
from .views import (
    BookListAPIView,
    BookDetailAPIView,
    BookExportAPIView,
    LoanListAPIView,
    LoanDetailAPIView,
    LoanExportAPIView
)

app_name = 'library'
urlpatterns = [
    path('books/', BookListAPIView.as_view(), name='books-list'),
    path('books/export/', BookExportAPIView.as_view(), name='books-export'),
    path('books/<int:rid>/', BookDetailAPIView.as_view(), name='books-detail'),
    path('loans/', LoanListAPIView.as_view(), name='loans-list'),
    path('loans/export/', LoanExportAPIView.as_view(), name='loans-export'),
    path('loans/<int:rid>/', LoanDetailAPIView.as_view(), name='loans-detail'),
]
