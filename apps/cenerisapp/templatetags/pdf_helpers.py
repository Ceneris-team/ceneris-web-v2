# en cenerisapp/templatetags/pdf_helpers.py
from django import template
from django.contrib.staticfiles import finders

register = template.Library()

@register.simple_tag
def static_file(path):
    """
    Devuelve una URL 'file://' con la ruta absoluta a un archivo estático.
    """
    # finders.find() es el método más robusto
    absolute_path = finders.find(path)
    if absolute_path:
        return f'file://{absolute_path}'
    # Si no lo encuentra, devuelve una cadena vacía para evitar errores
    print(f"ADVERTENCIA en PDF: No se pudo encontrar el archivo estático '{path}'")
    return ''