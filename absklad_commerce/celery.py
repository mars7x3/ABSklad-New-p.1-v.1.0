import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'absklad_commerce.settings')

app = Celery('absklad_commerce')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    # banner tasks
    'set_banner_false': {
        'task': 'crm_general.marketer.tasks.set_banner_false',
        # 'schedule': crontab(minute=1, hour=0),
        'schedule': 600.0,
    },
    'set_banner_true': {
        'task': 'crm_general.marketer.tasks.set_banner_true',
        # 'schedule': crontab(minute=1, hour=0),
        'schedule': 600.0,
    },

    # kpi tasks
    'create_kpi': {
        'task': 'crm_kpi.tasks.create_kpi',
        # 'schedule': crontab(day_of_month='1'),
        'schedule': 800.0,
    },
    'confirm_dealer_kpis': {
        'task': 'crm_kpi.tasks.confirm_dealer_kpis',
        # 'schedule': crontab(day_of_month='5'),
        'schedule': 800.0,
    },

    # discount tasks
    'discount_start': {
        'task': 'crm_general.tasks.calculate_discount_product_price',
        # 'schedule': crontab(minute=1, hour=0),
        'schedule': 600.0,
    },
    'discount_end': {
        'task': 'crm_general.tasks.update_product_prices_after_ended_discount',
        # 'schedule': crontab(minute=1, hour=0),
        'schedule': 600.0,
    },

    # sync 1c task
    'sync_balance_1c_to_crm_task': {
        'task': 'one_c.tasks.sync_balance_1c_to_crm',
        'schedule': 3.0,
    },
}

app.conf.timezone = settings.TIME_ZONE
