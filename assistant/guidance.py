"""Module help derived from the caller's permitted query fields."""

def module_guidance(spec):
    noun=spec.aliases[0]
    examples=[f'Show {noun}',f'How many {noun} records are there?']
    if spec.key=='staff':examples=['Show staff','How many faculty members are there?','Count staff by department']
    extras={
        'students':['How many students are currently enrolled?','Show students in Class 10','Show incomplete student profiles'],
        'attendance':['Attendance today','Attendance by class this month','Attendance below 75% this month'],
        'fees':['Show outstanding fees by student','Show overdue fees'],
        'payments':['Total fee collections this month','Compare fee collections this month with last month'],
        'results':['Average marks by class','Show exam failures','Top 10 exam performers'],
        'loans':['Show overdue books'],
        'payroll':['Total net payroll this month'],
    }
    examples+=extras.get(spec.key,[])
    if spec.key not in ['students','attendance','fees','results','payroll']:
        group=next((key for key in spec.groups if key not in ['name','title']),None)
        if group:examples.append(f'Count {noun} by {group.replace("_"," ")}')
    status=spec.fields.get('status')
    if status and status.choices:
        value,title=next(iter(status.flatchoices))
        examples.append(f'Show {noun} with status {title}')
    if spec.key=='staff' and 'salary' in spec.fields:examples.append('Average staff salary by department')
    details=[str(field.verbose_name).capitalize() for field in spec.fields.values()]
    capabilities=['List records, search by name (for example: named "Anu"), and count matching records.']
    if 'name' not in spec.fields:capabilities[0]='List records and count matching records.'
    if spec.numeric:capabilities.append('Total or average permitted numeric fields: '+', '.join(sorted(spec.numeric))+'.')
    if spec.groups:capabilities.append('Group counts by '+', '.join(key.replace('_',' ') for key in spec.groups)+'.')
    if spec.date_path:capabilities.append('Narrow results by supported dates, months, or explicit date ranges.')
    capabilities.append('Generate a PDF report after a successful data query.')
    limitations=['I can read and summarize records; use the module screens to add or edit them.']
    if spec.key=='staff':limitations.append('Active/inactive employment status and staff attendance are not stored, so I cannot report them.')
    return {'module':spec.key,'label':spec.label,'details':details,'capabilities':capabilities,'examples':examples,'limitations':limitations}
