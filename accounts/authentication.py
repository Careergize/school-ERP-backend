"""Bearer session authentication integrated with DRF permissions."""
import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .models import AccessSession


class BearerSessionAuthentication(BaseAuthentication):
    def authenticate(self,request):
        parts=get_authorization_header(request).split()
        if not parts: return None
        if len(parts)!=2 or parts[0].lower()!=b'bearer':
            raise AuthenticationFailed('Invalid authorization header.')
        token_hash=hashlib.sha256(parts[1]).hexdigest()
        session=AccessSession.objects.select_related('user').filter(token_hash=token_hash,expires_at__gt=timezone.now(),user__is_active=True).first()
        if session is None: raise AuthenticationFailed('Please sign in again.')
        return session.user,session

    def authenticate_header(self,request): return 'Bearer'
