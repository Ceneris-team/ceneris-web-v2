import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EMO

logger = logging.getLogger(__name__)

# Destinatarios fijos del panorama de EMOs Programados (en vez del grupo
# Django 'Doctor', cuya membresía no es confiable de mantener al día).
DESTINATARIOS_EMO_PROGRAMADOS = ['salud.ocupacional@ceneris.com']
CORREO_COPIA_EMO_PROGRAMADOS = 'habilitaciones@ceneris.com'


def notificar_doctores(nuevo_emo=None, destinatarios_override=None):
    """
    Envía un correo con el panorama de EMOs en estado 'Programado': total,
    sin registrar resultado y/o lectura -vencidos- (rojo) y programados hasta
    la fecha -sin vencer- (amarillo), a DESTINATARIOS_EMO_PROGRAMADOS con
    copia a CORREO_COPIA_EMO_PROGRAMADOS.

    Si se pasa nuevo_emo, se destaca como el EMO recién programado en el correo.

    Si se pasa destinatarios_override (lista de correos), se envía únicamente
    a esos correos (sin copia) en vez de los destinatarios reales — útil para
    pruebas, sin afectar a los destinatarios reales.
    """
    if destinatarios_override:
        destinatarios = destinatarios_override
        copia = None
    else:
        destinatarios = DESTINATARIOS_EMO_PROGRAMADOS
        copia = CORREO_COPIA_EMO_PROGRAMADOS

    hoy = timezone.now().date()
    emos_programados_qs = EMO.objects.filter(estado='Programado').select_related(
        'trabajador', 'empresa', 'proyecto', 'lugar_examen', 'cargo'
    ).order_by('fecha_programada')

    total = emos_programados_qs.count()
    emos_vencidos, emos_programados = [], []

    for e in emos_programados_qs:
        if not e.fecha_programada:
            emos_programados.append(e)
            continue
        dias = (e.fecha_programada - hoy).days
        e.dias_diferencia = dias
        if dias < 0:
            emos_vencidos.append(e)
        else:
            emos_programados.append(e)

    context = {
        'hoy': hoy,
        'total': total,
        'nuevo_emo': nuevo_emo,
        'emos_vencidos': emos_vencidos,
        'emos_programados': emos_programados,
        'total_vencidos': len(emos_vencidos),
        'total_programados': len(emos_programados),
    }

    if nuevo_emo:
        asunto = (
            f"Nuevo EMO Programado — "
            f"{nuevo_emo.trabajador.apellido_paterno} {nuevo_emo.trabajador.apellido_materno}, "
            f"{nuevo_emo.trabajador.nombres}"
        )
    else:
        asunto = f"Resumen Semanal de EMOs Programados — {hoy.strftime('%d/%m/%Y')}"

    if destinatarios_override:
        asunto = f"[PRUEBA] {asunto}"

    try:
        html_content = render_to_string('calidad/emails/reporte_semanal_doctor.html', context)
        email = EmailMultiAlternatives(
            subject=asunto,
            body=(
                f"Total EMOs programados: {total} "
                f"({len(emos_vencidos)} sin registrar resultado y/o lectura, "
                f"{len(emos_programados)} programados hasta la fecha)."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
            cc=[copia] if copia else None,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    except Exception:
        logger.exception("Error notificando el panorama de EMOs programados")
