"""Strict validation for plans; ORM paths never come directly from user text."""
from copy import deepcopy
from datetime import date

OPERATIONS={'list','count','aggregate','group','attendance_rate','attendance_below','outstanding','exam_average','exam_failures','exam_ranking','incomplete','net_pay'}
PERIODS={'all','today','yesterday','this_month','last_month','this_year','current_academic_year','previous_academic_year','custom'}
KEYS={'resource','operation','aggregation','metric','groups','filters','period','start','end','grade','section','academic_year','compare','threshold','limit','latest','student_ids','columns'}


class QueryProblem(Exception):
    def __init__(self,message,kind='clarification'):
        self.message,self.kind=message,kind


def validate_plan(raw,resources):
    if not isinstance(raw,dict) or set(raw)-KEYS:raise QueryProblem('That query plan is not supported. Please rephrase your question.')
    plan=deepcopy(raw)
    if plan.get('resource') not in resources:raise QueryProblem('You do not have permission to query that module.','forbidden')
    spec=resources[plan['resource']]
    operation=plan.setdefault('operation','list')
    if operation not in OPERATIONS:raise QueryProblem('Only read-only reporting operations are supported.')
    supported={'attendance_rate':'attendance','attendance_below':'attendance','outstanding':'fees','incomplete':'students','net_pay':'payroll',
               'exam_average':'results','exam_failures':'results','exam_ranking':'results'}
    if operation in supported and supported[operation]!=spec.key:raise QueryProblem('The requested calculation is not supported for that module.')
    plan.setdefault('period','all')
    if plan['period'] not in PERIODS:raise QueryProblem('Please specify a supported date range.')
    if plan['period']=='custom':
        try:
            start,end=date.fromisoformat(plan['start']),date.fromisoformat(plan['end'])
            if start>end:raise ValueError
        except (KeyError,TypeError,ValueError):raise QueryProblem('Provide a valid start and end date in YYYY-MM-DD order.')
    if plan.get('grade') is not None:
        if type(plan['grade']) is not int or not 1<=plan['grade']<=12:raise QueryProblem('Please specify a class number from 1 to 12.')
        if spec.class_path is None:raise QueryProblem(f'{spec.label} does not have a configured class relationship.')
    if plan.get('section') is not None and (not isinstance(plan['section'],str) or len(plan['section'])!=1 or not plan['section'].isalpha()):raise QueryProblem('Please specify a single section letter.')
    groups=plan.setdefault('groups',[])
    if not isinstance(groups,list) or len(groups)>2 or any(group not in spec.groups and group!='month' for group in groups):raise QueryProblem('That grouping is unavailable for this module.')
    columns=plan.get('columns',[])
    if not isinstance(columns,list) or len(columns)>10 or any(field not in spec.fields for field in columns):raise QueryProblem('Those display fields are unavailable or restricted.','forbidden')
    metric=plan.get('metric')
    if metric and metric not in spec.numeric:raise QueryProblem('That numeric field is unavailable or restricted.','forbidden')
    if plan.get('aggregation','count') not in ['count','sum','avg']:raise QueryProblem('Only count, sum, and average aggregations are supported.')
    for key,lower,upper in [('threshold',0,100),('limit',1,100)]:
        if key in plan and (type(plan[key]) not in [int,float] or not lower<=plan[key]<=upper):raise QueryProblem(f'{key} must be between {lower} and {upper}.')
    if type(plan.get('compare',False)) is not bool or type(plan.get('latest',False)) is not bool:raise QueryProblem('Invalid comparison options.')
    filters=plan.setdefault('filters',[])
    if not isinstance(filters,list) or len(filters)>10:raise QueryProblem('Use at most ten filters.')
    for item in filters:
        if not isinstance(item,dict) or set(item)!={'field','op','value'}:raise QueryProblem('Unsupported filter structure.')
        if item['field'] not in spec.fields or item['op'] not in ['eq','contains','gte','lte','isnull','in']:raise QueryProblem('That field or filter is unavailable or restricted.','forbidden')
        if item['op']=='in' and (not isinstance(item['value'],list) or len(item['value'])>1000):raise QueryProblem('Too many filter values.')
        if item['op']=='isnull' and type(item['value']) is not bool:raise QueryProblem('A missing-value filter requires true or false.')
    ids=plan.get('student_ids',[])
    if not isinstance(ids,list) or len(ids)>5000 or any(type(item) is not int or item<1 for item in ids):raise QueryProblem('The referenced student set is too large. Narrow the previous result.')
    return plan
