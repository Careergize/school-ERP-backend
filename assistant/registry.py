"""Allowlisted business metadata. Auth/system models never enter this registry."""
from dataclasses import dataclass
from django.db import models
from core.registry import MODULES
from core.services import model_for,queryset_for
from configuration.services import module_catalog

ALIASES={
 'students':['students','student','pupils','enrolled'], 'parents':['parents','guardians','parent','guardian'],
 'admissions':['admissions','applications','applicants','registration'], 'classes':['classes','batches','classrooms and batches'],
 'courses':['courses','curriculum'], 'academic_years':['academic years'], 'enrollments':['enrollment history','academic history','transfers'],
 'subjects':['subjects','subject list'], 'assignments':['assignments','homework'], 'submissions':['submissions','submitted work'],
 'rooms':['classrooms','facilities','laboratories'], 'activities':['events','activities'], 'exams':['exams','examinations','exam schedule'],
 'results':['results','marks','scores','performance','pass mark','performers','exam failures','exam result','failed students'], 'fees':['fees','invoices','dues','outstanding','pending payments','fee'],
 'payments':['receipts','collections','collected','fee revenue','payments'], 'attendance':['attendance','absent','absentees'],
 'timetable':['timetable','lessons','class schedule'], 'books':['books','library catalog','library catalogue'],
 'loans':['library loans','book loans','borrowed','lending','overdue books','books not returned','unreturned books','returned books'], 'transport':['transport routes','bus routes','buses','transport'],
 'transport_allocations':['transport allocations','bus allocations','bus students'], 'hostels':['hostel rooms','hostels'],
 'hostel_allocations':['hostel allocations','hostel students','boarders'], 'staff':['teachers','faculty','staff','employees'],
 'payroll':['payroll','payslips','salaries','salary payments'], 'reviews':['performance reviews','staff reviews'],
 'notices':['notices','announcements','notice board'], 'messages':['messages','notifications'], 'school_settings':['school settings','school details'],
}
CLASS_PATHS={
 'students':'school_class','classes':'','parents':'students__school_class','admissions':'school_class','enrollments':'school_class',
 'subjects':'school_class','assignments':'school_class','submissions':'assignment__school_class','exams':'school_class',
 'results':'exam__school_class','attendance':'student__school_class','timetable':'school_class','fees':'student__school_class',
 'payments':'invoice__student__school_class','loans':'student__school_class','transport_allocations':'student__school_class',
 'hostel_allocations':'student__school_class',
}
DATE_PATHS={'students':'enrollments_student__from_date','admissions':'created_at','enrollments':'from_date','academic_years':'start_date',
 'assignments':'due','submissions':'created_at','exams':'date','results':'exam__date','attendance':'date','timetable':None,
 'fees':'due','payments':'date','staff':'joined','payroll':'month','reviews':'date','activities':'date','loans':'issued',
 'hostel_allocations':'from_date','notices':'date','messages':'date'}
PRIVATE={'email','phone','address','dob','salary'}
SYSTEM={'id','version','created_at','updated_at','author','enrolled_student'}


@dataclass
class Resource:
    key:str
    label:str
    model:object
    fields:dict
    display:list
    numeric:set
    date_path:str|None
    class_path:str|None
    groups:dict
    aliases:list


def registry(user):
    catalog=module_catalog(user)
    output={}
    for key,config in MODULES.items():
        if not catalog[key]['can_read']:continue
        if key not in ALIASES and user['role']!='admin' and user['role'] not in config.get('assistant_roles',[]):continue
        Model=model_for(key);fields={};display=[];numeric=set();groups={}
        for field in Model._meta.fields:
            if field.name in SYSTEM:continue
            if field.name in PRIVATE and user['role'] not in ['admin','accountant','parent','student']:continue
            if field.name=='salary' and user['role'] not in ['admin','accountant']:continue
            name='class_id' if field.name=='school_class' else field.attname
            fields[name]=field
            if isinstance(field,(models.DecimalField,models.IntegerField)) and not isinstance(field,models.ForeignKey): numeric.add(name)
            if field.choices or (isinstance(field,models.CharField) and field.name not in PRIVATE):
                groups[name]=field.name
            if len(display)<7 and field.name not in PRIVATE:display.append(name)
        class_path=CLASS_PATHS.get(key)
        if class_path is not None:groups['class']=(class_path+'__name') if class_path else 'name'
        if key in ['results','exams','assignments','timetable']:
            groups['subject']='exam__subject__name' if key=='results' else 'subject__name'
        if any(field.name=='student' for field in Model._meta.fields):groups['student']='student__name'
        if key=='payments':groups['student']='invoice__student__name'
        if key=='payroll':numeric.add('net_pay')
        output[key]=Resource(key,config['label'],Model,fields,display,numeric,DATE_PATHS.get(key),class_path,groups,ALIASES.get(key,[config['label'].lower()]))
    return output


def public_registry(user):
    return [{'key':item.key,'label':item.label,'aliases':item.aliases,'fields':[{'name':name,'label':str(field.verbose_name),'type':field.get_internal_type()} for name,field in item.fields.items()],
             'numeric_fields':sorted(item.numeric),'group_fields':sorted(item.groups),'date_field':item.date_path,
             'operations':['list','count','aggregate','group']+({'attendance':['attendance_rate','attendance_below'],'fees':['outstanding'],'results':['exam_average','exam_failures','exam_ranking'],'students':['incomplete'],'payroll':['net_pay']}.get(item.key,[]))}
            for item in registry(user).values()]


def scoped(resource,user):
    if resource not in registry(user):
        from .plans import QueryProblem
        raise QueryProblem('You do not have permission to query that module.','forbidden')
    return queryset_for(resource,user)
