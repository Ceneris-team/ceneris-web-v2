from django import template
from datetime import date, timedelta

register = template.Library()

@register.filter
def garantia_status(item):
    # Usamos getattr para obtener la fecha de forma segura,
    # probando ambos nombres de campo.
    fecha_vencimiento = getattr(item, 'fecVencimientoGarantia', None) or getattr(item, 'fecVencGarantia', None)

    if not isinstance(fecha_vencimiento, date):
        return ''
    
    today = date.today()
    un_mes_desde_hoy = today + timedelta(days=30)
    
    if fecha_vencimiento < today:
        return 'vencida'
    elif fecha_vencimiento <= un_mes_desde_hoy:
        return 'proxima'
    else:
        return 'vigente'