import logging

from django.core.management.base import BaseCommand

from notificaciones.models import EmailLog
from notificaciones.services import SendGridEmailService

logger = logging.getLogger(__name__)

HTML_PRUEBA = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; font-family:Arial,sans-serif; background:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f5; padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#fff; max-width:600px;">
    <tr>
        <td bgcolor="#e67e22" style="padding:30px; text-align:center;">
            <h1 style="margin:0; color:#fff; font-size:22px;">CENERIS — Correo de Prueba</h1>
        </td>
    </tr>
    <tr>
        <td style="padding:30px;">
            <p style="font-size:16px; color:#333;">Hola <strong>{{ nombre }}</strong>,</p>
            <p style="font-size:14px; color:#555;">
                Este es un correo de prueba enviado desde el servicio de notificaciones
                transaccionales de CENERIS vía SendGrid.
            </p>
            <table width="100%" cellpadding="8" cellspacing="0" border="0"
                   style="margin:20px 0; border:1px solid #ddd;">
                <tr style="background:#f9f9f9;">
                    <td style="font-weight:bold; color:#333;">Servicio</td>
                    <td style="color:#555;">SendGrid API v3</td>
                </tr>
                <tr>
                    <td style="font-weight:bold; color:#333;">Plantillas</td>
                    <td style="color:#555;">{{ estado_plantillas }}</td>
                </tr>
                <tr style="background:#f9f9f9;">
                    <td style="font-weight:bold; color:#333;">Cola de reintentos</td>
                    <td style="color:#555;">{{ estado_reintentos }}</td>
                </tr>
            </table>
            <p style="font-size:12px; color:#999;">
                Si recibiste este correo, el servicio de notificaciones funciona correctamente.
            </p>
        </td>
    </tr>
    <tr>
        <td bgcolor="#333" style="padding:15px; text-align:center;">
            <p style="margin:0; font-size:11px; color:#aaa;">CENERIS &copy; 2026</p>
        </td>
    </tr>
</table>
</td></tr></table>
</body>
</html>
"""


class Command(BaseCommand):
    help = (
        'Envía un correo de prueba vía SendGrid para verificar la '
        'configuración, el registro en EmailLog y la cola de reintentos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Dirección de correo destino para la prueba',
        )
        parser.add_argument(
            '--forzar-fallo',
            action='store_true',
            help='Simula un fallo para probar la cola de reintentos',
        )

    def handle(self, *args, **options):
        email_destino = options['email']
        forzar_fallo = options['forzar_fallo']

        try:
            service = SendGridEmailService()
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        contexto = {
            'nombre': 'Equipo CENERIS',
            'estado_plantillas': 'Activo — plantillas parametrizadas con {{ variables }}',
            'estado_reintentos': 'Activo — backoff exponencial (1, 2, 4, 8, 16 min)',
        }

        if forzar_fallo:
            self._probar_fallo(service, email_destino, contexto)
        else:
            self._probar_envio(service, email_destino, contexto)

        self._mostrar_resumen()

    def _probar_envio(self, service, email_destino, contexto):
        self.stdout.write(f'\nEnviando correo de prueba a: {email_destino}')
        self.stdout.write('-' * 50)

        log = service.enviar(
            destinatario=email_destino,
            asunto='[PRUEBA] CENERIS — Verificación del servicio de correo',
            cuerpo_html=HTML_PRUEBA,
            contexto=contexto,
        )

        if log.estado == EmailLog.Estado.ENVIADO:
            self.stdout.write(self.style.SUCCESS(
                f'ENVIADO — ID: {log.id}, SendGrid MsgID: {log.sendgrid_message_id}'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'FALLIDO — ID: {log.id}, Error: {log.ultimo_error}'
            ))
            self.stdout.write(
                f'  Reintentos: {log.intentos}/{log.max_intentos}, '
                f'Próximo: {log.proximo_reintento}'
            )

    def _probar_fallo(self, service, email_destino, contexto):
        self.stdout.write(self.style.WARNING(
            '\nSimulando fallo para probar cola de reintentos...'
        ))
        self.stdout.write('-' * 50)

        log = EmailLog.objects.create(
            destinatario=email_destino,
            asunto='[PRUEBA-REINTENTO] CENERIS — Test de cola de reintentos',
            cuerpo_html=service._renderizar(HTML_PRUEBA, contexto),
            cuerpo_texto='Correo de prueba de reintentos',
            remitente=service.from_email,
            contexto_json=contexto,
            estado=EmailLog.Estado.FALLIDO,
            intentos=1,
            ultimo_error='Fallo simulado para prueba de reintentos',
        )
        log.calcular_proximo_reintento()
        from django.utils import timezone
        log.proximo_reintento = timezone.now()
        log.save()

        self.stdout.write(self.style.SUCCESS(
            f'EmailLog #{log.id} creado con estado FALLIDO.'
        ))
        self.stdout.write(
            'Ejecute "python manage.py reintentar_emails" para verificar el reintento.'
        )

    def _mostrar_resumen(self):
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('RESUMEN DE LOGS:')
        for estado, label in EmailLog.Estado.choices:
            count = EmailLog.objects.filter(estado=estado).count()
            if count:
                self.stdout.write(f'  {label}: {count}')
        self.stdout.write('=' * 50)
