import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somali_missions.settings')

app = Celery('somali_missions')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
