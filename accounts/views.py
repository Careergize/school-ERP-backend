from types import SimpleNamespace
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.api import ERPAPIView
from . import services


class LoginAPIView(ERPAPIView):
    public = True

    def post(self, request):
        body = self.object_body(request)
        if not isinstance(body.get('email'), str) or not isinstance(body.get('password'), str):
            raise ValidationError({'detail': 'Email and password must be strings.'})
        proxy = SimpleNamespace(client=SimpleNamespace(host=request.META.get('REMOTE_ADDR', 'unknown')))
        return Response(services.login(services.Login(body['email'], body['password']), proxy))


class CurrentUserAPIView(ERPAPIView):
    def get(self, request):
        return Response(services.me(self.erp_user))


class LogoutAPIView(ERPAPIView):
    def post(self, request):
        return Response(services.logout(request, self.erp_user))


class ChangePasswordAPIView(ERPAPIView):
    def post(self, request):
        return Response(services.change_password(self.object_body(request), self.erp_user))


class UserListAPIView(ERPAPIView):
    admin_only = True

    def get(self, request):
        return Response(services.users(self.erp_user))

    def post(self, request):
        return Response(services.create_user(self.object_body(request), self.erp_user), status=201)
