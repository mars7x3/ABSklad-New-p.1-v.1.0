from django.apps import AppConfig


class CrmStatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm_stat'

    def ready(self):
        import crm_stat.signals
