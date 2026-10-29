"""Build frontend form metadata from Django models, never from record schemas."""
from django.apps import apps
from django.db import models
from core.registry import MODULES


def module_catalog(user=None):
    output = {}
    target_modules = {v['model'].lower(): key for key,v in MODULES.items()}
    for key, config in MODULES.items():
        model = apps.get_model(config['model'])
        fields = []
        for field in model._meta.fields:
            if field.name in ['id', 'version', 'created_at', 'updated_at', 'enrolled_student', 'author']:
                continue
            api_name = 'class_id' if field.name == 'school_class' else field.attname
            kind, options = 'text', None
            if isinstance(field, models.ForeignKey):
                kind = 'ref:' + target_modules[field.related_model._meta.label_lower]
            elif field.choices:
                kind, options = 'select', [value for value,label in field.choices]
            elif isinstance(field, models.DecimalField): kind = 'money'
            elif isinstance(field, models.IntegerField): kind = 'number'
            elif isinstance(field, models.DateField): kind = 'date'
            elif isinstance(field, models.TimeField): kind = 'time'
            elif isinstance(field, models.EmailField): kind = 'email'
            elif isinstance(field, models.TextField): kind = 'textarea'
            fields.append({'key':api_name, 'label':str(field.verbose_name), 'type':kind,
                           'required':not field.blank and not field.null and not field.has_default(), 'options':options,
                           'default':field.get_default() if field.has_default() else None,
                           'max_length':getattr(field,'max_length',None),
                           'min':next((validator.limit_value for validator in field.validators if validator.__class__.__name__=='MinValueValidator'),0 if isinstance(field,models.PositiveIntegerField) else None)})
        readable = {
            'admin':set(MODULES),
            'accountant':{'fees','payments','payroll','staff','students','classes','notices','messages'},
            'librarian':{'books','loans','students','classes','notices','messages'},
            'teacher':set(MODULES)-{'admissions','parents','payroll','reviews'},
            'student':set(MODULES)-{'admissions','parents','staff','payroll','reviews'},
            'parent':set(MODULES)-{'admissions','staff','payroll','reviews'},
        }
        output[key] = {**config, 'fields':fields, 'can_write':bool(user and user['role'] in config['roles']),
                       'can_read':bool(user and key in readable.get(user['role'],set()))}
    return output


def app_directory():
    result = {}
    for key, config in MODULES.items():
        app = result.setdefault(config['app'], {'name':config['app'], 'resources':{}})
        app['resources'][key] = '/api/' + config['endpoint']
    return list(result.values())
