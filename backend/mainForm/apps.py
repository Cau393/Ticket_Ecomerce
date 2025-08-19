from django.apps import AppConfig


class MainformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mainForm'

    def ready(self):
        import mainForm.signals
