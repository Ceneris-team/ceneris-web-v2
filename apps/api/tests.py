import hashlib
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from recursoshumanos.models import EventoLoginOffline, Trabajador

# Create your tests here.


class EstadoTrabajadorFeriadoTests(TestCase):
    """CAV-13/CAV-64: el endpoint de estado expone el feriado del día para que
    la app móvil pueda mostrar el banner "Día Feriado"."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='estado_user', password='x')
        self.trabajador = Trabajador.objects.create(
            dni='30000001',
            apellido_paterno='Estado',
            apellido_materno='Test',
            nombres='Usuario',
            user=self.user,
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.url = reverse('trabajador-estado')

    def test_requiere_autenticacion(self):
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_dia_feriado_expone_es_feriado_y_nombre(self):
        from administracion.models import Feriado

        Feriado.objects.create(
            fecha=timezone.localdate(),
            nombre='Fiestas Patrias',
            tipo=Feriado.Tipo.NACIONAL,
            ambito=Feriado.Ambito.NACIONAL,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['es_feriado'])
        self.assertEqual(response.data['nombre_feriado'], 'Fiestas Patrias')

    def test_dia_normal_sin_feriado(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['es_feriado'])
        self.assertIsNone(response.data['nombre_feriado'])

    def test_no_rompe_los_campos_existentes(self):
        response = self.client.get(self.url)
        for campo in ('ultimoTipoMarcacion', 'ubicacionesPermitidas',
                      'tiene_horario', 'es_por_horas', 'meta_horas',
                      'horario_entrada', 'horario_salida', 'es_tardanza',
                      'mensaje_aviso'):
            self.assertIn(campo, response.data)


class UsuariosAutorizadosSyncTests(TestCase):
    """
    CAV-184: pruebas del endpoint de sincronizacion (CAV-182) y de su
    contrato de integridad (checksum determinista).
    """

    def setUp(self):
        User = get_user_model()

        self.caller_user = User.objects.create_user(username='caller_sync', password='x')
        self.caller_trabajador = Trabajador.objects.create(
            dni='10000001',
            apellido_paterno='Caller',
            apellido_materno='Test',
            nombres='Usuario',
            user=self.caller_user,
        )

        self.otro_user = User.objects.create_user(username='otro_autorizado', password='x')
        Trabajador.objects.create(
            dni='10000002',
            apellido_paterno='Otro',
            apellido_materno='Test',
            nombres='Autorizado',
            user=self.otro_user,
        )

        # Trabajador sin cuenta vinculada: NO debe aparecer en la sincronizacion
        Trabajador.objects.create(
            dni='10000003',
            apellido_paterno='SinCuenta',
            apellido_materno='Test',
            nombres='Fantasma',
            user=None,
        )

        self.client = APIClient()
        token = RefreshToken.for_user(self.caller_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.url = reverse('usuarios-autorizados-sync')

    def test_requiere_autenticacion(self):
        client = APIClient()
        response = client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_sync_completo_devuelve_solo_trabajadores_con_usuario(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        dnis = {u['dni'] for u in response.data['usuarios']}
        self.assertIn('10000001', dnis)
        self.assertIn('10000002', dnis)
        self.assertNotIn('10000003', dnis)  # no tiene user vinculado

    def test_respuesta_incluye_checksum_y_version(self):
        response = self.client.get(self.url)
        self.assertIn('checksum', response.data)
        self.assertIn('version', response.data)
        self.assertTrue(len(response.data['checksum']) == 64)  # sha256 hex

    def test_checksum_es_determinista_sin_importar_orden(self):
        from api.views import _calcular_checksum_usuarios

        lista_a = [
            {'dni': '2', 'username': 'b'},
            {'dni': '1', 'username': 'a'},
        ]
        lista_b = [
            {'dni': '1', 'username': 'a'},
            {'dni': '2', 'username': 'b'},
        ]
        self.assertEqual(
            _calcular_checksum_usuarios(lista_a),
            _calcular_checksum_usuarios(lista_b),
        )

    def test_checksum_cambia_si_los_datos_cambian(self):
        from api.views import _calcular_checksum_usuarios

        original = [{'dni': '1', 'username': 'a'}]
        manipulado = [{'dni': '1', 'username': 'a-manipulado'}]
        self.assertNotEqual(
            _calcular_checksum_usuarios(original),
            _calcular_checksum_usuarios(manipulado),
        )

    def test_sync_incremental_con_since_futuro_no_devuelve_nada(self):
        response = self.client.get(self.url, {'since': '2999-01-01T00:00:00Z'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['usuarios'], [])

    def test_sync_con_since_invalido_devuelve_400(self):
        response = self.client.get(self.url, {'since': 'no-es-una-fecha'})
        self.assertEqual(response.status_code, 400)

    def test_sync_incremental_solo_devuelve_cambios_recientes(self):
        # Sincronizacion inicial: "version" queda registrada como cursor.
        primera = self.client.get(self.url)
        cursor = primera.data['version']

        # Nada cambio todavia: el incremental debe venir vacio.
        segunda = self.client.get(self.url, {'since': cursor})
        self.assertEqual(segunda.data['usuarios'], [])

        # Desactivamos a un trabajador -> su actualizado_en se refresca (auto_now)
        self.caller_trabajador.activo = False
        self.caller_trabajador.save()

        tercera = self.client.get(self.url, {'since': cursor})
        dnis = {u['dni'] for u in tercera.data['usuarios']}
        self.assertEqual(dnis, {'10000001'})
        self.assertFalse(tercera.data['usuarios'][0]['activo'])

    def test_checksum_coincide_con_lo_que_realmente_viaja_por_la_red(self):
        """
        Test de regresion (CAV-183): simula exactamente lo que hace el
        cliente movil -> parsea los bytes JSON reales de la respuesta
        HTTP (no el objeto Python interno de Django) y recalcula el
        checksum de la misma forma que 'user_sync_service.dart'. Si el
        checksum se calculara sobre una representacion distinta a la que
        de verdad viaja por la red (como paso con sort_keys=True), esta
        prueba lo detecta.
        """
        response = self.client.get(self.url)
        payload = json.loads(response.content)

        usuarios_como_los_ve_el_cliente = payload['usuarios']
        normalizados = sorted(usuarios_como_los_ve_el_cliente, key=lambda u: u['dni'])
        canonical = json.dumps(normalizados, separators=(',', ':'))
        checksum_recalculado_por_cliente = hashlib.sha256(
            canonical.encode('utf-8')
        ).hexdigest()

        self.assertEqual(checksum_recalculado_por_cliente, payload['checksum'])


class EventoLoginOfflineTests(TestCase):
    """
    CAV-148 (backend): pruebas del endpoint de auditoria de login
    offline (CAV-83).
    """

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(username='offline_user', password='x')
        self.trabajador = Trabajador.objects.create(
            dni='20000001',
            apellido_paterno='Offline',
            apellido_materno='Test',
            nombres='Usuario',
            user=self.user,
        )

        self.client = APIClient()
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.url = reverse('evento-login-offline')

    def test_requiere_autenticacion(self):
        client = APIClient()
        response = client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_registra_el_evento_correctamente(self):
        payload = {
            'device_id': 'device-abc-123',
            'fecha_hora_offline': '2026-08-01T09:15:00Z',
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 201)

        evento = EventoLoginOffline.objects.get(pk=response.data['id'])
        self.assertEqual(evento.trabajador, self.trabajador)
        self.assertEqual(evento.device_id, 'device-abc-123')
        self.assertIsNotNone(evento.fecha_hora_reportado)

    def test_falla_si_faltan_campos(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_falla_si_el_usuario_no_tiene_trabajador_vinculado(self):
        User = get_user_model()
        user_sin_trabajador = User.objects.create_user(username='sin_trabajador', password='x')
        client = APIClient()
        token = RefreshToken.for_user(user_sin_trabajador).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        payload = {
            'device_id': 'device-xyz',
            'fecha_hora_offline': timezone.now().isoformat(),
        }
        response = client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 404)

    def test_multiples_eventos_del_mismo_trabajador_se_acumulan(self):
        for i in range(3):
            self.client.post(self.url, {
                'device_id': f'device-{i}',
                'fecha_hora_offline': timezone.now().isoformat(),
            }, format='json')

        self.assertEqual(
            EventoLoginOffline.objects.filter(trabajador=self.trabajador).count(),
            3,
        )
