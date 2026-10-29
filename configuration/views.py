from rest_framework.response import Response
from core.api import ERPAPIView
from core.registry import MODULES
from core.services import HTTPException
from .services import module_catalog, app_directory


class ModuleCatalogAPIView(ERPAPIView):
    def get(self,request): return Response(module_catalog(self.erp_user))


class ModuleMetadataAPIView(ERPAPIView):
    """Read-only model metadata for React form rendering."""
    def get(self,request,module):
        if module not in MODULES: raise HTTPException(404,'Unknown module.')
        return Response(module_catalog(self.erp_user)[module])


class AppDirectoryAPIView(ERPAPIView):
    def get(self,request): return Response(app_directory())

from core.api import RecordListAPIView, RecordDetailAPIView, RecordExportAPIView
from .models import SchoolSettings
from .serializers import SchoolSettingsSerializer


class SchoolSettingsListAPIView(RecordListAPIView):
    module = 'school_settings'
    model = SchoolSettings
    serializer_class = SchoolSettingsSerializer


class SchoolSettingsDetailAPIView(RecordDetailAPIView):
    module = 'school_settings'
    model = SchoolSettings
    serializer_class = SchoolSettingsSerializer


class SchoolSettingsExportAPIView(RecordExportAPIView):
    module = 'school_settings'
