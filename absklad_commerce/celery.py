import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'absklad_commerce.settings')

app = Celery('absklad_commerce')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'set_banner_false': {
        'task': 'crm_general.tasks.set_banner_false',
        'schedule': crontab(minute=1, hour=0),
    },
    'sync_balance_1c_to_crm_task': {
        'task': 'one_c.tasks.sync_balance_1c_to_crm',
        'schedule': 3.0,
    },
    'day_stat_task': {
        'task': "crm_stat.tasks.day_stat_task",
        'schedule': crontab(hour=0, minute=2)
    }
}

app.conf.timezone = settings.TIME_ZONE
