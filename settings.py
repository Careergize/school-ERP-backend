import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-development-only-change-before-deployment')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
ROOT_URLCONF = 'urls'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'rest_framework']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.environ.get('ERP_DB', str(BASE_DIR / 'django.sqlite3'))}}
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.middleware.common.CommonMiddleware']
REST_FRAMEWORK = {'UNAUTHENTICATED_USER': None, 'DEFAULT_AUTHENTICATION_CLASSES': [], 'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer']}
USE_TZ = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if not DEBUG and SECRET_KEY == 'local-development-only-change-before-deployment':
    raise RuntimeError('Set DJANGO_SECRET_KEY before disabling development mode.')

# Feature apps own their models, serializers, APIViews, URLs, and migrations.
INSTALLED_APPS += [
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'admissions.apps.AdmissionsConfig',
    'students.apps.StudentsConfig',
    'academics.apps.AcademicsConfig',
    'examinations.apps.ExaminationsConfig',
    'finance.apps.FinanceConfig',
    'attendance.apps.AttendanceConfig',
    'timetable.apps.TimetableConfig',
    'library.apps.LibraryConfig',
    'transport.apps.TransportConfig',
    'hostel.apps.HostelConfig',
    'communication.apps.CommunicationConfig',
    'reporting.apps.ReportingConfig',
    'hr.apps.HrConfig',
    'configuration.apps.ConfigurationConfig',
]

AUTH_USER_MODEL = "accounts.User"
TIME_ZONE = "Asia/Kolkata"

# SQLite is convenient locally; PostgreSQL can be selected for deployment.
if os.environ.get('DATABASE_URL'):
    from urllib.parse import urlparse, unquote
    database_url = urlparse(os.environ['DATABASE_URL'])
    if database_url.scheme not in ['postgres', 'postgresql']:
        raise RuntimeError('DATABASE_URL must use postgres:// or postgresql://.')
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(database_url.path.lstrip('/')),
        'USER': unquote(database_url.username or ''),
        'PASSWORD': unquote(database_url.password or ''),
        'HOST': database_url.hostname or 'localhost',
        'PORT': database_url.port or 5432,
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'prefer')},
    }
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Local-only school data assistant. No external provider or API key is used.
INSTALLED_APPS += ['assistant.apps.AssistantConfig']
ASSISTANT_PLANNER = 'assistant.planner.LocalPlanner'
ASSISTANT_POLICY_VERSION = '1'
ASSISTANT_QUERY_TIMEOUT_SECONDS = 8
ASSISTANT_MAX_SOURCE_ROWS = 20000
ASSISTANT_MAX_RESULT_ROWS = 2500
ASSISTANT_PDF_MAX_ROWS = 1000
ASSISTANT_PDF_MAX_PAGES = 60
ASSISTANT_PDF_MAX_BYTES = 5 * 1024 * 1024
ASSISTANT_PDF_TIMEOUT_SECONDS = 15
ASSISTANT_RESULT_TTL_SECONDS = 3600
ASSISTANT_CHAT_RATE = 20
ASSISTANT_REPORT_RATE = 6
ASSISTANT_LOGO_PATH = os.environ.get('ASSISTANT_LOGO_PATH', '')
ASSISTANT_PDF_FONT = os.environ.get('ASSISTANT_PDF_FONT', '')

ASSISTANT_MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
