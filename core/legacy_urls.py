from types import SimpleNamespace
from django.urls import path
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
import services as s

class Endpoint(APIView):
    handler_name = ''
    public = False
    admin_only = False
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except s.HTTPException as exc:
            from django.http import JsonResponse
            return JsonResponse({'detail': exc.detail}, status=exc.status_code)
    def execute(self, request, **kwargs):
        proxy = SimpleNamespace(headers=request.headers, client=SimpleNamespace(host=request.META.get('REMOTE_ADDR', 'unknown')))
        u = None if self.public else s.user(proxy)
        if self.admin_only and u['role'] != 'admin':
            raise s.HTTPException(403, 'Administrator access required.')
        fn = self.handler_name
        if fn == 'records': fn = {'POST':'create','PUT':'update','DELETE':'delete'}[request.method]
        import inspect
        values = dict(kwargs, u=u, request=proxy, body=request.data)
        if fn == 'login': values['body'] = s.Login(**{k: request.data.get(k, '') for k in ['email','password']})
        result = getattr(s, fn)(**{k:v for k,v in values.items() if k in inspect.signature(getattr(s, fn)).parameters})
        return result if isinstance(result, HttpResponse) else Response(result)
    def get(self, request, **kwargs): return self.execute(request, **kwargs)
    def post(self, request, **kwargs): return self.execute(request, **kwargs)
    def put(self, request, **kwargs): return self.execute(request, **kwargs)
    def delete(self, request, **kwargs): return self.execute(request, **kwargs)

# Explicit method allowlists ensure GET requests never invoke mutation handlers.
def endpoint(route, handler, methods, public=False, admin=False):
    view = type(handler.title()+'APIView', (Endpoint,), dict(handler_name=handler, public=public, admin_only=admin, http_method_names=methods+['options']))
    return path('api/'+route, view.as_view())
urlpatterns = [
 endpoint('health','health',['get'],True), endpoint('auth/login','login',['post'],True),
 endpoint('auth/me','me',['get']), endpoint('auth/logout','logout',['post']), endpoint('auth/password','change_password',['post']),
 endpoint('catalog','catalog',['get']), endpoint('data','data',['get']),
 endpoint('records/<str:module>','records',['post']), endpoint('records/<str:module>/<int:rid>','records',['put','delete']),
 endpoint('admissions/<int:rid>/enroll','enroll',['post'],admin=True), endpoint('export/<str:module>','export',['get']),
 endpoint('audit','audit_log',['get'],admin=True),
]
class UsersAPIView(Endpoint):
    admin_only=True
    http_method_names=['get','post','options']
    def execute(self, request, **kwargs):
        self.handler_name = 'users' if request.method == 'GET' else 'create_user'
        return super().execute(request, **kwargs)
urlpatterns.append(path('api/users', UsersAPIView.as_view()))
