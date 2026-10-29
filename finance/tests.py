import csv
import io
from accounts.models import User
from test_workflows import ERPWorkflowTests


class InvoiceClassFilterTests(ERPWorkflowTests):
    def test_class_filter_and_export_keep_student_scope(self):
        other_class=self.create('classes',dict(name='Grade 2',year='2026-27',teacher_id=self.staff['id'],capacity=30))
        other_student=self.create('students',dict(name='Other student',roll='B1',class_id=other_class['id'],dob='2018-01-01',gender='Other',status='Active'))
        first=self.create('fees',dict(name='First class fee',student_id=self.student['id'],amount='1000.00',due='2026-12-01'))
        self.create('fees',dict(name='Other class fee',student_id=other_student['id'],amount='2000.00',due='2026-12-01'))
        url=self.url('fees')
        result=self.client.get(url,{'class_id':self.batch['id'],'page_size':1})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.data['count'],1)
        self.assertEqual(result.data['results'][0]['id'],first['id'])
        self.assertEqual(self.client.get(url).data['count'],2)
        self.assertEqual(self.client.get(url,{'class_id':other_class['id'],'search':'First'}).data['count'],0)
        self.assertEqual(self.client.get(url,{'class_id':'bad'}).status_code,400)
        exported=self.client.get(url+'export/',{'class_id':self.batch['id']})
        rows=list(csv.DictReader(io.StringIO(exported.content.decode())))
        self.assertEqual([r['name'] for r in rows],['First class fee'])
        user=User.objects.create_user(email='fee-student@test.local',password='Long-password-928!',name='Student',role='student',student_id=self.student['id'])
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(url,{'class_id':other_class['id']}).data['count'],0)
        rows=list(csv.DictReader(io.StringIO(self.client.get(url+'export/',{'class_id':other_class['id']}).content.decode())))
        self.assertEqual(rows,[])
