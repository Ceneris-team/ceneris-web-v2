from django.http import JsonResponse
from django.shortcuts import render

from .access_matrix import ACCESS_MATRIX


class PlatformAccessMiddleware:
    """
    CAV-186: aplica la matriz de grupos/plataformas de CAV-185 en cada
    request. Debe ir despues de AuthenticationMiddleware en MIDDLEWARE
    (necesita `request.user` ya resuelto).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        denegado = self._verificar_acceso(request)
        if denegado is not None:
            return denegado
        return self.get_response(request)

    def _verificar_acceso(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            # Sin sesion: lo maneja @login_required / LoginView de cada
            # vista, no es responsabilidad de este middleware.
            return None

        if user.is_superuser:
            # Regla critica de negocio: el superusuario nunca queda
            # bloqueado por restricciones de plataforma.
            return None

        grupos_permitidos = self._grupos_para_ruta(request.path)
        if grupos_permitidos is None:
            # Ruta fuera de la matriz, o dentro de ella pero abierta a
            # cualquier grupo (regla general del movil / Metricas).
            return None

        if user.groups.filter(name__in=grupos_permitidos).exists():
            return None

        mensaje = 'No tienes permiso para acceder a esta seccion.'
        if request.path.startswith('/api/'):
            return JsonResponse({'detail': mensaje}, status=403)
        return render(request, 'accesos/acceso_restringido.html', status=403)

    @staticmethod
    def _grupos_para_ruta(path):
        # Prefijos mas largos primero, por si en el futuro se agregan
        # sub-rutas mas especificas dentro de un prefijo ya listado.
        for prefijo in sorted(ACCESS_MATRIX, key=len, reverse=True):
            if path.startswith(prefijo):
                return ACCESS_MATRIX[prefijo]
        return None
