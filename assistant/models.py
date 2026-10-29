import uuid
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='assistant_conversations')
    context=models.JSONField(default=dict)
    version=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    expires_at=models.DateTimeField(db_index=True)


class QueryResult(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='results')
    request_id=models.UUIDField(default=uuid.uuid4)
    plan=models.JSONField()
    payload=models.JSONField()
    source_refs=models.JSONField(default=dict)
    access_fingerprint=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField(db_index=True)

    class Meta:
        ordering=['-created_at']
        constraints=[models.UniqueConstraint(fields=['conversation','request_id'],name='assistant_result_request_unique')]


class Report(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    result=models.ForeignKey(QueryResult,on_delete=models.CASCADE,related_name='reports')
    mode=models.CharField(max_length=12,choices=[('summary','Summary'),('detailed','Detailed')])
    status=models.CharField(max_length=12,default='generating',choices=[('generating','Generating'),('ready','Ready'),('failed','Failed')])
    content=models.BinaryField(default=bytes)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    expires_at=models.DateTimeField(db_index=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['result','mode'],name='assistant_report_result_mode_unique')]


class UsageBucket(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    minute=models.DateTimeField()
    kind=models.CharField(max_length=10)
    count=models.PositiveIntegerField(default=0)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','minute','kind'],name='assistant_usage_user_minute_kind')]


class QueryAudit(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    resource=models.CharField(max_length=64,blank=True)
    operation=models.CharField(max_length=32,blank=True)
    outcome=models.CharField(max_length=20)
    row_count=models.PositiveIntegerField(default=0)
    elapsed_ms=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
