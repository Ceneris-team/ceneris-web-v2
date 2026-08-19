import logging
from datetime import date

from django.contrib.auth.models import Group, User

from .services import SendGridEmailService

logger = logging.getLogger(__name__)


def _obtener_emails_grupo(nombre_grupo):
    """Retorna los emails de los usuarios activos de un grupo Django."""
    try:
        grupo = Group.objects.get(name=nombre_grupo)
    except Group.DoesNotExist:
        logger.warning('Grupo "%s" no existe — no se enviarán correos.', nombre_grupo)
        return []

    return list(
        User.objects.filter(
            groups=grupo,
            is_active=True,
        )
        .exclude(email='')
        .values_list('email', flat=True)
    )


def notificar_solicitud_horas_extra(solicitud, request=None):
    """
    Envía un correo a los Supervisores notificando una nueva solicitud
    de horas extra que requiere aprobación.

    Args:
        solicitud: instancia de SolicitudHorasExtra recién creada
        request: HttpRequest (opcional) para construir la URL absoluta
    """
    destinatarios = _obtener_emails_grupo('Supervisores')
    if not destinatarios:
        logger.warning(
            'No hay supervisores con email para notificar la solicitud #%s',
            solicitud.pk,
        )
        return

    trabajador = solicitud.trabajador
    nombre_completo = (
        f'{trabajador.nombres} {trabajador.apellido_paterno} '
        f'{trabajador.apellido_materno}'
    )

    enlace = ''
    if request:
        from django.urls import reverse
        ruta = reverse('recursoshumanos:panel_aprobacion_he')
        enlace = request.build_absolute_uri(ruta)

    contexto = {
        'trabajador_nombre': nombre_completo,
        'trabajador_dni': trabajador.dni,
        'trabajador_area': str(trabajador.area) if trabajador.area else '',
        'fecha_horas_extra': solicitud.fecha_horas_extra.strftime('%d/%m/%Y'),
        'cantidad_horas': str(solicitud.cantidad_horas),
        'justificacion': solicitud.justificacion,
        'origen': 'Aplicación móvil' if solicitud.solicitado_desde_app else 'Web',
        'enlace_aprobacion': enlace,
        'anio': date.today().year,
    }

    try:
        servicio = SendGridEmailService()
    except ValueError:
        logger.error('SendGrid no configurado — no se pudo notificar solicitud #%s', solicitud.pk)
        return

    primer_destinatario = destinatarios[0]
    cc = destinatarios[1:] if len(destinatarios) > 1 else None

    servicio.enviar_con_django_template(
        destinatario=primer_destinatario,
        asunto=f'Nueva solicitud de horas extra — {nombre_completo}',
        template_name='notificaciones/emails/solicitud_horas_extra.html',
        contexto=contexto,
        cc=cc,
    )

    logger.info(
        'Notificación de solicitud #%s enviada a %d supervisor(es)',
        solicitud.pk, len(destinatarios),
    )
