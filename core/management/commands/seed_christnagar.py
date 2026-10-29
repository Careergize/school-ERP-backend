"""Seed a complete, repeatable Christnagar School sample dataset."""
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import sqlite3
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from core.models import AuditEvent
from core.registry import MODULES

MALE = ['Aarav','Adithya','Arjun','Abhinav','Akash','Alan','Amal','Anand','Ashwin','Basil','Chris','Daniel','David','Dev','Ethan','Joel','Joshua','Kevin','Mathew','Nikhil']
FEMALE = ['Aadhya','Ananya','Ann','Anjali','Anna','Diya','Eva','Hannah','Irene','Jiya','Leah','Maria','Meera','Mia','Nandana','Neha','Rachel','Riya','Sara','Sneha']
SURNAMES = ['Thomas','Nair','Joseph','Menon','Jacob','George','Mathew','Rao','Fernandes','Varghese']
SUBJECTS = [('English','ENG'),('Mathematics','MAT'),('Malayalam','MAL'),('Hindi','HIN'),('Environmental Studies','EVS'),('Computer Studies','CMP'),('Science','SCI'),('Social Science','SOC')]
PERIODS = [('09:00','09:40'),('09:45','10:25'),('10:40','11:20'),('11:25','12:05'),('13:00','13:40'),('13:45','14:25')]


