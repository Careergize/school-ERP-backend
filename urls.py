"""Project routing: each feature owns its URL configuration."""
from django.urls import include, path

urlpatterns = [
    path('api/v1/assistant/', include('assistant.urls')),
    path('api/v1/', include('core.urls')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/admissions/', include('admissions.urls')),
    path('api/v1/students/', include('students.urls')),
    path('api/v1/academics/', include('academics.urls')),
    path('api/v1/examinations/', include('examinations.urls')),
    path('api/v1/finance/', include('finance.urls')),
    path('api/v1/attendance/', include('attendance.urls')),
    path('api/v1/timetable/', include('timetable.urls')),
    path('api/v1/library/', include('library.urls')),
    path('api/v1/transport/', include('transport.urls')),
    path('api/v1/hostel/', include('hostel.urls')),
    path('api/v1/communication/', include('communication.urls')),
    path('api/v1/hr/', include('hr.urls')),
    path('api/v1/reporting/', include('reporting.urls')),
    path('api/v1/configuration/', include('configuration.urls')),
    path('', include('core.legacy_urls')),
]

# Serve the React production build from port 8000 during local development.
from django.conf import settings
if settings.DEBUG:
    from core.frontend import frontend_index, UI_DIST
    from django.views.static import serve
    urlpatterns += [
        path('', frontend_index, name='frontend'),
        path('assets/<path:path>', serve, {'document_root': UI_DIST/'assets'}, name='frontend-assets'),
    ]
