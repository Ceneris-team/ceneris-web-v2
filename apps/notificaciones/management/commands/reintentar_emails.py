import logging

from django.core.management.base import BaseCommand

from notificaciones.services import SendGridEmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Reintenta el envío de correos fallidos cuyo tiempo de espera '
        '(backoff exponencial) ya expiró. Ejecutar vía cron cada 1-2 min.'
    )

    def handle(self, *args, **options):
        try:
            service = SendGridEmailService()
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        resultados = service.reintentar_fallidos()

        msg = (
            f"Reintentos completados — "
            f"reenviados: {resultados['reenviados']}, "
            f"fallidos: {resultados['fallidos']}, "
            f"descartados: {resultados['descartados']}"
        )

        if resultados['reenviados'] or resultados['fallidos'] or resultados['descartados']:
            self.stdout.write(self.style.SUCCESS(msg))
            logger.info(msg)
        else:
            self.stdout.write('No hay emails pendientes de reintento.')