class Command(BaseCommand):
    help = 'Add 100 synthetic students and related records for Christnagar School, preserving existing records.'

    def add_arguments(self,parser):
        parser.add_argument('--school-name',default='Christnagar School')
        parser.add_argument('--as-of',help='Reference date (YYYY-MM-DD); defaults to today.')
        parser.add_argument('--no-backup',action='store_true',help='Skip the automatic SQLite backup (for isolated tests).')

    def handle(self,*args,**options):
        try: self.today=date.fromisoformat(options['as_of']) if options['as_of'] else timezone.localdate()
        except ValueError: raise CommandError('--as-of must use YYYY-MM-DD.')
        if self.today>timezone.localdate(): raise CommandError('The reference date cannot be in the future.')
        self.start_year=self.today.year if self.today.month>=4 else self.today.year-1
        self.year_name=f'{self.start_year}–{str(self.start_year+1)[2:]}'
        self.start=date(self.start_year,4,1);self.end=date(self.start_year+1,3,31)
        self.prefix=f'CNS-{self.start_year}'
        self.created=Counter()
        if not options['no_backup']: self.backup_database()
        try:
            with transaction.atomic(): self.seed(options['school_name'])
        except Exception as exc:
            raise CommandError(f'Seeding rolled back without partial records: {exc}') from exc
        totals={key:apps.get_model(config['model']).objects.count() for key,config in MODULES.items()}
        self.stdout.write(self.style.SUCCESS(f'{options["school_name"]}: 100 sample students, 10 in each of Classes 1–10.'))
        for key in MODULES:
            self.stdout.write(f'{key}: {totals[key]} total (+{self.created[MODULES[key]["model"].lower()]} created)')
        self.stdout.write(f'Sample accounts created: {self.created["accounts.user"]}. All are inactive with unusable passwords.')
        self.stdout.write('All personal/contact details and finance/payroll entries added by this command are synthetic samples.')

    def backup_database(self):
        database=connection.settings_dict['NAME']
        if connection.vendor!='sqlite' or not database or str(database)==':memory:' or not Path(database).is_file(): return
        directory=Path(settings.BASE_DIR)/'backups';directory.mkdir(exist_ok=True)
        destination=directory/f'before_christnagar_seed_{timezone.localtime():%Y%m%d_%H%M%S_%f}.sqlite3'
        connection.ensure_connection()
        with sqlite3.connect(destination) as target: connection.connection.backup(target)
        self.stdout.write(f'Existing database backed up to {destination}')

    def ensure(self,label,lookup,**values):
        Model=apps.get_model(label)
        existing=Model.objects.filter(**lookup).first()
        if existing: return existing
        instance=Model(**lookup,**values);instance.full_clean();instance.save()
        self.created[Model._meta.label_lower]+=1
        return instance

    def account(self,email,name,role,**links):
        User=get_user_model()
        if User.objects.filter(email__iexact=email).exists(): return
        account=User(email=email,name=name,role=role,is_active=False,**links)
        account.set_unusable_password();account.full_clean();account.save()
        self.created['accounts.user']+=1

    def seed(self,school_name):
        School=apps.get_model('configuration.SchoolSettings')
        school=School.objects.order_by('-id').first()
        if school:
            if school.name!=school_name:
                school.name=school_name;school.version+=1;school.full_clean();school.save()
        else:
            self.ensure('configuration.SchoolSettings',{'name':school_name},email='office@christnagar.example',phone='0000000000',address='Sample school address — replace with the actual campus address.',currency='INR',timezone='Asia/Kolkata')
        year=self.ensure('academics.AcademicYear',{'name':self.year_name},start_date=self.start,end_date=self.end)
        courses=[]
        for code,name,description in [('PRIMARY','Primary School','Classes 1–5'),('MIDDLE','Middle School','Classes 6–8'),('SECONDARY','Secondary School','Classes 9–10')]:
            courses.append(self.ensure('academics.Course',{'code':'CNS-'+code},name=name,description=description))
        classroom_teachers=[];all_staff=[];faculty={}
        for index in range(10):
            name=f'{FEMALE[index]} {SURNAMES[index]}'
            teacher=self.ensure('hr.Staff',{'email':f'class.teacher.{index+1:02d}@christnagar.example'},name=name,phone=f'00001{index+1:05d}',designation='Class Teacher',department='Primary' if index<5 else 'Secondary',salary=Decimal(34000+index*1000),joined=date(self.start_year-2,6,1))
            classroom_teachers.append(teacher);all_staff.append(teacher)
        for index,(subject,code) in enumerate(SUBJECTS):
            for group in range(2):
                number=index*2+group
                name=f'{MALE[number%len(MALE)]} {SURNAMES[(number+3)%len(SURNAMES)]}'
                teacher=self.ensure('hr.Staff',{'email':f'faculty.{code.lower()}.{group+1}@christnagar.example'},name=name,phone=f'00002{number+1:05d}',designation='Subject Teacher',department=subject,salary=Decimal(38000+index*1000),joined=date(self.start_year-3,6,1))
                faculty[(code,group)]=teacher;all_staff.append(teacher)
        support=[]
        for index,(designation,role,salary) in enumerate([('Principal',None,80000),('Accountant','accountant',40000),('Librarian','librarian',32000),('Hostel Warden',None,30000),('Transport Coordinator',None,30000)]):
            staff=self.ensure('hr.Staff',{'email':f'{designation.lower().replace(" ",".")}@christnagar.example'},name=f'{["Mary","Rohan","Susan","Peter","Vinod"][index]} {SURNAMES[index]}',phone=f'00003{index+1:05d}',designation=designation,department='Administration',salary=Decimal(salary),joined=date(self.start_year-4,6,1))
            support.append(staff);all_staff.append(staff)
            if role:self.account(staff.email,staff.name,role,staff=staff)
        for staff in classroom_teachers+list(faculty.values()): self.account(staff.email,staff.name,'teacher',staff=staff)
        batches=[];subjects={};assignments={};exams={}
        for grade in range(1,11):
            room=self.ensure('academics.Classroom',{'name':f'Class {grade} A'},building='Primary Block' if grade<=5 else 'Senior Block',capacity=40,type='Classroom')
            batch=self.ensure('academics.Batch',{'name':f'Class {grade} A','year':self.year_name},teacher=classroom_teachers[grade-1],capacity=40,room=room,course=courses[0 if grade<=5 else 1 if grade<=8 else 2],academic_year=year)
            batches.append(batch)
            syllabus=SUBJECTS[:4]+([SUBJECTS[4],SUBJECTS[5]] if grade<=5 else [SUBJECTS[6],SUBJECTS[7]])
            for number,(title,code) in enumerate(syllabus):
                subject=self.ensure('academics.Subject',{'code':f'CNS-C{grade:02d}-{code}'},name=title,school_class=batch,teacher=faculty[(code,(grade-1)//6)])
                subjects[(grade,number)]=subject
                assignments[(grade,number)]=self.ensure('academics.Assignment',{'name':f'{self.prefix} Class {grade} {title} Practice','school_class':batch},subject=subject,due=self.today+timedelta(days=7),description=f'Sample {title.lower()} practice for Class {grade}: complete the revision exercises and submit your work before the due date.')
                for term,month,day in [('Term 1',9,7),('Term 2',11,16)]:
                    exam=self.ensure('examinations.Exam',{'name':f'{self.prefix} {term} {title}','school_class':batch},subject=subject,date=date(self.start_year,month,day)+timedelta(days=number),max_marks=100,pass_marks=35)
                    if term=='Term 1':exams[(grade,number)]=exam
            for day_index,day in enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday']):
                for period,(begin,end) in enumerate(PERIODS):
                    subject=subjects[(grade,(period+grade-1+day_index)%6)]
                    self.ensure('timetable.Lesson',{'school_class':batch,'day':day,'start':time.fromisoformat(begin)},name=f'{subject.name} · Class {grade}',subject=subject,teacher=subject.teacher,end=time.fromisoformat(end),room=room)
        for name,kind in [('Science Laboratory','Laboratory'),('Computer Laboratory','Laboratory'),('School Auditorium','Auditorium'),('Sports Hall','Sports')]:
            self.ensure('academics.Classroom',{'name':name},building='Campus Facilities',capacity=60,type=kind)
        self.stdout.write('Academic structure ready: Classes 1–10, subjects, exams, assignments, and conflict-free lessons.')
        students=[]
        for index in range(100):
            grade=index//10+1;position=index%10;gender='Male' if index%2==0 else 'Female'
            given=(MALE if gender=='Male' else FEMALE)[(index//2)%20];surname=SURNAMES[index//40]
            name=f'{given} {surname}';guardian_gender='Father' if index%2==0 else 'Mother'
            guardian_name=f'{(MALE if guardian_gender=="Father" else FEMALE)[(index+7)%20]} {surname}'
            guardian=self.ensure('students.Guardian',{'email':f'parent.{index+1:03d}@christnagar.example'},name=guardian_name,phone=f'00004{index+1:05d}',relationship=guardian_gender,address=f'Sample House {index+1}, Demonstration Lane')
            student=self.ensure('students.Student',{'roll':f'{self.prefix}-{index+1:03d}'},name=name,school_class=batches[grade-1],parent=guardian,dob=date(self.start_year-grade-5,1+position%3,3+position*2),gender=gender,email=f'student.{index+1:03d}@christnagar.example',phone=f'00005{index+1:05d}',address=guardian.address,status='Active')
            students.append(student)
            self.ensure('students.Enrollment',{'student':student,'school_class':student.school_class,'from_date':self.start},status='Active')
            self.ensure('admissions.Application',{'enrolled_student':student},name=student.name,school_class=student.school_class,email=guardian.email,phone=guardian.phone,dob=student.dob,status='Accepted')
            self.account(student.email,student.name,'student',student=student)
            self.account(guardian.email,guardian.name,'parent',parent=guardian)
            for number in range(6):
                exam=exams[(grade,number)]
                if exam.date<=self.today:
                    marks=28+(index*7+number*11)%70
                    self.ensure('examinations.Result',{'student':student,'exam':exam},marks=marks,remarks='Sample result: excellent progress' if marks>=85 else 'Sample result: revise key concepts' if marks<35 else 'Sample result: steady progress')
                self.ensure('academics.Submission',{'student':student,'assignment':assignments[(grade,number)]},content=f'Sample completed exercises by {student.name} for {subjects[(grade,number)].name}.',feedback='' if index%5==0 else 'Sample feedback: work reviewed; continue practising.')
            attendance_days=[];cursor=self.today
            while len(attendance_days)<20:
                if cursor.weekday()<5 and cursor>=self.start:attendance_days.append(cursor)
                cursor-=timedelta(days=1)
                if cursor<self.start:break
            for attendance_day in attendance_days:
                variation=(index+attendance_day.toordinal())%25
                state='Absent' if variation==0 else 'Late' if variation==1 else 'Excused' if variation==2 else 'Present'
                self.ensure('attendance.Attendance',{'student':student,'date':attendance_day},status=state,note='Synthetic attendance sample')
            for term,due in [(1,date(self.start_year,4,15)),(2,date(self.start_year,9,15)),(3,date(self.start_year+1,1,15))]:
                amount=Decimal(4500+grade*500)
                invoice=self.ensure('finance.Invoice',{'student':student,'name':f'{self.prefix} Term {term} Tuition'},amount=amount,due=due)
                paid=amount if term==1 else amount if term==2 and position<7 else amount/2 if term==2 and position<9 else Decimal('0')
                if paid and due<=self.today:
                    self.ensure('finance.Receipt',{'reference':f'{self.prefix}-T{term}-{index+1:03d}'},invoice=invoice,amount=paid,date=due-timedelta(days=2),method=['Cash','Bank transfer','Cheque'][index%3])
        self.stdout.write('Student records ready: 100 profiles and linked guardians, academic history, results, attendance, fees, and submissions.')
        for index in range(20):
            batch=batches[index%10]
            self.ensure('admissions.Application',{'email':f'applicant.{index+1:03d}@christnagar.example'},name=f'{FEMALE[index%20] if index%2 else MALE[index%20]} {SURNAMES[(index+2)%10]}',school_class=batch,phone=f'00006{index+1:05d}',dob=date(self.start_year-index%10-6,2,10),status='Applied' if index<8 else 'Under review' if index<16 else 'Rejected')
        routes=[]
        for index,direction in enumerate(['North','South','East','West','Central']):
            routes.append(self.ensure('transport.Route',{'name':f'CNS {direction} Route'},vehicle=f'CNS-DEMO-BUS-{index+1:02d}',driver=f'{MALE[(index+10)%20]} {SURNAMES[index]}',phone=f'00007{index+1:05d}',capacity=30,stops=f'Sample {direction} Stop 1\nSample {direction} Stop 2\nChristnagar School'))
        for index,student in enumerate(students):
            self.ensure('transport.TransportAllocation',{'student':student},route=routes[index%5],stop=f"Sample {['North','South','East','West','Central'][index%5]} Stop {1+index%2}")
        hostel_rooms={}
        for gender in ['Male','Female']:
            for number in [1,2]:
                hostel_rooms[(gender,number)]=self.ensure('hostel.HostelRoom',{'name':f'CNS {"Boys" if gender=="Male" else "Girls"} Room {number}'},building='Boys Hostel' if gender=='Male' else 'Girls Hostel',capacity=6,warden=support[3].name)
        hostel_counts=Counter()
        for student in students[80:]:
            hostel_counts[student.gender]+=1;number=1 if hostel_counts[student.gender]<=5 else 2
            self.ensure('hostel.HostelAllocation',{'student':student,'from_date':self.start},hostel=hostel_rooms[(student.gender,number)],to_date=self.end)
        books=[]
        titles=['English Reading Companion','Mathematics Explorer','Science Discovery','Malayalam Reader','Hindi Practice','Computer Fundamentals','World History','Geography Atlas','Nature and Environment','School Stories']
        for index in range(30):
            digits=f'978000{index+1:06d}';checksum=(10-sum(int(value)*(1 if position%2==0 else 3) for position,value in enumerate(digits))%10)%10
            books.append(self.ensure('library.Book',{'isbn':digits+str(checksum)},name=f'{titles[index%10]} · Level {index//10+1}',author='Christnagar Sample Academic Team',copies=5,shelf=f'{["LIT","SCI","REF"][index//10]}-{index%10+1:02d}'))
        for index,student in enumerate(students):
            old=index%4 in [0,1];issued=self.today-timedelta(days=21 if old else 5)
            self.ensure('library.Loan',{'book':books[index%30],'student':student,'issued':issued},due=issued+timedelta(days=14),returned=self.today-timedelta(days=10) if index%4==0 else None)
        for index,staff in enumerate(all_staff):
            for months_ago in range(3):
                month_index=self.today.year*12+self.today.month-1-months_ago
                month=f'{month_index//12}-{month_index%12+1:02d}'
                self.ensure('hr.Payslip',{'staff':staff,'month':month},basic=staff.salary,allowances=Decimal(2500),deductions=Decimal(1500),status='Approved' if months_ago==0 else 'Paid')
            self.ensure('hr.PerformanceReview',{'staff':staff,'date':self.today-timedelta(days=10)},rating=3+index%3,description='Synthetic term review: lesson preparation, student engagement, attendance, and teamwork assessed.')
        actor=get_user_model().objects.filter(role='admin',is_active=True).order_by('id').first()
        for index,(name,audience) in enumerate([('Welcome to Christnagar School','Everyone'),('Term 2 Examination Schedule','Students'),('Parent–Teacher Meeting','Parents'),('Staff Development Workshop','Staff'),('Library Reading Week','Everyone'),('Transport Route Update','Parents')]):
            self.ensure('communication.Notice',{'name':self.prefix+' '+name},date=self.today-timedelta(days=index),audience=audience,description=f'Sample school announcement: {name}. Please contact the school office for actual dates and arrangements.',author=actor)
        for index,(name,audience) in enumerate([('Homework and revision reminder','Students'),('Fee statement available','Parents'),('Academic planning meeting','Staff'),('Campus services update','Everyone')]):
            self.ensure('communication.Message',{'name':self.prefix+' '+name},date=self.today-timedelta(days=index),audience=audience,description='Synthetic in-app message for demonstration. No email or SMS is sent.',author=actor)
        for index,title in enumerate(['School Assembly','Science Exhibition','Annual Sports Day','Reading Festival','Arts and Culture Day','Parent–Teacher Meeting']):
            self.ensure('academics.Activity',{'name':self.prefix+' '+title},date=self.today+timedelta(days=7+index*4),location=['School Auditorium','Science Laboratory','Sports Hall'][index%3],description=f'Sample {title.lower()} activity for Christnagar School.')
        for module,config in MODULES.items():
            if self.created[config['model'].lower()]:
                AuditEvent.objects.create(user=actor,action='seed_sample',module=module,record_id=apps.get_model(config['model']).objects.order_by('id').values_list('id',flat=True).first())
        self.stdout.write('Campus, library, transport, hostel, HR, payroll, communication, and audit records ready.')
