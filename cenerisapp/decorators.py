
from django.contrib.auth.decorators import user_passes_test

def es_supervisor(user):
    return user.groups.filter(name='Supervisor').exists()

def es_tecnico(user):
    return user.groups.filter(name='Técnico').exists()

supervisor_required = user_passes_test(es_supervisor)
tecnico_required = user_passes_test(es_tecnico)