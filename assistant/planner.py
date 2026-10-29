"""Local English-to-plan interpretation. No network access or generated code."""
import re
from copy import deepcopy
from core.registry import MODULES
from .plans import QueryProblem
from .registry import ALIASES


class LocalPlanner:
    name='Local query mode'

    def plan(self,message,context,resources):
        self.resource=None
        try:return self._plan(message,context,resources)
        except QueryProblem as exc:
            if exc.kind!='forbidden' and not getattr(exc,'resource',None):
                text=message.lower()
                matches=[(len(alias),key) for key,spec in resources.items() for alias in spec.aliases if re.search(r'\b'+re.escape(alias)+r'\b',text)]
                if self.resource:exc.resource=self.resource
                elif matches:exc.resource=max(matches)[1]
                elif context.get('plan'):exc.resource=context['plan']['resource']
            raise

    def _plan(self,message,context,resources):
        text=' '.join(message.lower().replace('–','-').replace('’',"'").split())
        text=re.sub(r"\b(?:aren't|isn't)\b",'not',text)
        text=re.sub(r'\b(?:no\. of|number of|how much (students|teachers|faculty|staff|parents|books))\b',lambda m:'how many '+(m.group(1) or ''),text)
        text=re.sub(r'\b(?:give me|display|list out)\b','show',text)
        text=re.sub(r'\b(?:department|designation|status|class|subject)[ -]wise\b',lambda m:'by '+m.group(0).replace('-',' ').split()[0],text)
        previous=context.get('plan') or {}
        if re.fullmatch(r'(hi|hello|hey|help|what can you do|what modules can you help with|what can i ask)[.!? ]*',text):return {'module_help':'all'}
        if re.search(r'\b(passwords?|tokens?|credentials?|api keys?|secret keys?)\b',text):
            raise QueryProblem('Credentials, passwords, and authentication tokens are never accessible to the assistant.','forbidden')
        if re.search(r'^(delete|remove|update|insert|drop|alter|truncate|execute|run sql|run python|send email|pay)\b',text):
            raise QueryProblem('This assistant is read-only. Use the ERP module screens to make changes.','unsupported')
        for phrase,key,label in [('staff attendance','staff_attendance','Staff attendance'),('teacher attendance','staff_attendance','Staff attendance'),('leave','leave','Leave management'),('inventory','inventory','Inventory'),('assets','assets','Asset management'),('expenses','expenses','Expenses')]:
            if re.search(r'\b'+re.escape(phrase)+r'\b',text) and key not in MODULES:
                raise QueryProblem(f'{label} is not implemented in the current ERP. I cannot report data that the application does not store.','unavailable')
        if 'attendance' in text and any(word in text for word in ['pending fees','outstanding fees']):
            raise QueryProblem('First ask for the attendance-based student list, then ask for "their pending fees" to reuse that student set.')
        if text.rstrip('.!?')=='compare both' and not previous.get('compare'):
            raise QueryProblem('Which two periods or groups should I compare?')
        if re.fullmatch(r'(yes[,. ]*)?(generate( the)?( pdf)?( report)?|export( this)?|download( the)?( pdf)?|pdf report)[.! ]*',text):
            if not previous:raise QueryProblem('Ask a data question first, then I can generate a report for those results.')
            return {'report_current':True}
        scores={}
        for key,config in MODULES.items():
            aliases=ALIASES.get(key,[config['label'].lower()])
            hits=[len(alias.split())*10+len(alias)/100 for alias in aliases if re.search(r'\b'+re.escape(alias)+r'\b',text)]
            if hits:scores[key]=max(hits)
        # Business intent takes precedence over the student/staff nouns in the question.
        if any(word in text for word in ['attendance','absent','absentees']):resource='attendance'
        elif any(word in text for word in ['outstanding','pending fees','pending payments','unpaid','fee balances','fee balance','overdue fees']):resource='fees'
        elif any(word in text for word in ['collected','collections','fee revenue','receipts']):resource='payments'
        elif 'performance review' in text or 'staff review' in text:resource='reviews'
        elif any(word in text for word in ['pass mark','scored','average mark','subject-wise performance','subject wise performance']) or (re.search(r'\b(top|bottom)\b',text) and any(word in text for word in ['exam','marks','results','performers'])):resource='results'
        elif 'borrowed' in text or 'overdue books' in text or 'library loan' in text or ('book' in text and 'returned' in text):resource='loans'
        elif 'academic history' in text or 'enrollment history' in text:resource='enrollments'
        elif 'joined' in text and 'student' in text:resource='students'
        elif 'incomplete' in text and ('admission' in text or 'student' in text):resource='students'
        elif ('teacher' in text or 'faculty' in text) and ('salary' in text or 'salaries' in text):resource='staff'
        elif scores:resource=max(scores,key=scores.get)
        elif previous and re.search(r'(only|section|class|grade|same|those|their|compare|month|year|today|yesterday|below|above|export|report)',text):resource=previous['resource']
        else:raise QueryProblem('Which module and measure do you need? For example: "How many students are enrolled?", "Outstanding fees by student", or "Attendance for Class 8 this month".')
        if resource not in resources:raise QueryProblem('Your account does not have permission to access that module.','forbidden')
        self.resource=resource
        help_request=re.search(r'\b(help|what can|what all|what details|which details|what information|what do you|tell me about)\b',text)
        bare_module=any(text.strip(' .!?')==alias for alias in resources[resource].aliases)
        if help_request or bare_module:return {'module_help':resource}
        if re.search(r'\b(tomorrow|next week|next month|next year|upcoming)\b',text):
            raise QueryProblem('For future schedules, please give explicit YYYY-MM-DD start and end dates so I can query saved records without guessing the period.')
        if re.search(r'\b(why|predict|forecast|recommend|should|will|best way)\b',text):
            raise QueryProblem('I can report saved records, counts, and summaries, but cannot determine causes, predict outcomes, or make recommendations. Try one of the module questions below.','unsupported')
        if resource=='staff' and re.search(r'\b(inactive|not active|active|employment status)\b',text):
            problem=QueryProblem('Staff records do not store active/inactive employment status, so I cannot count inactive faculty. Ask for registered faculty counts or staff by department instead.','unavailable')
            problem.resource=resource
            raise problem
        follow=bool(previous and (re.search(r'^(only|compare|show the same|same|what about|and |their|those|for class|for grade|this month|last month)',text) or not scores))
        plan=deepcopy(previous) if follow else {'resource':resource,'operation':'list','period':'all','filters':[],'groups':[]}
        if plan.get('resource')!=resource:
            plan={'resource':resource,'operation':'list','period':'all','filters':[],'groups':[]}
        plan['resource']=resource
        plan.pop('student_ids',None)
        if previous and re.search(r'\b(those students|their|these students)\b',text):
            ids=context.get('student_ids')
            if not ids:raise QueryProblem('The previous result does not identify a student set. First request a student-based list.')
            plan['student_ids']=ids
        grade=re.search(r'\b(?:class|grade|standard)\s*(10|11|12|[1-9])(?:st|nd|rd|th)?\b',text) or re.search(r'\b(10|11|12|[1-9])(?:st|nd|rd|th)\s+(?:class|grade|standard)\b',text)
        if grade:plan['grade']=int(grade.group(1))
        section=re.search(r'\bsection\s+([a-z])\b',text)
        if section:plan['section']=section.group(1).upper()
        years=re.search(r'\b(20\d{2})\s*[-/]\s*(\d{2}|20\d{2})\b',text)
        if years:plan['academic_year']=years.group(1)+'-'+years.group(2)[-2:];plan['period']='current_academic_year'
        explicit_range=re.search(r'\b(\d{4}-\d{2}-\d{2})\s+(?:to|through|until)\s+(\d{4}-\d{2}-\d{2})\b',text)
        if explicit_range:plan.update(period='custom',start=explicit_range.group(1),end=explicit_range.group(2))
        elif 'previous academic year' in text or 'last academic year' in text:plan['period']='previous_academic_year'
        elif 'academic year' in text and not years:plan['period']='current_academic_year'
        elif 'this month' in text or 'current month' in text:plan['period']='this_month'
        elif 'last month' in text or 'previous month' in text:plan['period']='last_month'
        elif 'yesterday' in text:plan['period']='yesterday'
        elif 'today' in text:plan['period']='today'
        elif 'this year' in text:plan['period']='this_year'
        if not explicit_range:
            single_date=re.search(r'\b(?:on|for)\s+(\d{4}-\d{2}-\d{2})\b',text)
            if single_date:plan.update(period='custom',start=single_date.group(1),end=single_date.group(1))
            month_names=['january','february','march','april','may','june','july','august','september','october','november','december']
            named_month=next((name for name in month_names if re.search(r'\b'+name+r'\b',text)),None)
            if named_month:
                year_match=re.search(r'\b(20\d{2})\b',text)
                if not year_match:raise QueryProblem('Please include a year with the month, for example September 2026.')
                import calendar
                year=int(year_match.group(1));month=month_names.index(named_month)+1
                plan.update(period='custom',start=f'{year}-{month:02d}-01',end=f'{year}-{month:02d}-{calendar.monthrange(year,month)[1]}')
            if any(phrase in text for phrase in ['last week','this week','last quarter','this quarter']) and not single_date:
                from datetime import timedelta
                from django.utils import timezone
                today=timezone.localdate()
                if 'week' in text:
                    start=today-timedelta(days=today.weekday())
                    end=today
                    if 'last week' in text:end=start-timedelta(days=1);start-=timedelta(days=7)
                else:
                    start=today.replace(month=((today.month-1)//3)*3+1,day=1);end=today
                    if 'last quarter' in text:
                        end=start-timedelta(days=1);start=end.replace(month=((end.month-1)//3)*3+1,day=1)
                plan.update(period='custom',start=start.isoformat(),end=end.isoformat())
        if 'all time' in text or 'all dates' in text:plan['period']='all'
        if 'compare' in text:
            if plan['period'] in ['all','last_month']:plan['period']='this_month'
            plan['compare']=True
        elif not follow:plan['compare']=False
        if 'latest' in text or 'most recent' in text:plan['latest']=True
        if re.search(r'\b(class[- ]wise|by class|each class|across classes)\b',text):plan['groups']=['class']
        if re.search(r'\b(subject[- ]wise|by subject|each subject)\b',text):
            plan['groups']=(['class'] if 'across classes' in text else [])+['subject']
        for phrase,field in [('by department','department'),('by status','status'),('by month','month'),('monthly trend','month'),('by designation','designation'),('by audience','audience')]:
            if phrase in text:plan['groups']=[field]
        for field in resources[resource].groups:
            phrase=field.replace('_',' ')
            if re.search(r'\b(?:by|per|each)\s+'+re.escape(phrase)+r's?\b',text):
                if field not in plan['groups']:plan['groups']=[field]
        filters=plan.setdefault('filters',[])
        def set_filter(field,op,value):
            nonlocal filters
            filters=[item for item in filters if item['field']!=field]
            filters.append({'field':field,'op':op,'value':value})
        if resource=='students':
            if 'incomplete' in text:plan['operation']='incomplete'
            elif any(word in text for word in ['how many','count','number of','total students']):plan['operation']='group' if plan['groups'] else 'count'
            elif not follow:plan['operation']='list'
            if 'currently enrolled' in text:set_filter('status','eq','Active')
            for status in ['Graduated','Withdrawn']:
                if status.lower() in text:set_filter('status','eq',status)
        elif resource=='attendance':
            threshold=re.search(r'(?:below|under|less than)\s*(\d+(?:\.\d+)?)\s*%?',text)
            if threshold:plan.update(operation='attendance_below',threshold=float(threshold.group(1)))
            elif re.search(r'\b(absent|absentees|present|late|excused)\b',text):
                plan['operation']='count' if re.search(r'\b(how many|count|number of)\b',text) else 'list'
                if 'absentees' in text:set_filter('status','eq','Absent')
            else:plan['operation']='attendance_rate'
        elif resource=='fees' and any(word in text for word in ['outstanding','pending','unpaid','balance','overdue']):
            plan['operation']='outstanding'
            if 'overdue' in text:set_filter('due','lte',__import__('django.utils.timezone',fromlist=['localdate']).localdate().isoformat())
        elif resource=='results':
            if any(word in text for word in ['below the pass','below pass','failed','failures']):plan['operation']='exam_failures'
            elif re.search(r'\b(top|best|bottom|lowest)\b',text):
                plan['operation']='exam_ranking'
                limit=re.search(r'\b(?:top|bottom)\s+(\d+)\b',text);plan['limit']=int(limit.group(1)) if limit else 10
                plan['aggregation']='avg' if 'bottom' in text or 'lowest' in text else 'sum'
            elif 'average' in text or 'performance' in text:
                plan['operation']='exam_average'
                if not plan['groups']:plan['groups']=['class']
            elif any(word in text for word in ['how many','count','number of']):plan['operation']='count'
            else:plan['operation']='list'
        elif resource=='payments' and 'compare' in text and not any(word in text for word in ['how many','number of','count']):plan.update(operation='aggregate',metric='amount',aggregation='sum')
        elif resource=='payroll' and any(word in text for word in ['total','how much','net','summar']):plan['operation']='net_pay'
        elif any(word in text for word in ['how many','count','number of']):plan['operation']='group' if plan['groups'] else 'count'
        elif any(word in text for word in ['average','total','how much','sum','revenue']):
            spec=resources[resource]
            metric=next((field for field in spec.numeric if re.search(r'\b'+re.escape(field.replace('_',' '))+r'\b',text)),None)
            if not metric:metric=next((field for field in ['amount','salary','marks','rating','copies','capacity'] if field in spec.numeric),None)
            if not metric:raise QueryProblem(f'Which numeric measure do you need for {spec.label.lower()}?')
            plan.update(operation='group' if plan['groups'] else 'aggregate',metric=metric,aggregation='avg' if 'average' in text else 'sum')
        elif plan['groups'] and not follow:plan['operation']='group';plan['aggregation']='count'
        elif not follow:plan['operation']='list'
        if resource=='staff' and ('teacher' in text or 'faculty' in text):set_filter('designation','contains','Teacher')
        if resource=='loans':
            if 'overdue' in text:
                set_filter('returned','isnull',True)
                from django.utils import timezone
                set_filter('due','lte',timezone.localdate().isoformat())
            elif re.search(r'\b(not returned|unreturned)\b',text):set_filter('returned','isnull',True)
            elif 'returned' in text:set_filter('returned','isnull',False)
        # Explicit field-name search is safe and asks for clarification if no value is provided.
        named=re.search(r'\b(?:named|name is|called)\s+["\']?(.+?)["\']?$',message,re.I)
        if named and 'name' in resources[resource].fields:set_filter('name','contains',named.group(1).strip(' ."\''))
        status_field=resources[resource].fields.get('status')
        if status_field and status_field.choices:
            choices=list(status_field.flatchoices)
            for value,title in choices:
                phrase=str(title).lower()
                if re.search(r'\b'+re.escape(phrase)+r'\b',text):
                    negative=re.search(r'\b(?:not|non|except|excluding)\s+'+re.escape(phrase)+r'\b',text)
                    set_filter('status','in' if negative else 'eq',[key for key,_ in choices if key!=value] if negative else value)
        for field_name in ['department','designation','audience']:
            if field_name not in resources[resource].fields:continue
            match=re.search(r'\b'+field_name+r'\s+(?:is\s+|equals\s+)?["\']([^"\']+)["\']',message,re.I)
            if match:set_filter(field_name,'contains',match.group(1))
        if 'for teachers' not in text and resource in ['notices','messages']:
            for audience in ['Parents','Students','Staff','Everyone']:
                if re.search(r'\b'+audience.lower()+r'\b',text):set_filter('audience','eq',audience)
        if re.search(r'\b(top|bottom|highest|lowest)\b',text) and resource!='results':
            raise QueryProblem('Please specify an exam-based ranking, or ask for a count, list, total, or grouped summary. Other ranking criteria are not configured in local mode.')
        requested_columns=[]
        for phrase,field in [('email','email'),('phone','phone'),('address','address'),('date of birth','dob'),('salary','salary'),('salaries','salary')]:
            if phrase in text and plan['operation']=='list':
                if field not in resources[resource].fields:raise QueryProblem('That personal or salary field is unavailable to your account.','forbidden')
                requested_columns.append(field)
        if requested_columns:plan['columns']=list(dict.fromkeys(resources[resource].display+requested_columns))[:10]
        plan['filters']=filters
        return plan
