"""Consultas reutilizables sobre el calendario de feriados."""
from datetime import date

from ..models import Feriado


def es_feriado(fecha: date) -> bool:
    return Feriado.objects.filter(fecha=fecha).exists()


def obtener_feriados_rango(fecha_inicio: date, fecha_fin: date) -> set[date]:
    return set(
        Feriado.objects
        .filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
        .values_list('fecha', flat=True)
    )
