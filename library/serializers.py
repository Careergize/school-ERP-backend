from django.apps import apps
from rest_framework import serializers
from core.serializers import RecordSerializer
from . import models


class BookSerializer(RecordSerializer):
    available_copies = serializers.SerializerMethodField()

    def get_available_copies(self, instance):
        return instance.copies - instance.loans.filter(returned__isnull=True).count()

    class Meta:
        model = models.Book
        fields = ['id', 'version', 'name', 'author', 'isbn', 'copies', 'available_copies', 'shelf', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class LoanSerializer(RecordSerializer):
    loan_status = serializers.SerializerMethodField()

    def get_loan_status(self, instance):
        from django.utils import timezone
        return 'Returned' if instance.returned else 'Overdue' if instance.due < timezone.localdate() else 'On loan'

    book_id = serializers.PrimaryKeyRelatedField(source='book', queryset=apps.get_model('library.Book').objects.all(), required=True, allow_null=False)
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=True, allow_null=False)

    class Meta:
        model = models.Loan
        fields = ['id', 'version', 'book_id', 'student_id', 'issued', 'due', 'returned', 'loan_status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
