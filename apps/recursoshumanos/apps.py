from django.apps import AppConfig


class RecursoshumanosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recursoshumanos'

    def ready(self):
        import recursoshumanos.signals
