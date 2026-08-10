from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Toma los parámetros GET actuales, los actualiza con los nuevos
    parámetros proporcionados y devuelve la cadena de consulta codificada.
    """
    # Hacemos una copia mutable del diccionario GET de la petición actual
    query = context['request'].GET.copy()
    
    # Sobrescribimos o añadimos los nuevos parámetros que nos pasen
    for key, value in kwargs.items():
        query[key] = value
        
    # Devolvemos la cadena de consulta codificada
    return query.urlencode()

@register.simple_tag(takes_context=True)
def url_replace_arg(context, arg_name, arg_value):
    query = context['request'].GET.copy()
    query[arg_name] = arg_value
    return query.urlencode()