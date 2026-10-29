"""Reusable APIView behavior for typed model-backed resources."""
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from accounts.authentication import BearerSessionAuthentication
from accounts import services as accounts
from core import services


class ERPAPIView(APIView):
    authentication_classes = [BearerSessionAuthentication]
    permission_classes = [IsAuthenticated]
    public = False
    admin_only = False

    def get_authenticators(self):
        return [] if self.public else super().get_authenticators()

    def get_permissions(self):
        return [AllowAny()] if self.public else super().get_permissions()

    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        self.erp_user=None if self.public else {'id':request.user.pk,'name':request.user.name,'email':request.user.email,'role':request.user.role,'student_id':request.user.student_id,'staff_id':request.user.staff_id,'parent_id':request.user.parent_id}
        if self.admin_only: accounts.admin(self.erp_user)

    def handle_exception(self,exc):
        if isinstance(exc,services.HTTPException):
            payload={'detail':exc.detail}
            if exc.errors: payload['errors']=exc.errors
            return Response(payload,status=exc.status_code)
        return super().handle_exception(exc)

    def object_body(self,request):
        if not isinstance(request.data,dict): raise ValidationError({'detail':'Expected a JSON object.'})
        return request.data

    def respond(self,result,status=200):
        return result if isinstance(result,HttpResponse) else Response(result,status=status)


class RecordListAPIView(ERPAPIView):
    module = None
    model = None
    serializer_class = None

    def get_queryset(self):
        queryset = services.queryset_for(self.module, self.erp_user, self.request.query_params.get('search', ''))
        from django.db import models
        from django.core.exceptions import ValidationError as ModelValidationError
        fields = {('class_id' if field.name == 'school_class' else field.attname):field
                  for field in self.model._meta.fields}
        for key,value in self.request.query_params.items():
            if key in ['search','page','page_size'] or value == '':
                continue
            field = fields.get(key)
            if field is None or field.name in ['password','created_at','updated_at']:
                raise ValidationError({'detail':f'Unsupported filter: {key}.'})
            try:
                if isinstance(field, models.ForeignKey):
                    value = int(value)
                    if value < 1: raise ValueError
                else:
                    value = field.to_python(value)
            except (ValueError,TypeError,ModelValidationError):
                raise ValidationError({'detail':f'Invalid filter value for {key}.'})
            queryset = queryset.filter(**{field.attname:value})
        return queryset

    def get(self,request):
        try:
            page=int(request.query_params.get('page',1));size=int(request.query_params.get('page_size',25))
            if page<1 or not 1<=size<=100: raise ValueError
        except (TypeError,ValueError):
            raise ValidationError({'detail':'page must be positive and page_size must be between 1 and 100.'})
        qs=self.get_queryset();count=qs.count();start=(page-1)*size
        return Response({'count':count,'page':page,'page_size':size,
            'next':page+1 if start+size<count else None,'previous':page-1 if page>1 else None,
            'results':self.serializer_class(qs[start:start+size],many=True).data})

    def post(self,request):
        return Response(services.create(self.module,self.object_body(request),self.erp_user),status=201)


class RecordDetailAPIView(ERPAPIView):
    module = None
    model = None
    serializer_class = None

    def get(self,request,rid):
        instance=services.instance_for(self.module,rid,self.erp_user)
        return Response(self.serializer_class(instance).data)

    def put(self,request,rid):
        return Response(services.update(self.module,rid,self.object_body(request),self.erp_user))

    def delete(self,request,rid):
        services.delete(self.module,rid,self.erp_user)
        return Response(status=204)


class RecordExportAPIView(ERPAPIView):
    module = None
    def get(self,request): return self.respond(services.export(self.module,self.erp_user))


class HealthAPIView(ERPAPIView):
    public = True
    def get(self,request): return Response(services.health())
