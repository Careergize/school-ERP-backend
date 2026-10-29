from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from . import models, serializers


class ApplicationListAPIView(RecordListAPIView):
    module = 'admissions'
    model = models.Application
    serializer_class = serializers.ApplicationSerializer


class ApplicationDetailAPIView(RecordDetailAPIView):
    module = 'admissions'
    model = models.Application
    serializer_class = serializers.ApplicationSerializer


class ApplicationExportAPIView(RecordExportAPIView):
    module = 'admissions'
    model = models.Application
    serializer_class = serializers.ApplicationSerializer


from rest_framework.response import Response
from core.api import ERPAPIView
from .services import enroll


class EnrollAPIView(ERPAPIView):
    admin_only = True
    def post(self,request,rid): return Response(enroll(rid,self.erp_user),status=201)
