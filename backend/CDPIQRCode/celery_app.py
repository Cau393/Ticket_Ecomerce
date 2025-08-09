# CDPIQRCode/celery_app.py

import os
from celery import Celery

# This line is crucial. It sets up the Django environment for Celery.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CDPIQRCode.settings')

app = Celery('CDPIQRCode')

# This tells Celery to load its configuration from your Django settings.py file.
# The `namespace='CELERY'` means all Celery settings must start with CELERY_
# e.g., CELERY_BROKER_URL.
app.config_from_object('django.conf:settings', namespace='CELERY')

# This automatically finds all tasks.py files in your installed apps.
app.autodiscover_tasks()