from datetime import timedelta
from django.utils import timezone
from accounts.models import User
from rest_framework.test import APIClient
from test_workflows import ERPWorkflowTests


class ImprovementTests(ERPWorkflowTests):
    def test_class_filter_scopes_gaps_plans_and_choices(self):
        baseline=self.baseline()
        root='/api/v1/improvement/'
        body=dict(baseline_id=baseline['id'],topic='Fractions',target=60,due=str(timezone.localdate()+timedelta(days=14)),instructions='Practice fractions.')
        self.assertEqual(self.client.post(root+'plans/',body,format='json').status_code,201)
        other=self.create('classes',dict(name='Grade 2 B',year='2026-27',teacher_id=self.staff['id'],capacity=30))
        matched=self.client.get(root,{'class_id':self.batch['id']})
        self.assertEqual(matched.status_code,200)
        self.assertEqual(len(matched.data['gaps']),1)
        self.assertEqual(len(matched.data['plans']),1)
        empty=self.client.get(root,{'class_id':other['id']})
        self.assertEqual(empty.data['gaps'],[])
        self.assertEqual(empty.data['plans'],[])
        self.assertEqual(len(empty.data['classes']),2)
        self.assertEqual(self.client.get(root,{'class_id':'invalid'}).status_code,400)
        self.assertEqual(self.client.get(root,{'class_id':999999}).status_code,404)
        user=User.objects.create_user(email='filter@test.local',password='Long-password-928!',name='Learner',role='student',student_id=self.student['id'])
        self.client.force_authenticate(user)
        self.assertEqual([c['id'] for c in self.client.get(root).data['classes']],[self.batch['id']])
        self.assertEqual(self.client.get(root,{'class_id':other['id']}).status_code,404)

    def baseline(self):
        exam=self.create('exams',dict(name='Baseline', class_id=self.batch['id'], subject_id=self.subject['id'], date=str(timezone.localdate()-timedelta(days=5)), max_marks=100, pass_marks=40))
        return self.create('results',dict(student_id=self.student['id'], exam_id=exam['id'], marks=38))

    def test_full_improvement_loop(self):
        baseline=self.baseline()
        root='/api/v1/improvement/'
        self.assertEqual(self.client.get(root).data['gaps'][0]['score'],38)
        body=dict(baseline_id=baseline['id'],topic='Fractions',target=60,due=str(timezone.localdate()+timedelta(days=14)),instructions='Review pages 10–12 and practice questions 1–10.')
        response=self.client.post(root+'plans/',body,format='json');self.assertEqual(response.status_code,201,response.data)
        plan=response.data
        self.assertEqual(self.client.post(root+'plans/',body,format='json').status_code,409)
        invalid=self.client.post(root+f"plans/{plan['id']}/",dict(version=plan['version'],reassessment_id=baseline['id'],feedback='Review',close=True),format='json')
        self.assertEqual(invalid.status_code,400)
        for task in plan['tasks']:
            response=self.client.post(root+f"tasks/{task['id']}/",dict(version=task['version'],completed=True,evidence='Completed questions and corrected mistakes.'),format='json')
            self.assertEqual(response.status_code,200,response.data);plan=response.data
        exam=self.create('exams',dict(name='Follow-up',class_id=self.batch['id'],subject_id=self.subject['id'],date=str(timezone.localdate()),max_marks=50,pass_marks=20))
        result=self.create('results',dict(student_id=self.student['id'],exam_id=exam['id'],marks=35))
        review=dict(version=plan['version'],reassessment_id=result['id'],feedback='Explains fractions independently.',close=True)
        stale={**review,'version':1}
        self.assertEqual(self.client.post(root+f"plans/{plan['id']}/",stale,format='json').status_code,409)
        response=self.client.post(root+f"plans/{plan['id']}/",review,format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['improvement'],32)
        self.assertTrue(response.data['closed'])
        task=plan['tasks'][0]
        self.assertEqual(self.client.post(root+f"tasks/{task['id']}/",dict(version=task['version'],completed=False,evidence='Changed'),format='json').status_code,409)

    def test_permissions_and_validation(self):
        baseline=self.baseline();root='/api/v1/improvement/'
        self.assertEqual(APIClient().get(root).status_code,401)
        user=User.objects.create_user(email='learner@test.local',password='Long-password-928!',name='Learner',role='student',student_id=self.student['id'])
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(root).status_code,200)
        self.assertEqual(self.client.post(root+'plans/',{},format='json').status_code,403)
        from students.models import Student
        other=Student.objects.create(name='Other',roll='OTHER',school_class_id=self.batch['id'],dob='2018-01-01')
        user.student=other;user.save()
        self.assertEqual(self.client.get(root).data['gaps'],[])
