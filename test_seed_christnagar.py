"""The school seeder must remain complete, consistent, and safe to rerun."""
from io import StringIO
from decimal import Decimal
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Count, Sum
from django.test import TestCase
from core.registry import MODULES
from students.models import Student, Guardian, Enrollment
from academics.models import Batch
from configuration.models import SchoolSettings
from finance.models import Invoice, Receipt
from library.models import Loan, Book
from timetable.models import Lesson
from core.models import AuditEvent


class ChristnagarSeedTests(TestCase):
    def test_complete_seed_preserves_existing_records_and_is_idempotent(self):
        original=Guardian.objects.create(name='Existing guardian',email='existing@example.com',phone='0000000000',relationship='Guardian')
        school=SchoolSettings.objects.create(name='Existing school',email='office@existing.example',phone='0000012345',currency='INR',timezone='Asia/Kolkata')
        get_user_model().objects.create_superuser(email='admin@existing.example',name='Existing administrator',password='Existing-password-928!')
        output=StringIO()
        call_command('seed_christnagar',no_backup=True,as_of='2026-10-28',stdout=output)
        self.assertEqual(Student.objects.count(),100)
        self.assertEqual(Batch.objects.count(),10)
        self.assertEqual(set(Batch.objects.annotate(total=Count('students')).values_list('total',flat=True)),{10})
        self.assertEqual(Student.objects.filter(parent__isnull=False).count(),100)
        self.assertEqual(Enrollment.objects.filter(status='Active').count(),100)
        self.assertTrue(Guardian.objects.filter(pk=original.pk,name='Existing guardian').exists())
        school.refresh_from_db()
        self.assertEqual(school.name,'Christnagar School')
        self.assertEqual(school.email,'office@existing.example')
        self.assertEqual(school.phone,'0000012345')
        for key,config in MODULES.items():
            self.assertGreater(apps.get_model(config['model']).objects.count(),0,key)
        self.assertEqual(Lesson.objects.count(),300)
        self.assertEqual(Invoice.objects.count(),300)
        self.assertEqual(Receipt.objects.count(),190)
        for invoice in Invoice.objects.all():
            self.assertLessEqual(invoice.receipts.aggregate(total=Sum('amount'))['total'] or Decimal('0'),invoice.amount)
        for book in Book.objects.all():
            self.assertLessEqual(book.loans.filter(returned__isnull=True).count(),book.copies)
        accounts=get_user_model().objects.filter(email__endswith='@christnagar.example')
        self.assertEqual(accounts.count(),228)
        self.assertFalse(accounts.filter(is_active=True).exists())
        self.assertTrue(all(not account.has_usable_password() for account in accounts))
        counts={key:apps.get_model(config['model']).objects.count() for key,config in MODULES.items()}
        user_count=get_user_model().objects.count();audit_count=AuditEvent.objects.count()
        call_command('seed_christnagar',no_backup=True,as_of='2026-10-28',stdout=StringIO())
        self.assertEqual(counts,{key:apps.get_model(config['model']).objects.count() for key,config in MODULES.items()})
        self.assertEqual(user_count,get_user_model().objects.count())
        self.assertEqual(audit_count,AuditEvent.objects.count())
