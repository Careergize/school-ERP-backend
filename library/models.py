from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from core.models import RecordModel


class Book(RecordModel):
    name = models.CharField('Book title', max_length=255)
    author = models.CharField('Author', max_length=255)
    isbn = models.CharField('ISBN', max_length=255, unique=True)
    copies = models.PositiveIntegerField('Total copies')
    shelf = models.CharField('Shelf', max_length=255)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.pk and self.loans.filter(returned__isnull=True).count() > self.copies:
            raise ValidationError('Copies cannot be fewer than active loans.', code='conflict')


class Loan(RecordModel):
    book = models.ForeignKey('library.Book', verbose_name='Book', on_delete=models.PROTECT, related_name='loans')
    student = models.ForeignKey('students.Student', verbose_name='Student', on_delete=models.PROTECT, related_name='loans_student')
    issued = models.DateField('Issue date')
    due = models.DateField('Return due')
    returned = models.DateField('Returned on', null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['due', 'returned'])]
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(condition=Q(due__gte=F('issued')), name='library_loan_due_after_issue'),
            models.CheckConstraint(condition=Q(returned__isnull=True) | Q(returned__gte=F('issued')), name='library_loan_return_after_issue'),
        ]

    def __str__(self):
        return f"Loan #{self.pk}"

    def clean(self):
        super().clean()
        if self.issued and self.due and (self.due < self.issued or (self.returned and self.returned < self.issued)):
            raise ValidationError('Loan return dates cannot precede the issue date.')
        if self.book_id and not self.returned and Loan.objects.filter(book_id=self.book_id, returned__isnull=True).exclude(pk=self.pk).count() >= self.book.copies:
            raise ValidationError('No book copies are available.', code='conflict')
