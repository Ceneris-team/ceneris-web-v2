# en cenerisapp/templatetags/pdf_filters.py
from django import template
from django.conf import settings
import os

register = template.Library()

@register.simple_tag
def static_path(path):
    """
    Devuelve la ruta absoluta del sistema de archivos a un archivo estático.
    """

    # Usamos STATIC_ROOT en producción (Render) y STATICFILES_DIRS en desarrollo
    if settings.DEBUG:
        # En desarrollo, busca en el primer directorio de STATICFILES_DIRS
        static_dir = settings.STATICFILES_DIRS[0]
        file_path = os.path.join(static_dir, path)
    else:
        # En producción (Render), busca en STATIC_ROOT
        static_dir = settings.STATIC_ROOT
        file_path = os.path.join(static_dir, path)
    
    # Convierte a un formato de URL de archivo local que WeasyPrint entiende
    return f'file://{file_path}'