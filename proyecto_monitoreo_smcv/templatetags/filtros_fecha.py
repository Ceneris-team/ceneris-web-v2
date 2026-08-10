from django import template

register = template.Library()

@register.filter
def fecha_larga_es(fecha):
    """
    Convierte una fecha a formato: '09 julio 2025'
    """
    if not fecha:
        return ""
    
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    
    # fecha.day:02d asegura que el 9 se vea como 09
    return f"{fecha.day:02d} {meses[fecha.month]} {fecha.year}"