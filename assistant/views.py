from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from core.api import ERPAPIView
from core.services import HTTPException
from . import services
from .models import Conversation,Report
from .registry import public_registry
from .serializers import ChatInput,ReportInput


class CapabilitiesAPIView(ERPAPIView):
    def get(self,request):
        resources=public_registry(self.erp_user)
        keys={item['key'] for item in resources}
        examples=[question for module,question in [('students','How many students are currently enrolled?'),('students','Show students in Class 10, Section A.'),('attendance',"What is today's attendance percentage?"),('fees','Show students with pending fees.'),('results','What is the average mark for each class?'),('books','How many books are in the library?')] if module in keys]
        return Response({'mode':'local','label':'Local query mode','external_provider':False,'resources':resources,
            'limits':{'page_size':100},'examples':examples})


class ConversationAPIView(ERPAPIView):
    def post(self,request):
        conversation=services.owned_conversation(self.erp_user)
        return Response({'conversation_id':str(conversation.pk)},status=201)


class ConversationDetailAPIView(ERPAPIView):
    def get(self,request,identifier):
        conversation=services.owned_conversation(self.erp_user,identifier)
        last=conversation.results.first()
        return Response({'conversation_id':str(conversation.pk),'latest':services.present(services.accessible_result(self.erp_user,last.pk)) if last else None})


class ChatAPIView(ERPAPIView):
    def post(self,request):
        serializer=ChatInput(data=self.object_body(request));serializer.is_valid(raise_exception=True)
        return Response(services.chat(self.erp_user,**serializer.validated_data))


class ResultAPIView(ERPAPIView):
    def get(self,request,identifier):
        try:
            page=int(request.query_params.get('page',1));size=int(request.query_params.get('page_size',25))
            if page<1 or not 1<=size<=100:raise ValueError
        except ValueError:raise HTTPException(400,'Invalid result pagination.')
        result=services.accessible_result(self.erp_user,identifier)
        return Response(services.present(result,page,size))


class ReportAPIView(ERPAPIView):
    def post(self,request):
        serializer=ReportInput(data=self.object_body(request));serializer.is_valid(raise_exception=True)
        from .reports import create_report
        result=create_report(self.erp_user,**serializer.validated_data)
        return Response(result,status=202 if result['status']=='generating' else 200)


class ReportStatusAPIView(ERPAPIView):
    def get(self,request,identifier):
        try:report=Report.objects.get(pk=identifier,result__conversation__owner_id=self.erp_user['id'])
        except Report.DoesNotExist:raise HTTPException(404,'Report not found.')
        services.accessible_result(self.erp_user,report.result_id)
        from .reports import report_status
        return Response(report_status(report))


class ReportDownloadAPIView(ERPAPIView):
    def get(self,request,identifier):
        try:report=Report.objects.get(pk=identifier,result__conversation__owner_id=self.erp_user['id'])
        except Report.DoesNotExist:raise HTTPException(404,'Report not found.')
        services.accessible_result(self.erp_user,report.result_id)
        if report.expires_at<=timezone.now():raise HTTPException(410,'The report download expired. Run the query again.')
        if report.status!='ready':raise HTTPException(409,'The PDF is not ready. Retry generation or choose a summary report.')
        response=HttpResponse(bytes(report.content),content_type='application/pdf')
        response['Content-Disposition']=f'attachment; filename="school-report-{report.pk}.pdf"'
        response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
        return response
