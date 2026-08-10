# administracion/decorators.py

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def group_required(*group_names):
    """Requires user to be in at least one of the given groups."""
    def in_groups(u):
        if u.is_authenticated:
            # Permite el acceso si el usuario está en alguno de los grupos O si es un superusuario
            if bool(u.groups.filter(name__in=group_names)) or u.is_superuser:
                return True
        # Si no cumple las condiciones, lanza el error de Permiso Denegado
        raise PermissionDenied
    return user_passes_test(in_groups)