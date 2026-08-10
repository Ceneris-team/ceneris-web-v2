# recursoshumanos/signals.py
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Asistencia, TareoDiario

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Asistencia)
def actualizar_tareo_al_guardar_asistencia(sender, instance, raw=False, **kwargs):
    """
    Mantiene el TareoDiario del día sincronizado con las marcaciones reales.

    El recálculo que marca el día como "Asistió" vivía únicamente en la vista
    de la API (el flujo de la app móvil). Si una marcación se creaba por otra
    vía -panel de administración, un script, o una carga manual-, el
    TareoDiario se quedaba con su valor por defecto ('F' = Falta) aunque
    existieran marcaciones reales, y el trabajador figuraba como si hubiera
    faltado.

    Ojo: las inserciones hechas con SQL directo (por fuera del ORM de Django)
    no disparan esta señal. Para esos casos existe el comando de
    mantenimiento `python manage.py recalcular_tareos`.
    """
    # Import local: services importa models, evitamos el import circular.
    from .services import recalcular_asistencia_diaria

    if raw:  # Carga de fixtures: no tocar nada.
        return

    try:
        if not instance.usuario_id or not instance.timestamp:
            return

        trabajador = getattr(instance.usuario, 'trabajador', None)
        if trabajador is None:
            return

        fecha_local = timezone.localtime(instance.timestamp).date()
        tareo = TareoDiario.objects.filter(
            trabajador=trabajador,
            fecha=fecha_local,
        ).first()

        # Si el día no está programado no creamos el tareo: eso evita generar
        # días de trabajo por una marcación suelta (ej. un domingo).
        if tareo is None:
            return

        recalcular_asistencia_diaria(tareo)
    except Exception:
        # Nunca romper el guardado de una marcación por un fallo al
        # recalcular: la marcación es el dato crítico que no se puede perder.
        logger.exception(
            'No se pudo recalcular el TareoDiario para la asistencia %s',
            getattr(instance, 'pk', None),
        )
