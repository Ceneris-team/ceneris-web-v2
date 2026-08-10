from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Uso: {% if request.user|has_group:"Supervisores" %}
    """
    # 1. Protección: Si no está logueado, no tiene grupo.
    if not user.is_authenticated:
        return False
        
    # 2. Optimización: .exists() es más rápido que traer todo el objeto Group
    return user.groups.filter(name=group_name).exists()