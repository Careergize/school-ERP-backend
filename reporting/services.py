"""Role-scoped database aggregates, without loading entire record collections."""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from core.services import queryset_for
from core.registry import MODULES


def summary(user):
    querysets={module:queryset_for(module,user) for module in MODULES}
    def total(module,key='amount'):
        return querysets[module].aggregate(total=Sum(key))['total'] or Decimal('0')
    invoices,receipts=total('fees'),total('payments')
    payroll=querysets['payroll'].aggregate(basic=Sum('basic'),allowances=Sum('allowances'),deductions=Sum('deductions'))
    net=sum((payroll[key] or Decimal('0'))*sign for key,sign in [('basic',1),('allowances',1),('deductions',-1)])
    today=timezone.localdate()
    attendance=querysets['attendance'].filter(date=today)
    return {
        'as_of':today.isoformat(),'currency':'INR',
        'counts':{module:qs.count() for module,qs in querysets.items()},
        'finance':{'invoiced':str(invoices),'collected':str(receipts),'outstanding':str(invoices-receipts)},
        'payroll':{'net_total':str(net)},
        'attendance':{'recorded':attendance.count(),'present':attendance.filter(status='Present').count()},
        'admissions':{state:querysets['admissions'].filter(status=state).count() for state in ['Applied','Under review','Accepted','Rejected']},
    }
