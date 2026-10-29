"""Model-backed API and database constraint regression tests."""
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from core.registry import MODULES
from finance.models import Invoice
from students.models import Student, Enrollment
from accounts.models import AccessSession


class ERPWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password='Test-only-password-928!'
        cls.admin=get_user_model().objects.create_superuser(email='admin@school.local',name='Admin',password=cls.password)

    def setUp(self):
        self.client=APIClient()
        response=self.client.post('/api/v1/accounts/login/',{'email':self.admin.email,'password':self.password},format='json')
        self.assertEqual(response.status_code,200,response.content)
        self.token=response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+self.token)
        self.staff=self.create('staff',dict(name='Teacher',email='teacher@school.local',phone='123',designation='Teacher',department='Science',salary='30000.00',joined='2026-01-01'))
        self.room=self.create('rooms',dict(name='Room 1',building='Main',capacity=30,type='Classroom'))
        self.batch=self.create('classes',dict(name='Grade 1 A',year='2026-27',teacher_id=self.staff['id'],capacity=3,room_id=self.room['id']))
        self.subject=self.create('subjects',dict(name='Science',code='SCI',class_id=self.batch['id'],teacher_id=self.staff['id']))
        self.student=self.create('students',dict(name='Student One',roll='A1',class_id=self.batch['id'],dob='2018-01-01',gender='Other',status='Active'))

    def url(self,module,rid=None):
        return '/api/'+MODULES[module]['endpoint']+(str(rid)+'/' if rid is not None else '')

    def create(self,module,body):
        response=self.client.post(self.url(module),body,format='json')
        self.assertEqual(response.status_code,201,response.content)
        return response.data

    def test_apps_routes_and_model_metadata(self):
        for module,config in MODULES.items():
            response=self.client.get(self.url(module))
            self.assertEqual(response.status_code,200,(module,response.content))
            self.assertIn('results',response.data)
        catalog=self.client.get('/api/v1/configuration/modules/')
        self.assertEqual(catalog.status_code,200,catalog.content)
        self.assertEqual(set(catalog.data),set(MODULES))
        fields={field['key']:field for field in catalog.data['students']['fields']}
        self.assertEqual(fields['class_id']['type'],'ref:classes')
        self.assertNotIn('password',str(catalog.data))
        self.assertEqual(reverse('students:students-list'),self.url('students'))
        self.assertEqual(APIClient().get(self.url('students')).status_code,401)
        self.assertEqual(self.client.patch(self.url('students',self.student['id']),{},format='json').status_code,405)
        self.assertEqual(self.client.get(self.url('students')+'?page_size=101').status_code,400)
        self.assertEqual(self.client.get(self.url('students')+'?search=Student%20One').data['count'],1)
        self.assertEqual(self.client.get(self.url('students')+'?search=missing').data['count'],0)

    def test_versions_relationships_and_history(self):
        self.assertTrue(Enrollment.objects.filter(student_id=self.student['id'],school_class_id=self.batch['id'],status='Active').exists())
        changed={**self.student,'name':'Updated Student'}
        response=self.client.put(self.url('students',self.student['id']),changed,format='json')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.data['version'],2)
        self.assertEqual(self.client.put(self.url('students',self.student['id']),changed,format='json').status_code,409)
        self.assertEqual(self.client.delete(self.url('classes',self.batch['id'])).status_code,409)
        self.assertEqual(self.client.get(self.url('students',999999)).status_code,404)
        second=self.create('classes',dict(name='Grade 2 A',year='2027-28',teacher_id=self.staff['id'],capacity=3))
        changed={**response.data,'class_id':second['id']}
        moved=self.client.put(self.url('students',self.student['id']),changed,format='json')
        self.assertEqual(moved.status_code,200,moved.content)
        self.assertEqual(Enrollment.objects.filter(student_id=self.student['id']).count(),2)
        self.assertEqual(Enrollment.objects.get(student_id=self.student['id'],school_class_id=self.batch['id']).status,'Transferred')

    def test_admissions_enrollment_and_capacity(self):
        application=self.create('admissions',dict(name='Applicant',class_id=self.batch['id'],email='parent@school.local',phone='123',dob='2018-01-01',status='Applied'))
        endpoint=self.url('admissions',application['id'])+'enroll/'
        response=self.client.post(endpoint)
        self.assertEqual(response.status_code,201,response.content)
        self.assertEqual(Student.objects.count(),2)
        self.assertEqual(self.client.post(endpoint).status_code,409)
        self.create('students',dict(name='Third',roll='A3',class_id=self.batch['id'],dob='2018-01-01',gender='Other',status='Active'))
        rejected=self.client.post(self.url('students'),dict(name='Fourth',roll='A4',class_id=self.batch['id'],dob='2018-01-01',gender='Other',status='Active'),format='json')
        self.assertEqual(rejected.status_code,409,rejected.content)

    def test_decimal_fees_receipts_and_reports(self):
        invoice=self.create('fees',dict(name='Term 1',student_id=self.student['id'],amount='0.30',due='2026-11-01'))
        self.create('payments',dict(invoice_id=invoice['id'],amount='0.10',date='2026-10-01',method='Cash'))
        self.create('payments',dict(invoice_id=invoice['id'],amount='0.20',date='2026-10-01',method='Bank transfer'))
        response=self.client.post(self.url('payments'),dict(invoice_id=invoice['id'],amount='0.01',date='2026-10-01',method='Cash'),format='json')
        self.assertEqual(response.status_code,409,response.content)
        self.assertEqual(Invoice.objects.get(pk=invoice['id']).amount,Decimal('0.30'))
        report=self.client.get('/api/v1/reporting/summary/')
        self.assertEqual(report.status_code,200,report.content)
        self.assertEqual(Decimal(report.data['finance']['outstanding']),Decimal('0.00'))
        self.assertEqual(self.client.delete(self.url('fees',invoice['id'])).status_code,409)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Invoice.objects.create(name='Invalid',student_id=self.student['id'],amount=-1,due='2026-11-01')

    def test_exams_attendance_and_timetable(self):
        exam=self.create('exams',dict(name='Term 1',class_id=self.batch['id'],subject_id=self.subject['id'],date='2026-11-01',max_marks=100,pass_marks=40))
        result=self.create('results',dict(student_id=self.student['id'],exam_id=exam['id'],marks=85))
        invalid=self.client.post(self.url('results'),dict(student_id=self.student['id'],exam_id=exam['id'],marks=101),format='json')
        self.assertIn(invalid.status_code,[409,422])
        attendance=dict(student_id=self.student['id'],date=timezone.localdate().isoformat(),status='Present')
        self.create('attendance',attendance)
        self.assertEqual(self.client.post(self.url('attendance'),attendance,format='json').status_code,409)
        attendance['date']=(timezone.localdate()+timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post(self.url('attendance'),attendance,format='json').status_code,422)
        lesson=dict(name='Science lesson',class_id=self.batch['id'],subject_id=self.subject['id'],teacher_id=self.staff['id'],day='Monday',start='09:00',end='10:00',room_id=self.room['id'])
        self.create('timetable',lesson)
        lesson.update(start='09:30',end='10:30')
        self.assertEqual(self.client.post(self.url('timetable'),lesson,format='json').status_code,409)

    def test_library_transport_hostel_and_payroll(self):
        book=self.create('books',dict(name='Science',author='Author',isbn='123',copies=1,shelf='A'))
        loan=dict(book_id=book['id'],student_id=self.student['id'],issued='2026-10-01',due='2026-10-15')
        borrowed=self.create('loans',loan)
        self.assertEqual(self.client.post(self.url('loans'),loan,format='json').status_code,409)
        returned=self.client.put(self.url('loans',borrowed['id']),{**borrowed,'returned':'2026-10-10'},format='json')
        self.assertEqual(returned.status_code,200,returned.content)
        self.create('loans',loan)
        route=self.create('transport',dict(name='North',vehicle='BUS-01',driver='Driver',phone='123',capacity=1,stops='Main Road'))
        self.create('transport_allocations',dict(student_id=self.student['id'],route_id=route['id'],stop='Main Road'))
        hostel=self.create('hostels',dict(name='101',building='A',capacity=1,warden='Warden'))
        allocation=dict(student_id=self.student['id'],hostel_id=hostel['id'],from_date='2026-10-01',to_date='2026-11-01')
        self.create('hostel_allocations',allocation)
        self.assertEqual(self.client.post(self.url('hostel_allocations'),allocation,format='json').status_code,409)
        payslip=self.create('payroll',dict(staff_id=self.staff['id'],month='2026-10',basic='30000.00',allowances='1000.00',deductions='500.00',status='Draft'))
        self.assertEqual(self.client.post(self.url('payroll'),dict(staff_id=self.staff['id'],month='invalid',basic='100',allowances='0',deductions='0',status='Draft'),format='json').status_code,422)
        self.create('reviews',dict(staff_id=self.staff['id'],date='2026-10-01',rating=4,description='Review'))
        report=self.client.get('/api/v1/reporting/summary/')
        self.assertEqual(Decimal(report.data['payroll']['net_total']),Decimal('30500'))

    def test_scoped_accounts_exports_and_session_revocation(self):
        other=self.create('students',dict(name='Other Student',roll='A2',class_id=self.batch['id'],dob='2018-01-01',gender='Other',status='Active'))
        body=dict(name='Student account',email='student@school.local',password='Student-password-928!',role='student',student_id=self.student['id'])
        self.assertEqual(self.client.post('/api/v1/accounts/users/',body,format='json').status_code,201)
        client=APIClient();login=client.post('/api/v1/accounts/login/',{'email':body['email'],'password':body['password']},format='json')
        self.assertEqual(login.status_code,200,login.content)
        client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['token'])
        self.assertEqual(client.get(self.url('students')).data['count'],1)
        self.assertEqual(client.get(self.url('students',other['id'])).status_code,404)
        self.assertEqual(client.get('/api/v1/accounts/users/').status_code,403)
        self.assertEqual(client.post(self.url('books'),{},format='json').status_code,403)
        export=client.get('/api/'+MODULES['students']['export_endpoint'])
        self.assertEqual(export.status_code,200)
        self.assertNotIn(b'Other Student',export.content)
        self.assertEqual(client.post('/api/v1/accounts/logout/').status_code,200)
        self.assertEqual(client.get('/api/v1/accounts/me/').status_code,401)
        self.assertNotEqual(get_user_model().objects.get(email=body['email']).password,body['password'])

    def test_legacy_routes_and_safe_deletion(self):
        self.assertEqual(self.client.get('/api/data').status_code,200)
        self.assertEqual(self.client.get('/api/catalog').status_code,200)
        self.assertEqual(self.client.get('/api/export/students').status_code,200)
        book=self.create('books',dict(name='Disposable',author='Author',isbn='456',copies=1,shelf='B'))
        self.assertEqual(self.client.delete(self.url('books',book['id'])).status_code,204)
        self.assertEqual(self.client.get(self.url('books',book['id'])).status_code,404)


    def test_teacher_communication_ownership(self):
        body=dict(name='Faculty account',email='faculty@school.local',password='School-access-928!',role='teacher',staff_id=self.staff['id'])
        self.assertEqual(self.client.post('/api/v1/accounts/users/',body,format='json').status_code,201)
        teacher=APIClient()
        login=teacher.post('/api/v1/accounts/login/',{'email':body['email'],'password':body['password']},format='json')
        self.assertEqual(login.status_code,200,login.content)
        teacher.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['token'])
        response=teacher.post(self.url('notices'),{'name':'Class update','date':'2026-10-01','audience':'Students','description':'Bring your workbook.'},format='json')
        self.assertEqual(response.status_code,201,response.content)
        self.assertEqual(teacher.get(self.url('notices')).data['count'],1)
        updated=teacher.put(self.url('notices',response.data['id']),{**response.data,'description':'Bring your science workbook.'},format='json')
        self.assertEqual(updated.status_code,200,updated.content)
        admin_notice=self.create('notices',dict(name='Staff notice',date='2026-10-01',audience='Staff',description='Staff update'))
        changed={**admin_notice,'audience':'Students'}
        self.assertEqual(teacher.put(self.url('notices',admin_notice['id']),changed,format='json').status_code,403)


    def test_frontend_filters_defaults_and_computed_fields(self):
        catalog=self.client.get('/api/v1/configuration/modules/').data
        self.assertEqual(next(field for field in catalog['payments']['fields'] if field['key']=='method')['default'],'Cash')
        self.assertFalse(catalog['payments']['fields'][0]['required'] is False)
        self.assertEqual(self.client.get(self.url('subjects')+'?class_id='+str(self.batch['id'])).data['count'],1)
        self.assertEqual(self.client.get(self.url('subjects')+'?class_id=999999').data['count'],0)
        self.assertEqual(self.client.get(self.url('subjects')+'?class_id=bad').status_code,400)
        self.assertEqual(self.client.get(self.url('subjects')+'?unknown=1').status_code,400)
        invoice=self.create('fees',dict(name='Term invoice',student_id=self.student['id'],amount='100.00',due='2026-11-01'))
        self.assertEqual(invoice['balance'],'100.00')
        self.assertEqual(invoice['payment_status'],'Unpaid')
        self.create('payments',dict(invoice_id=invoice['id'],amount='25.00',date='2026-10-01',method='Cash'))
        invoice=self.client.get(self.url('fees',invoice['id'])).data
        self.assertEqual(invoice['paid_amount'],'25.00')
        self.assertEqual(invoice['balance'],'75.00')
        self.assertEqual(invoice['payment_status'],'Partial')
        book=self.create('books',dict(name='Book',author='Author',isbn='TEST',copies=1,shelf='B'))
        self.assertEqual(book['available_copies'],1)
        loan=self.create('loans',dict(book_id=book['id'],student_id=self.student['id'],issued='2026-01-01',due='2026-01-10'))
        self.assertEqual(loan['loan_status'],'Overdue')
        self.assertEqual(self.client.get(self.url('books',book['id'])).data['available_copies'],0)
