import logging
from html import unescape
from re import sub as re_sub

from django.conf import settings
from django.template import Template, Context
from django.utils import timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition,
)

from .models import EmailLog, PlantillaEmail

logger = logging.getLogger(__name__)


class SendGridEmailService:
    """Servicio centralizado de envío de correo transaccional vía SendGrid."""

    def __init__(self):
        api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        if not api_key:
            raise ValueError(
                'SENDGRID_API_KEY no está configurada en settings. '
                'Defina la variable de entorno SENDGRID_API_KEY.'
            )
        self.client = SendGridAPIClient(api_key)
        self.from_email = getattr(
            settings, 'SENDGRID_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def enviar(
        self,
        destinatario,
        asunto,
        cuerpo_html,
        cuerpo_texto='',
        cc=None,
        bcc=None,
        attachments=None,
        plantilla=None,
        contexto=None,
    ):
        """
        Encola y envía un correo. Registra el intento en EmailLog.

        Args:
            destinatario: email destino (str)
            asunto: asunto del correo (str) — puede contener {{ variables }}
            cuerpo_html: HTML del correo (str) — puede contener {{ variables }}
            cuerpo_texto: texto plano alternativo (str, opcional)
            cc: lista de emails CC (list[str], opcional)
            bcc: lista de emails BCC (list[str], opcional)
            attachments: lista de dicts con keys: content (base64), filename, type
            plantilla: instancia de PlantillaEmail (opcional)
            contexto: dict de variables para renderizar plantilla/asunto/cuerpo

        Returns:
            EmailLog instance
        """
        contexto = contexto or {}

        if plantilla and isinstance(plantilla, str):
            plantilla = PlantillaEmail.objects.filter(
                nombre=plantilla, activa=True
            ).first()

        if plantilla:
            asunto = self._renderizar(plantilla.asunto, contexto)
            cuerpo_html = self._renderizar(plantilla.cuerpo_html, contexto)
            cuerpo_texto = (
                self._renderizar(plantilla.cuerpo_texto, contexto)
                if plantilla.cuerpo_texto
                else self._html_a_texto(cuerpo_html)
            )
        else:
            asunto = self._renderizar(asunto, contexto) if contexto else asunto
            cuerpo_html = self._renderizar(cuerpo_html, contexto) if contexto else cuerpo_html

        if not cuerpo_texto:
            cuerpo_texto = self._html_a_texto(cuerpo_html)

        log = EmailLog.objects.create(
            destinatario=destinatario,
            cc=','.join(cc) if cc else '',
            bcc=','.join(bcc) if bcc else '',
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            cuerpo_texto=cuerpo_texto,
            remitente=self.from_email,
            plantilla=plantilla if isinstance(plantilla, PlantillaEmail) else None,
            contexto_json=contexto,
            estado=EmailLog.Estado.PENDIENTE,
        )

        self._intentar_envio(log, attachments)
        return log

    def enviar_con_plantilla(self, destinatario, nombre_plantilla, contexto, **kwargs):
        """Atajo para enviar usando el nombre de una PlantillaEmail registrada."""
        plantilla = PlantillaEmail.objects.filter(
            nombre=nombre_plantilla, activa=True
        ).first()
        if not plantilla:
            raise ValueError(f'Plantilla "{nombre_plantilla}" no encontrada o inactiva.')
        return self.enviar(
            destinatario=destinatario,
            asunto=plantilla.asunto,
            cuerpo_html=plantilla.cuerpo_html,
            plantilla=plantilla,
            contexto=contexto,
            **kwargs,
        )

    def enviar_con_django_template(
        self, destinatario, asunto, template_name, contexto, **kwargs
    ):
        """
        Envía usando un template de Django (archivo .html en templates/).
        Compatible con las plantillas existentes del proyecto.
        """
        from django.template.loader import render_to_string

        cuerpo_html = render_to_string(template_name, contexto)
        return self.enviar(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            contexto=contexto,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Envío real vía SendGrid
    # ------------------------------------------------------------------

    def _intentar_envio(self, log, attachments=None):
        """Intenta enviar el correo registrado en el EmailLog."""
        log.intentos += 1
        try:
            message = Mail(
                from_email=log.remitente or self.from_email,
                to_emails=log.destinatario,
                subject=log.asunto,
                html_content=log.cuerpo_html,
                plain_text_content=log.cuerpo_texto or None,
            )

            if log.cc:
                for addr in log.cc.split(','):
                    addr = addr.strip()
                    if addr:
                        message.add_cc(addr)

            if log.bcc:
                for addr in log.bcc.split(','):
                    addr = addr.strip()
                    if addr:
                        message.add_bcc(addr)

            if attachments:
                for att in attachments:
                    attachment = Attachment(
                        FileContent(att['content']),
                        FileName(att['filename']),
                        FileType(att.get('type', 'application/octet-stream')),
                        Disposition('attachment'),
                    )
                    message.add_attachment(attachment)

            response = self.client.send(message)

            log.estado = EmailLog.Estado.ENVIADO
            log.enviado_at = timezone.now()
            log.sendgrid_message_id = response.headers.get('X-Message-Id', '')
            log.ultimo_error = ''
            log.save()

            logger.info(
                'Email enviado OK: %s → %s (status=%s)',
                log.asunto, log.destinatario, response.status_code,
            )

        except Exception as exc:
            log.ultimo_error = str(exc)
            if log.intentos >= log.max_intentos:
                log.estado = EmailLog.Estado.DESCARTADO
                logger.error(
                    'Email DESCARTADO tras %d intentos: %s → %s — %s',
                    log.intentos, log.asunto, log.destinatario, exc,
                )
            else:
                log.estado = EmailLog.Estado.FALLIDO
                log.calcular_proximo_reintento()
                logger.warning(
                    'Email FALLIDO (intento %d/%d): %s → %s — %s. '
                    'Próximo reintento: %s',
                    log.intentos, log.max_intentos,
                    log.asunto, log.destinatario, exc, log.proximo_reintento,
                )
            log.save()

    def reintentar_fallidos(self):
        """
        Reintenta todos los emails fallidos cuyo próximo_reintento ya pasó.
        Diseñado para ejecutarse desde un management command via cron.

        Returns:
            dict con conteos de resultados
        """
        ahora = timezone.now()
        pendientes = EmailLog.objects.filter(
            estado=EmailLog.Estado.FALLIDO,
            proximo_reintento__lte=ahora,
        )

        resultados = {'reenviados': 0, 'fallidos': 0, 'descartados': 0}

        for log in pendientes:
            log.estado = EmailLog.Estado.REINTENTANDO
            log.save(update_fields=['estado'])

            self._intentar_envio(log)

            if log.estado == EmailLog.Estado.ENVIADO:
                resultados['reenviados'] += 1
            elif log.estado == EmailLog.Estado.DESCARTADO:
                resultados['descartados'] += 1
            else:
                resultados['fallidos'] += 1

        return resultados

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _renderizar(template_str, contexto):
        """Renderiza un string con sintaxis de Django template."""
        tmpl = Template(template_str)
        return tmpl.render(Context(contexto))

    @staticmethod
    def _html_a_texto(html):
        """Convierte HTML a texto plano básico."""
        texto = re_sub(r'<br\s*/?>', '\n', html)
        texto = re_sub(r'</p>', '\n\n', texto)
        texto = re_sub(r'<[^>]+>', '', texto)
        return unescape(texto).strip()
