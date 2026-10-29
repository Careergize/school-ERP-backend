from django.urls import path
from .views import ModuleCatalogAPIView, ModuleMetadataAPIView, AppDirectoryAPIView

app_name = 'configuration'
urlpatterns = [
    path('modules/', ModuleCatalogAPIView.as_view(), name='module-list'),
    path('modules/<str:module>/', ModuleMetadataAPIView.as_view(), name='module-metadata'),
    path('apps/', AppDirectoryAPIView.as_view(), name='app-directory'),
]

from .views import SchoolSettingsListAPIView, SchoolSettingsDetailAPIView, SchoolSettingsExportAPIView
urlpatterns += [
    path('school_settings/', SchoolSettingsListAPIView.as_view(), name='school-settings-list'),
    path('school_settings/export/', SchoolSettingsExportAPIView.as_view(), name='school-settings-export'),
    path('school_settings/<int:rid>/', SchoolSettingsDetailAPIView.as_view(), name='school-settings-detail'),
]
