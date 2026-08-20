"""Consultas reutilizables sobre el calendario de feriados."""
from datetime import date

from ..models import Feriado


def obtener_feriado(fecha: date, sede=None, empresa=None):
    """Devuelve el ``Feriado`` de esa fecha si aplica al scope, o ``None``.

    El scope se resuelve con ``Feriado.aplica_a`` (CAV-13): un feriado nacional
    aplica a todos; uno regional/local solo a su sede; uno de empresa solo a su
    empresa. Como ``fecha`` es única, hay a lo sumo un feriado por día.
    """
    feriado = Feriado.objects.filter(fecha=fecha).first()
    if feriado is not None and feriado.aplica_a(sede=sede, empresa=empresa):
        return feriado
    return None


def es_feriado(fecha: date, sede=None, empresa=None) -> bool:
    """True si la fecha es feriado.

    Sin ``sede``/``empresa`` responde "¿hay feriado ese día para alguien?"
    (compatibilidad con quien solo pregunta por la fecha). Con scope, responde
    si el feriado aplica a ese trabajador en particular.
    """
    if sede is None and empresa is None:
        return Feriado.objects.filter(fecha=fecha).exists()
    return obtener_feriado(fecha, sede=sede, empresa=empresa) is not None


def obtener_feriados_rango(fecha_inicio: date, fecha_fin: date) -> set[date]:
    return set(
        Feriado.objects
        .filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
        .values_list('fecha', flat=True)
    )


# Regla de negocio de la HU-02 (CAV-11): un feriado que ya afecta a tareos
# cerrados queda congelado, porque editarlo o borrarlo alteraria reportes de
# asistencia ya consolidados.
MSG_TAREO_CERRADO = "No es posible modificar ni eliminar un feriado asociado a tareos cerrados"


def tiene_tareos_cerrados(fecha: date) -> bool:
    """True si la fecha ya fue tareada (proxy de 'tareo cerrado').

    Feriado y TareoDiario no tienen FK: se relacionan por la fecha. Si ese dia
    ya tiene tareo, la asistencia de la fecha ya fue procesada y el feriado no
    debe tocarse.
    """
    # Import local: evita el import circular entre administracion y
    # recursoshumanos al cargar las apps.
    from recursoshumanos.models import TareoDiario

    return TareoDiario.objects.filter(fecha=fecha).exists()
