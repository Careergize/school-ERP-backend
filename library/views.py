from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class BookListAPIView(RecordListAPIView):
    module = 'books'
    model = models.Book
    serializer_class = serializers.BookSerializer


class BookDetailAPIView(RecordDetailAPIView):
    module = 'books'
    model = models.Book
    serializer_class = serializers.BookSerializer


class BookExportAPIView(RecordExportAPIView):
    module = 'books'
    model = models.Book
    serializer_class = serializers.BookSerializer


class LoanListAPIView(RecordListAPIView):
    module = 'loans'
    model = models.Loan
    serializer_class = serializers.LoanSerializer


class LoanDetailAPIView(RecordDetailAPIView):
    module = 'loans'
    model = models.Loan
    serializer_class = serializers.LoanSerializer


class LoanExportAPIView(RecordExportAPIView):
    module = 'loans'
    model = models.Loan
    serializer_class = serializers.LoanSerializer
