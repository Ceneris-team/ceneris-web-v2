# recursoshumanos/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite obtener un valor de un diccionario usando una variable como clave.
    Uso: {{ diccionario|get_item:variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)