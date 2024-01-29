from django.apps import AppConfig


class CrmGeneralConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm_general"

    def ready(self):
        import crm_general.signals
