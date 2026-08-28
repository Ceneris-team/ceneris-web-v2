from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from .middleware import PlatformAccessMiddleware
from .models import SesionCerradaRemotamente

User = get_user_model()


def _dummy_get_response(request):
    return HttpResponse('OK')


class PlatformAccessMiddlewareTests(TestCase):
    """CAV-188: prueba la matriz de CAV-185 contra todos los grupos y
    todas las plataformas."""

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()

        # La migracion 0001_grupos_iniciales (CAV-185) ya crea estos
        # grupos; los recuperamos en vez de volver a crearlos.
        cls.grupo_rrhh = Group.objects.get(name='Recursos Humanos')
        cls.grupo_calidad = Group.objects.get(name='Calidad')
        cls.grupo_admin = Group.objects.get(name='Administrador')
        cls.grupo_supervisores = Group.objects.get(name='Supervisores')

        cls.usuario_rrhh = User.objects.create_user(username='rrhh', password='x')
        cls.usuario_rrhh.groups.add(cls.grupo_rrhh)

        cls.usuario_calidad = User.objects.create_user(username='calidad', password='x')
        cls.usuario_calidad.groups.add(cls.grupo_calidad)

        cls.usuario_supervisor = User.objects.create_user(username='supervisor', password='x')
        cls.usuario_supervisor.groups.add(cls.grupo_supervisores)

        cls.usuario_admin_grupo = User.objects.create_user(username='admin_grupo', password='x')
        cls.usuario_admin_grupo.groups.add(cls.grupo_admin)

        cls.usuario_sin_grupo = User.objects.create_user(username='sin_grupo', password='x')

        cls.superuser = User.objects.create_superuser(
            username='root', password='x', email='root@ceneris.test'
        )

    def setUp(self):
        self.middleware = PlatformAccessMiddleware(_dummy_get_response)

    def _request(self, path, user):
        request = self.factory.get(path)
        request.user = user
        return request

    # --- /recursoshumanos/ : Recursos Humanos y Supervisores ---

    def test_rrhh_entra_a_recursoshumanos(self):
        response = self.middleware(self._request('/recursoshumanos/', self.usuario_rrhh))
        self.assertEqual(response.status_code, 200)

    def test_supervisor_entra_a_recursoshumanos(self):
        response = self.middleware(self._request('/recursoshumanos/', self.usuario_supervisor))
        self.assertEqual(response.status_code, 200)

    def test_calidad_no_entra_a_recursoshumanos(self):
        response = self.middleware(self._request('/recursoshumanos/', self.usuario_calidad))
        self.assertEqual(response.status_code, 403)

    def test_sin_grupo_no_entra_a_recursoshumanos(self):
        response = self.middleware(self._request('/recursoshumanos/', self.usuario_sin_grupo))
        self.assertEqual(response.status_code, 403)

    # --- /calidad/ : solo Calidad ---

    def test_calidad_entra_a_calidad(self):
        response = self.middleware(self._request('/calidad/', self.usuario_calidad))
        self.assertEqual(response.status_code, 200)

    def test_rrhh_no_entra_a_calidad(self):
        response = self.middleware(self._request('/calidad/', self.usuario_rrhh))
        self.assertEqual(response.status_code, 403)

    def test_supervisor_no_entra_a_calidad(self):
        response = self.middleware(self._request('/calidad/', self.usuario_supervisor))
        self.assertEqual(response.status_code, 403)

    # --- /metricas_ceneris/ : cualquier grupo ---

    def test_cualquier_grupo_entra_a_metricas(self):
        for user in [
            self.usuario_rrhh,
            self.usuario_calidad,
            self.usuario_supervisor,
            self.usuario_admin_grupo,
            self.usuario_sin_grupo,
        ]:
            response = self.middleware(self._request('/metricas_ceneris/', user))
            self.assertEqual(response.status_code, 200, msg=f'fallo para {user.username}')

    # --- /admin/ : solo Administrador ---

    def test_grupo_administrador_entra_al_admin_panel(self):
        response = self.middleware(self._request('/admin/', self.usuario_admin_grupo))
        self.assertEqual(response.status_code, 200)

    def test_rrhh_no_entra_al_admin_panel(self):
        response = self.middleware(self._request('/admin/', self.usuario_rrhh))
        self.assertEqual(response.status_code, 403)

    def test_calidad_no_entra_al_admin_panel(self):
        response = self.middleware(self._request('/admin/', self.usuario_calidad))
        self.assertEqual(response.status_code, 403)

    # --- /api/ (movil): regla general, todo autenticado entra ---

    def test_cualquier_autenticado_entra_a_api_sin_importar_grupo(self):
        for user in [self.usuario_rrhh, self.usuario_calidad, self.usuario_sin_grupo]:
            response = self.middleware(self._request('/api/token/', user))
            self.assertEqual(response.status_code, 200)

    # --- Bypass de superusuario (regla critica de negocio) ---

    def test_superuser_entra_a_todo_sin_tener_ningun_grupo(self):
        for path in ['/recursoshumanos/', '/calidad/', '/admin/', '/metricas_ceneris/', '/api/token/']:
            response = self.middleware(self._request(path, self.superuser))
            self.assertEqual(response.status_code, 200, msg=f'fallo en {path}')

    # --- Usuario no autenticado: no es responsabilidad de este middleware ---

    def test_usuario_no_autenticado_pasa_de_largo(self):
        request = self.factory.get('/recursoshumanos/')
        request.user = AnonymousUser()
        response = self.middleware(request)
        # No lo bloquea aqui; @login_required / LoginRequiredMixin de
        # cada vista es quien debe rechazarlo despues.
        self.assertEqual(response.status_code, 200)

    # --- Ruta fuera de la matriz: no se toca (fuera de alcance de CAV-20) ---

    def test_ruta_no_listada_no_se_restringe(self):
        response = self.middleware(self._request('/proyectos/', self.usuario_sin_grupo))
        self.assertEqual(response.status_code, 200)

    # --- Formato de la respuesta 403 segun la plataforma ---

    def test_403_en_web_no_es_json(self):
        response = self.middleware(self._request('/calidad/', self.usuario_rrhh))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('application/json', response.get('Content-Type', ''))

    @patch.dict('accesos.middleware.ACCESS_MATRIX', {'/api/secreta/': ['Administrador']}, clear=True)
    def test_403_en_api_devuelve_json(self):
        response = self.middleware(self._request('/api/secreta/', self.usuario_rrhh))
        self.assertEqual(response.status_code, 403)
        self.assertIn('application/json', response['Content-Type'])


