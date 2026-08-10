# en tu_app/templatetags/custom_filters.py

from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    # Si el 'dictionary' es None o no es un diccionario, devolvemos None
    # en lugar de lanzar un error.
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)