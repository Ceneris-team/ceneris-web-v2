from django.apps import AppConfig


class AccesosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accesos'

    def ready(self):
        # CAV-187: conecta el receptor de la señal user_logged_in que
        # invalida sesiones simultaneas para usuarios no-admin.
        from . import signals  # noqa: F401