class SesionSimultaneaTests(TestCase):
    """CAV-187: un usuario no-admin no puede tener mas de una sesion
    web activa; el superusuario esta exento."""

    @classmethod
    def setUpTestData(cls):
        cls.trabajador = User.objects.create_user(username='trabajador', password='clave12345')
        cls.superuser = User.objects.create_superuser(
            username='rootadmin', password='clave12345', email='root2@ceneris.test'
        )

    def test_segundo_login_invalida_la_sesion_anterior(self):
        cliente_1 = Client()
        cliente_2 = Client()

        self.assertTrue(cliente_1.login(username='trabajador', password='clave12345'))
        session_key_1 = cliente_1.session.session_key
        self.assertIsNotNone(session_key_1)
        self.assertTrue(Session.objects.filter(session_key=session_key_1).exists())

        self.assertTrue(cliente_2.login(username='trabajador', password='clave12345'))

        self.assertFalse(Session.objects.filter(session_key=session_key_1).exists())

    def test_superuser_puede_tener_sesiones_simultaneas(self):
        cliente_1 = Client()
        cliente_2 = Client()

        self.assertTrue(cliente_1.login(username='rootadmin', password='clave12345'))
        session_key_1 = cliente_1.session.session_key
        self.assertIsNotNone(session_key_1)

        self.assertTrue(cliente_2.login(username='rootadmin', password='clave12345'))

        self.assertTrue(Session.objects.filter(session_key=session_key_1).exists())


