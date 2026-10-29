"""Django password hashing and persisted, expiring bearer sessions."""
import hashlib
import secrets
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from core.services import HTTPException, audit, validate_serializer, validation_failure
from django.core.exceptions import ValidationError
from .models import AccessSession, LoginAttempt
from .serializers import UserSerializer


def user(request):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    session=AccessSession.objects.select_related('user').filter(token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at__gt=timezone.now(),user__is_active=True).first()
    if not session: raise HTTPException(401,'Please sign in again.')
    account=session.user
    return {'id':account.pk,'name':account.name,'email':account.email,'role':account.role,'student_id':account.student_id,'staff_id':account.staff_id,'parent_id':account.parent_id}


def admin(u=None):
    if not u or u['role']!='admin': raise HTTPException(403,'Administrator access required.')
    return u


class Login:
    def __init__(self,email='',password=''):
        self.email,self.password=email,password


def login(body,request):
    ip=request.client.host or '127.0.0.1'
    cutoff=timezone.now()-timedelta(minutes=15)
    LoginAttempt.objects.filter(at__lt=cutoff).delete()
    if LoginAttempt.objects.filter(ip=ip).count()>=15: raise HTTPException(429,'Too many login attempts. Try again in 15 minutes.')
    LoginAttempt.objects.create(ip=ip)
    account=get_user_model().objects.filter(email__iexact=body.email.strip()).first()
    if account is None:
        make_password(body.password)
        raise HTTPException(401,'Incorrect email or password.')
    if not account.check_password(body.password) or not account.is_active:
        raise HTTPException(401,'Incorrect email or password.')
    token=secrets.token_urlsafe(48)
    with transaction.atomic():
        AccessSession.objects.filter(expires_at__lte=timezone.now()).delete()
        AccessSession.objects.create(user=account,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=timezone.now()+timedelta(hours=8))
        LoginAttempt.objects.filter(ip=ip).delete()
        account.last_login=timezone.now();account.save(update_fields=['last_login'])
    return {'token':token,'user':{'id':account.pk,'name':account.name,'email':account.email,'role':account.role}}


def me(u=None): return {key:u[key] for key in ['id','name','email','role']}


def logout(request,u=None):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    AccessSession.objects.filter(user_id=u['id'],token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
    return {'ok':True}


def change_password(body,u=None):
    account=get_user_model().objects.get(pk=u['id'])
    if not account.check_password(str(body.get('current',''))): raise HTTPException(400,'Current password is incorrect.')
    password=body.get('password','')
    if not isinstance(password,str) or len(password)<12: raise HTTPException(422,'Use at least 12 characters.')
    from django.contrib.auth.password_validation import validate_password
    try: validate_password(password,account)
    except ValidationError as exc: validation_failure(exc)
    with transaction.atomic():
        account.set_password(password);account.save(update_fields=['password'])
        AccessSession.objects.filter(user=account).delete()
        audit(u,'password_change','users',account.pk)
    return {'ok':True}


def users(u=None):
    admin(u)
    return UserSerializer(get_user_model().objects.all().order_by('id'),many=True).data


def create_user(body,u=None):
    admin(u)
    serializer=UserSerializer(data=body);validate_serializer(serializer)
    try:
        with transaction.atomic():
            account=serializer.save();audit(u,'create','users',account.pk)
    except ValidationError as exc: validation_failure(exc)
    except IntegrityError: raise HTTPException(409,'Email already exists.')
    return UserSerializer(account).data


def initialize():
    import os
    User=get_user_model()
    if User.objects.filter(role='admin').exists(): return
    password=os.environ.get('ERP_ADMIN_PASSWORD','')
    if len(password)<12: raise RuntimeError('Set ERP_ADMIN_PASSWORD to at least 12 characters before initialization.')
    User.objects.create_superuser(email='admin@school.local',name='School administrator',password=password)
