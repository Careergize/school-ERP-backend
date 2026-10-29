"""Create the first administrator after applying Django migrations."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()
from accounts.services import initialize

if __name__ == '__main__':
    initialize()
    print('Administrator ready. Sign in as admin@school.local using the supplied password.')
