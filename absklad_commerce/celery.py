import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('main')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'set_banner_false': {
        'task': 'crm_general.tasks.set_banner_false',
        'schedule': crontab(minute=1, hour=0),
    },
}

app.conf.timezone = settings.TIME_ZONE