class AvisoSesionCerradaTests(TestCase):
    """CAV-187 (mejora): el dispositivo desplazado debe enterarse de
    por que perdio la sesion, no aparecer en el login sin explicacion."""

    @classmethod
    def setUpTestData(cls):
        cls.trabajador = User.objects.create_user(username='trabajador2', password='clave12345')
        cls.superuser = User.objects.create_superuser(
            username='rootadmin2', password='clave12345', email='root3@ceneris.test'
        )

    def _desplazar_sesion(self, username='trabajador2'):
        """Loguea dos clientes y devuelve el que quedo desplazado."""
        cliente_1 = Client()
        cliente_2 = Client()
        self.assertTrue(cliente_1.login(username=username, password='clave12345'))
        session_key_1 = cliente_1.session.session_key
        self.assertTrue(cliente_2.login(username=username, password='clave12345'))
        return cliente_1, session_key_1

    def test_se_registra_el_aviso_al_cerrar_la_sesion_anterior(self):
        _, session_key_1 = self._desplazar_sesion()

        aviso = SesionCerradaRemotamente.objects.get(session_key=session_key_1)
        self.assertEqual(aviso.usuario, self.trabajador)
        self.assertFalse(aviso.avisado)

    def test_superuser_no_genera_aviso(self):
        self._desplazar_sesion(username='rootadmin2')

        self.assertFalse(SesionCerradaRemotamente.objects.exists())

    @override_settings(SESION_UNICA_EXIMIR_SUPERUSUARIO=False)
    def test_superuser_si_recibe_aviso_con_la_excepcion_apagada(self):
        """El interruptor de desarrollo permite probar el aviso con una
        cuenta de administrador sin crear un usuario de prueba."""
        cliente_1, session_key_1 = self._desplazar_sesion(username='rootadmin2')

        self.assertFalse(Session.objects.filter(session_key=session_key_1).exists())
        datos = cliente_1.get('/seguridad/estado-sesion/').json()
        self.assertEqual(datos['motivo'], SesionCerradaRemotamente.MOTIVO_SESION_DUPLICADA)

    def test_estado_sesion_avisa_al_navegador_desplazado(self):
        cliente_1, _ = self._desplazar_sesion()

        respuesta = cliente_1.get('/seguridad/estado-sesion/')
        datos = respuesta.json()

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(datos['activa'])
        self.assertEqual(datos['motivo'], SesionCerradaRemotamente.MOTIVO_SESION_DUPLICADA)
        self.assertEqual(datos['segundos_redireccion'], 5)
        self.assertIn('/accounts/login/', datos['login_url'])
        self.assertIn(SesionCerradaRemotamente.MOTIVO_SESION_DUPLICADA, datos['login_url'])

    def test_estado_sesion_responde_activa_con_sesion_vigente(self):
        cliente = Client()
        self.assertTrue(cliente.login(username='trabajador2', password='clave12345'))

        datos = cliente.get('/seguridad/estado-sesion/').json()

        self.assertTrue(datos['activa'])

    def test_estado_sesion_sin_cookie_no_inventa_motivo(self):
        datos = Client().get('/seguridad/estado-sesion/').json()

        self.assertFalse(datos['activa'])
        self.assertEqual(datos['motivo'], 'sin_sesion')

    def test_login_muestra_el_aviso_una_sola_vez(self):
        cliente_1, session_key_1 = self._desplazar_sesion()

        primera = cliente_1.get('/accounts/login/')
        self.assertContains(primera, 'se inició sesión con esta misma cuenta')
        self.assertTrue(SesionCerradaRemotamente.objects.get(session_key=session_key_1).avisado)

        segunda = cliente_1.get('/accounts/login/')
        self.assertNotContains(segunda, 'se inició sesión con esta misma cuenta')

    def test_pagina_web_lleva_el_vigilante_inyectado(self):
        cliente = Client()
        self.assertTrue(cliente.login(username='trabajador2', password='clave12345'))

        respuesta = cliente.get('/seguridad/portal/')

        self.assertContains(respuesta, 'cav-aviso-sesion')
        self.assertContains(respuesta, '/seguridad/estado-sesion/')

    def test_el_vigilante_no_se_inyecta_en_respuestas_json(self):
        cliente = Client()
        self.assertTrue(cliente.login(username='trabajador2', password='clave12345'))

        respuesta = cliente.get('/seguridad/estado-sesion/')

        self.assertNotIn(b'cav-aviso-sesion', respuesta.content)

    def test_purga_de_avisos_antiguos(self):
        SesionCerradaRemotamente.objects.create(
            session_key='clave-vieja', usuario=self.trabajador,
            fecha_cierre=timezone.now() - timedelta(days=30),
        )
        SesionCerradaRemotamente.objects.create(
            session_key='clave-reciente', usuario=self.trabajador,
        )

        SesionCerradaRemotamente.purgar_antiguas(dias=7)

        claves = list(SesionCerradaRemotamente.objects.values_list('session_key', flat=True))
        self.assertEqual(claves, ['clave-reciente'])
