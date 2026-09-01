from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from .access_matrix import ACCESS_MATRIX
from .models import SesionCerradaRemotamente


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


class AvisoSesionCerradaMiddleware:
    """
    CAV-187 (mejora): inyecta el vigilante de sesion unica al final de cada
    pagina HTML que ve un usuario autenticado.

    Se hace por middleware y no por `{% include %}` porque el proyecto
    tiene ocho plantillas base independientes; asi el aviso llega a
    todas sin tocarlas una por una.
    """

    # Prefijos donde el vigilante no aporta nada (respuestas de API,
    # descargas del admin de Django, archivos estaticos).
    RUTAS_EXCLUIDAS = ('/api/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self._debe_inyectar(request, response):
            return response
        return self._inyectar(request, response)

    def _debe_inyectar(self, request, response):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser and getattr(settings, 'SESION_UNICA_EXIMIR_SUPERUSUARIO', True):
            # El superusuario esta exento de la sesion unica (CAV-187),
            # asi que no tiene nada que vigilar.
            return False
        if request.path.startswith(self.RUTAS_EXCLUIDAS):
            return False
        if getattr(response, 'streaming', False) or response.status_code != 200:
            return False
        return 'text/html' in response.get('Content-Type', '')

    @staticmethod
    def _inyectar(request, response):
        try:
            html = response.content.decode(response.charset)
        except (AttributeError, UnicodeDecodeError):
            return response

        posicion = html.lower().rfind('</body>')
        if posicion == -1:
            # Fragmento HTML (respuesta parcial de HTMX o similar): no
            # es una pagina completa, no se toca.
            return response

        snippet = render_to_string(
            'accesos/vigilante_sesion.html',
            {
                'url_estado_sesion': reverse('accesos:estado_sesion'),
                'url_login': settings.LOGIN_URL,
                'intervalo_ms': getattr(settings, 'SESION_UNICA_INTERVALO_SEGUNDOS', 15) * 1000,
                'segundos_redireccion': getattr(settings, 'SESION_UNICA_SEGUNDOS_REDIRECCION', 5),
                'motivo_sesion_duplicada': SesionCerradaRemotamente.MOTIVO_SESION_DUPLICADA,
            },
            request=request,
        )
        response.content = (html[:posicion] + snippet + html[posicion:]).encode(response.charset)
        if response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))
        return response
