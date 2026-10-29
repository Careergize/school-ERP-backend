from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from assistant.models import Conversation,QueryResult,UsageBucket,QueryAudit


class Command(BaseCommand):
    help='Remove expired assistant conversations, snapshots, PDFs, and old minimal usage/audit records.'
    def handle(self,*args,**options):
        now=timezone.now()
        count=QueryResult.objects.filter(expires_at__lte=now).delete()[0]
        count+=Conversation.objects.filter(expires_at__lte=now).delete()[0]
        count+=UsageBucket.objects.filter(minute__lt=now-timedelta(days=1)).delete()[0]
        count+=QueryAudit.objects.filter(created_at__lt=now-timedelta(days=30)).delete()[0]
        self.stdout.write(f'Removed {count} expired assistant records.')
