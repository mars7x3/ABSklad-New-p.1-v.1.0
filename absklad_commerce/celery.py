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
        'schedule': crontab(day_of_month='25'),
    },
    'confirm_dealer_kpis': {
        'task': 'crm_kpi.tasks.confirm_dealer_kpis',
        'schedule': crontab(day_of_month='1'),
    },

    # discount tasks
    'discount_activate': {
        'task': 'promotion.tasks.activate_discount',
        # 'schedule': crontab(minute=1, hour=0),
        'schedule': 600.0,
    },
    'discount_deactivate': {
        'task': 'promotion.tasks.deactivate_discount',
        'schedule': crontab(minute=1, hour=0),
    },

    'create_notifications': {
        'task': 'crm_general.marketer.tasks.create_notifications',
        # 'schedule': crontab(hour=8, minute=0),
        'schedule': 600.0,
    },

    'create_birthday_recommend_notifications': {
        'task': 'crm_general.marketer.tasks.create_birthday_recommend_notifications',
        'schedule': crontab(hour=8, minute=0),
    },

    'set_story': {
        'task': 'promotion.tasks.story_setter',
        'schedule': 1200.0,
    },

    # sync 1c task: BALANCE
    'sync_balance_1c_to_crm_task': {
        'task': 'one_c.tasks.sync_balance_1c_to_crm',
        'schedule': 5.0,
    },

    # sync 1c task: COUNT
    'sync_product_count_task': {
        'task': 'one_c.tasks.sync_product_count',
        'schedule': 20.0,
    },
    'day_stat_task': {
        'task': "crm_stat.tasks.day_stat_task",
        'schedule': crontab(hour=0, minute=2)
    },
    #
    'checking_update_crm_tasks': {
        'task': "crm_general.director.tasks.update_expired_crm_tasks",
        'schedule': 60.0
    }
}

app.conf.timezone = settings.TIME_ZONE
app.conf.update(result_extended=True)
