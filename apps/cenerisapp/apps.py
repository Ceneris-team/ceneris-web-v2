from django.apps import AppConfig


class CenerisappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cenerisapp'

    def ready(self):
        import cenerisapp.signals
