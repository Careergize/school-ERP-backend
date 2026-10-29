from rest_framework.response import Response
from core.api import ERPAPIView
from core import services as core
from .services import summary


class SummaryAPIView(ERPAPIView):
    def get(self, request):
        return Response(summary(self.erp_user))


class WorkspaceSnapshotAPIView(ERPAPIView):
    """Bootstrap endpoint for the current UI's cross-module reference selectors."""
    def get(self, request):
        return Response(core.data(self.erp_user))


class AuditLogAPIView(ERPAPIView):
    admin_only = True

    def get(self, request):
        return Response(core.audit_log(self.erp_user))
