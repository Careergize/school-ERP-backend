"""Assistant calculations, privacy boundaries, follow-ups, and PDF regressions."""
from datetime import date,timedelta
from decimal import Decimal
from io import StringIO,BytesIO
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Sum,Avg,Count,Q
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from pypdf import PdfReader
from core.registry import MODULES
from students.models import Student,Guardian
from hr.models import Staff
from attendance.models import Attendance
from finance.models import Invoice,Receipt
from examinations.models import Result
from .models import Conversation,QueryResult,Report,QueryAudit
from .registry import ALIASES,registry
from .engine import QueryEngine
from .plans import QueryProblem,validate_plan


@override_settings(ASSISTANT_CHAT_RATE=1000,ASSISTANT_REPORT_RATE=100)
class AssistantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=get_user_model().objects.create_superuser(email='assistant.admin@example.com',name='Assistant test administrator',password='Test-administrator-928!')
        call_command('seed_christnagar',no_backup=True,as_of='2026-10-28',stdout=StringIO())
        cls.child=Student.objects.order_by('id').first()
        cls.other=Student.objects.exclude(pk=cls.child.pk).first()
        cls.parent=get_user_model().objects.create_user(email='assistant.parent@example.com',name='Parent account',password='Parent-test-only-928!',role='parent',parent=cls.child.parent)
        cls.student=get_user_model().objects.create_user(email='assistant.student@example.com',name='Student account',password='Student-test-only-928!',role='student',student=cls.child)
        cls.teacher=get_user_model().objects.create_user(email='assistant.teacher@example.com',name='Teacher account',password='Teacher-test-only-928!',role='teacher',staff=cls.child.school_class.teacher)
        cls.accountant=get_user_model().objects.create_user(email='assistant.accountant@example.com',name='Accountant account',password='Accountant-test-only-928!',role='accountant')

    def setUp(self):
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.patch=patch('assistant.engine.timezone.localdate',return_value=date(2026,10,28));self.patch.start();self.addCleanup(self.patch.stop)

    def ask(self,question,client=None,conversation=None):
        response=(client or self.client).post('/api/v1/assistant/chat/',{'message':question,'conversation_id':conversation},format='json')
        self.assertEqual(response.status_code,200,response.content)
        return response.data

    def as_user(self,user):
        client=APIClient();client.force_authenticate(user);return client

    def report(self,result,client=None,mode='detailed'):
        response=(client or self.client).post('/api/v1/assistant/reports/',{'result_id':result['result_id'],'mode':mode},format='json')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.data['status'],'ready',response.data)
        return response.data

    def test_authentication_and_discovery_exclude_system_models(self):
        self.assertEqual(APIClient().get('/api/v1/assistant/capabilities/').status_code,401)
        response=self.client.get('/api/v1/assistant/capabilities/')
        self.assertEqual(response.status_code,200)
        self.assertEqual({item['key'] for item in response.data['resources']},set(MODULES))
        self.assertFalse(response.data['external_provider'])
        for item in response.data['resources']:
            self.assertNotIn('password',[field['name'] for field in item['fields']])
        self.assertNotIn('accounts',str(response.data['resources']))

    def test_module_help_and_suggestions(self):
        for key in registry({'id':self.admin.pk,'role':'admin'}):
            spec=registry({'id':self.admin.pk,'role':'admin'})[key]
            result=self.ask('Help with '+spec.aliases[0])
            self.assertEqual(result['kind'],'help',(key,result))
            self.assertEqual(result['guidance']['module'],key)
            self.assertTrue(result['guidance']['examples'])
        result=self.ask('How many faculty are not active?')
        self.assertEqual(result['kind'],'unavailable')
        self.assertIn('not stored',result['guidance']['limitations'][-1])
        result=self.ask('How many staff records are there?')
        self.assertEqual(result['kind'],'answer')
        self.assertEqual(result['guidance']['module'],'staff')

    def test_common_question_wording_and_filters(self):
        from .planner import LocalPlanner
        resources=registry({'id':self.admin.pk,'role':'admin'})
        cases=[
            ('How much faculty are there?','staff','count'),
            ('Count students class-wise','students','group'),
            ('How many students are not active?','students','count'),
            ('How many students are absent today?','attendance','count'),
            ('Show present attendance today','attendance','list'),
            ('Show books not returned','loans','list'),
            ('Show staff department "Science"','staff','list'),
            ('How many admissions last week?','admissions','count'),
            ('Show events this quarter','activities','list'),
        ]
        for question,resource,operation in cases:
            with self.subTest(question=question):
                plan=LocalPlanner().plan(question,{},resources)
                self.assertEqual(plan['resource'],resource)
                self.assertEqual(plan['operation'],operation)
                result=self.ask(question)
                self.assertEqual(result['kind'],'answer',result)
        plan=LocalPlanner().plan('How many students are not active?',{},resources)
        self.assertEqual(plan['filters'][0]['op'],'in')
        self.assertNotIn('Active',plan['filters'][0]['value'])
        plan=LocalPlanner().plan('Show books not returned',{},resources)
        self.assertIn({'field':'returned','op':'isnull','value':True},plan['filters'])
        result=self.ask('Why are students absent?')
        self.assertEqual(result['kind'],'unsupported')
        self.assertEqual(result['guidance']['module'],'attendance')
        result=self.ask('Show staff tomorrow')
        self.assertEqual(result['kind'],'clarification')
        self.assertEqual(result['guidance']['module'],'staff')

    def test_all_module_examples_are_executable(self):
        from .guidance import module_guidance
        for spec in registry({'id':self.admin.pk,'role':'admin'}).values():
            for question in module_guidance(spec)['examples']:
                with self.subTest(module=spec.key,question=question):
                    result=self.ask(question)
                    self.assertEqual(result['kind'],'answer',result)
                    self.assertEqual(result['guidance']['module'],spec.key)

    def test_general_help_only_suggests_permitted_modules(self):
        result=self.ask('What can you do?',self.as_user(self.student))
        self.assertEqual(result['kind'],'help')
        self.assertIn('Help with students',result['suggestions'])
        self.assertNotIn('Help with payroll',result['suggestions'])

    def test_module_help_respects_permissions_and_context(self):
        result=self.ask('Help with payroll',self.as_user(self.student))
        self.assertEqual(result['kind'],'forbidden')
        self.assertIsNone(result.get('guidance'))
        result=self.ask('How many students are currently enrolled?')
        self.ask('Help with staff',conversation=result['conversation_id'])
        follow=self.ask('Only Class 10',conversation=result['conversation_id'])
        self.assertEqual(follow['guidance']['module'],'students')

    def test_every_registered_module_is_queryable_without_a_rewrite(self):
        for module,config in MODULES.items():
            question='How many '+('staff' if module=='staff' else ALIASES[module][0])+' records are there?'
            result=self.ask(question)
            self.assertEqual(result['kind'],'answer',(module,result))
            expected=apps.get_model(config['model']).objects.count()
            self.assertEqual(int(result['summary'][0]['value']),expected,(module,result))

    def test_class_section_and_current_enrollment(self):
        result=self.ask('How many students are currently enrolled?')
        self.assertEqual(result['summary'][0]['value'],100)
        result=self.ask('Show students in Class 10, Section A.')
        self.assertEqual(result['total_rows'],10)
        self.assertTrue(all(row['class_id']=='Class 10 A' for row in result['rows']))
        self.assertEqual(self.ask('Show students in Class 10, Section B.')['kind'],'clarification')

    def test_outstanding_fees_are_exact_and_include_no_duplicate_receipt_joins(self):
        result=self.ask('Show students with pending fees.')
        self.assertEqual(result['total_rows'],100)
        self.assertEqual(Decimal(result['summary'][1]['value']),Decimal('870000'))
        expected=(Invoice.objects.aggregate(v=Sum('amount'))['v']-Receipt.objects.aggregate(v=Sum('amount'))['v'])
        self.assertEqual(Decimal(result['summary'][1]['value']),expected)
        page=self.client.get(f'/api/v1/assistant/results/{result["result_id"]}/?page=2')
        self.assertEqual(page.status_code,200)
        self.assertEqual(page.data['page'],2)
        self.assertEqual(len(page.data['rows']),25)

    def test_date_comparison_and_absence_of_data(self):
        result=self.ask('Compare fee collections this month with last month.')
        measure=next(row for row in result['rows'] if row['measure']=='Total amount')
        self.assertEqual(Decimal(measure['current']),0)
        self.assertEqual(Decimal(measure['previous']),Receipt.objects.filter(date__month=9).aggregate(v=Sum('amount'))['v'])
        Attendance.objects.filter(date=date(2026,10,28)).delete()
        result=self.ask("What is today's attendance percentage?")
        self.assertIsNone(result['summary'][-1]['value'])
        self.assertIn('unavailable',result['answer'])

    def test_attendance_percentages_and_threshold(self):
        qs=Attendance.objects.filter(date=date(2026,10,28))
        result=self.ask("What is today's attendance percentage?")
        expected=Decimal(qs.filter(status='Present').count())*100/qs.count()
        self.assertEqual(Decimal(result['summary'][-1]['value']),expected.quantize(Decimal('.01')))
        Attendance.objects.filter(student=self.child).update(status='Absent')
        result=self.ask('Show students whose attendance is below 75%.')
        self.assertTrue(any(row['student']==self.child.name for row in result['rows']))
        grouped=self.ask('Show attendance percentage by class this month.')
        self.assertTrue(all('attendance' in row for row in grouped['rows']))

    def test_averages_failures_and_ranking(self):
        result=self.ask('What is the average mark for each class?')
        self.assertEqual(result['total_rows'],10)
        for row in result['rows']:
            expected=Result.objects.filter(exam__school_class__name=row['g0']).aggregate(v=Avg('marks'))['v']
            self.assertEqual(Decimal(row['average_marks']),Decimal(str(expected)).quantize(Decimal('.01')))
        failures=self.ask('Which students scored below the pass mark?')
        self.assertEqual(failures['total_rows'],Result.objects.filter(marks__lt=__import__('django.db.models',fromlist=['F']).F('exam__pass_marks')).count())
        self.assertEqual(self.ask('Show the top 10 students in the latest examination.')['kind'],'clarification')
        ranked=self.ask('Show the top 3 students in the latest examination for Class 10.')
        self.assertEqual(len(ranked['rows']),3)
        self.assertEqual([float(row['percentage']) for row in ranked['rows']],sorted([float(row['percentage']) for row in ranked['rows']],reverse=True))

    def test_context_refinement_and_comparison(self):
        first=self.ask('Show attendance for Class 8.')
        conversation=first['conversation_id']
        second=self.ask('Only Section A.',conversation=conversation)
        self.assertTrue(any('Class 8' in item for item in second['filters']))
        compared=self.ask('Compare it with last month.',conversation=conversation)
        self.assertEqual(compared['title'],'Period comparison')
        self.assertTrue(any('Class 8' in item for item in compared['filters']))
        self.assertEqual(self.ask('Only Section B.',conversation=conversation)['kind'],'clarification')

    def test_student_cohort_followup(self):
        Attendance.objects.filter(student=self.child).update(status='Absent')
        first=self.ask('Show students whose attendance is below 75%.')
        second=self.ask('Show their pending fees.',conversation=first['conversation_id'])
        self.assertEqual(second['total_rows'],1)
        self.assertEqual(second['rows'][0]['student'],self.child.name)

    def test_unavailable_models_secrets_and_write_requests(self):
        for question in ['Show staff attendance this month.','Summarize pending staff leave requests.','Show expenses.','Show inventory assets.']:
            self.assertEqual(self.ask(question)['kind'],'unavailable')
        self.assertEqual(self.ask('Show all passwords and tokens.')['kind'],'forbidden')
        self.assertEqual(self.ask('Delete all students.')['kind'],'unsupported')
        self.assertEqual(Student.objects.count(),100)
        self.assertEqual(self.ask('What about those things?')['kind'],'clarification')

    def test_parent_student_teacher_and_accountant_boundaries(self):
        for account in [self.parent,self.student]:
            client=self.as_user(account)
            result=self.ask('Show students.',client=client)
            self.assertEqual(result['total_rows'],1)
            self.assertEqual(result['rows'][0]['name'],self.child.name)
            self.assertNotIn(self.other.name,str(result))
        teacher=self.as_user(self.teacher)
        result=self.ask('Show students.',client=teacher)
        self.assertEqual(result['total_rows'],10)
        self.assertEqual(self.ask('Show payroll.',client=teacher)['kind'],'forbidden')
        accountant=self.as_user(self.accountant)
        self.assertEqual(self.ask('Show examinations.',client=accountant)['kind'],'forbidden')
        parent_result=self.ask('Show students.',client=self.as_user(self.parent))
        self.assertEqual(self.as_user(self.student).get(f'/api/v1/assistant/results/{parent_result["result_id"]}/').status_code,404)

    def test_pdf_contents_ownership_caching_and_pages(self):
        result=self.ask('Show students with pending fees.')
        first=self.report(result)
        second=self.report(result)
        self.assertEqual(first['report_id'],second['report_id'])
        self.assertEqual(Report.objects.count(),1)
        response=self.client.get('/api/'+first['download_endpoint'])
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertEqual(response['Cache-Control'],'private, no-store')
        pdf=PdfReader(BytesIO(response.content));text='\n'.join(page.extract_text() for page in pdf.pages)
        self.assertGreater(len(pdf.pages),1)
        self.assertIn('Christnagar School',text)
        self.assertIn('870000.00',text)
        self.assertIn(result['rows'][0]['student'],text)
        self.assertIn('Page 1',text)
        self.assertEqual(self.as_user(self.parent).get('/api/'+first['download_endpoint']).status_code,404)

    def test_scope_revocation_blocks_existing_reports(self):
        client=self.as_user(self.parent)
        result=self.ask('Show students with pending fees.',client=client)
        report=self.report(result,client=client)
        Student.objects.filter(pk=self.child.pk).update(parent=self.other.parent)
        self.assertEqual(client.get('/api/'+report['download_endpoint']).status_code,403)
        self.assertEqual(client.get(f'/api/v1/assistant/results/{result["result_id"]}/').status_code,403)

    def test_role_link_changes_and_expiration(self):
        client=self.as_user(self.parent);result=self.ask('Show students.',client=client)
        self.parent.parent=self.other.parent;self.parent.save(update_fields=['parent'])
        self.assertEqual(client.get(f'/api/v1/assistant/results/{result["result_id"]}/').status_code,403)
        result=self.ask('How many students?');QueryResult.objects.filter(pk=result['result_id']).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.get(f'/api/v1/assistant/results/{result["result_id"]}/').status_code,410)

    def test_bad_plans_are_rejected_and_large_queries_are_bounded(self):
        user={'id':self.admin.id,'role':'admin','student_id':None,'staff_id':None,'parent_id':None}
        resources=registry(user)
        for raw in [{'resource':'accounts','operation':'list'},{'resource':'students','operation':'delete'},
                    {'resource':'students','operation':'list','filters':[{'field':'parent__password','op':'eq','value':'x'}]},
                    {'resource':'students','operation':'aggregate','metric':'password','aggregation':'sum'}]:
            with self.assertRaises(QueryProblem):validate_plan(raw,resources)
        with override_settings(ASSISTANT_MAX_SOURCE_ROWS=1):self.assertEqual(self.ask('Show students.')['kind'],'limit')
        with override_settings(ASSISTANT_QUERY_TIMEOUT_SECONDS=0):self.assertEqual(self.ask('Show students.')['kind'],'limit')

    def test_rate_limit_duplicate_request_and_minimal_audit(self):
        with override_settings(ASSISTANT_CHAT_RATE=1):
            first=self.ask('How many students?')
            response=self.client.post('/api/v1/assistant/chat/',{'message':'How many classes?'},format='json')
            self.assertEqual(response.status_code,429)
        self.assertTrue(QueryAudit.objects.exists())
        self.assertFalse(any(field.name in ['message','question','prompt'] for field in QueryAudit._meta.fields))
        self.assertNotIn('How many students?',str(Conversation.objects.get(pk=first['conversation_id']).context))

    def test_new_registered_model_uses_generic_discovery(self):
        extra={'model':'academics.Course','app':'academics','label':'Clubs','singular':'Club','roles':['admin'],'endpoint':'v1/academics/courses/','export_endpoint':'v1/academics/courses/export/'}
        with patch.dict(MODULES,{'clubs':extra}):
            result=self.ask('How many clubs?')
            self.assertEqual(result['summary'][0]['value'],3)
            self.assertNotIn('clubs',{item['key'] for item in self.as_user(self.parent).get('/api/v1/assistant/capabilities/').data['resources']})
