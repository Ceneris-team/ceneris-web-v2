import hashlib
import json
import uuid
from datetime import datetime, time as dt_time, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from recursoshumanos.models import (
    Asistencia,
    ConfiguracionTolerancia,
    EventoLoginOffline,
    IntentoFraude,
    Sede,
    TareoDiario,
    Trabajador,
)

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


class _MarcacionBaseTests(TestCase):
    """Infraestructura común de las pruebas del endpoint de marcación."""

    DEVICE_ID = 'device-faena-001'

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='marcador', password='x')
        self.sede = Sede.objects.create(nombre='Faena Cerro Verde')
        self.trabajador = Trabajador.objects.create(
            dni='40000001',
            apellido_paterno='Quispe',
            apellido_materno='Mamani',
            nombres='Juan',
            user=self.user,
            sede=self.sede,
        )
        self.client = APIClient()
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.url = reverse('registrar-asistencia')

    def _instante(self, fecha, hora=8, minuto=0):
        """Devuelve un datetime aware en America/Lima para esa fecha y hora."""
        return timezone.make_aware(datetime.combine(fecha, dt_time(hora, minuto)))

    def _payload(self, timestamp=None, tipo='Entrada', **extra):
        datos = {
            'device_id': self.DEVICE_ID,
            'tipo_marcacion': tipo,
            'latitud': -16.4,
            'longitud': -71.5,
            'nombre_ubicacion': 'Campamento',
        }
        if timestamp is not None:
            datos['timestamp'] = timestamp.isoformat()
        datos.update(extra)
        return datos

    def _marcar(self, **kwargs):
        return self.client.post(self.url, self._payload(**kwargs), format='json')


class MarcacionOfflineFechaRealTests(_MarcacionBaseTests):
    """La marca se valida y recalcula contra el día en que se MARCÓ, no contra
    el día en que el worker offline logró subirla.

    Antes todo colgaba de `timezone.localdate()`, así que una marca sincronizada
    con retraso se validaba contra el turno del día de subida: si ese día era
    libre o no tenía turno, respondía 403, registraba un fraude falso y el dato
    de planilla se perdía.
    """

    def test_marca_de_hace_3_dias_se_imputa_al_tareo_de_esa_fecha(self):
        fecha = timezone.localdate() - timedelta(days=3)
        tareo_real = TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=fecha, estado='O',
            hora_entrada=dt_time(8, 0), hora_salida=dt_time(17, 0),
        )
        tareo_hoy = TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=timezone.localdate(), estado='O',
        )

        respuesta = self._marcar(timestamp=self._instante(fecha, 8, 0))

        self.assertEqual(respuesta.status_code, 201)
        tareo_real.refresh_from_db()
        tareo_hoy.refresh_from_db()
        # El recálculo tocó el tareo del día de la marca...
        self.assertEqual(tareo_real.hora_entrada_real, dt_time(8, 0))
        # ...y dejó intacto el del día de sincronización.
        self.assertIsNone(tareo_hoy.hora_entrada_real)

    def test_marca_de_hace_14_meses_se_acepta_igual(self):
        """No hay caducidad por antigüedad: en faena se está meses sin señal."""
        fecha = timezone.localdate() - timedelta(days=425)

        respuesta = self._marcar(timestamp=self._instante(fecha, 7, 30))

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertTrue(
            TareoDiario.objects.filter(trabajador=self.trabajador, fecha=fecha).exists()
        )

    def test_dia_de_sincronizacion_es_dia_libre_ya_no_rechaza(self):
        """El caso que rompía la sincronización: subir el miércoles (libre) una
        marca hecha el lunes (laborable)."""
        fecha_marca = timezone.localdate() - timedelta(days=2)
        TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=fecha_marca, estado='O',
            hora_entrada=dt_time(8, 0),
        )
        TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=timezone.localdate(), estado='D',
        )

        respuesta = self._marcar(timestamp=self._instante(fecha_marca, 8, 0))

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(IntentoFraude.objects.count(), 0)

    def test_marca_atrasada_sin_tareo_lo_crea_y_no_registra_fraude(self):
        """Si RRHH nunca cargó ese turno la marca no se pierde: el tareo se crea
        al vuelo, igual que ya hace la importación biométrica."""
        fecha = timezone.localdate() - timedelta(days=240)

        respuesta = self._marcar(timestamp=self._instante(fecha, 6, 45))

        self.assertEqual(respuesta.status_code, 201)
        tareo = TareoDiario.objects.get(trabajador=self.trabajador, fecha=fecha)
        self.assertEqual(tareo.estado, 'O')
        self.assertEqual(Asistencia.objects.count(), 1)
        # Un desfase de sincronización no es fraude.
        self.assertEqual(IntentoFraude.objects.count(), 0)

    def test_marca_atrasada_en_dia_libre_real_se_acepta(self):
        """El motor de reglas ya admite marcas en día libre (ASISTIÓ +
        DIA_LIBRE, sin tardanza); rechazarlas aquí perdería planilla."""
        fecha = timezone.localdate() - timedelta(days=5)
        TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=fecha, estado='D',
        )

        respuesta = self._marcar(timestamp=self._instante(fecha, 9, 0))

        self.assertEqual(respuesta.status_code, 201)
        tareo = TareoDiario.objects.get(trabajador=self.trabajador, fecha=fecha)
        self.assertEqual(tareo.etiqueta_estado, 'DIA_LIBRE')
        self.assertEqual(tareo.resultado, 'A')
        self.assertEqual(IntentoFraude.objects.count(), 0)

    def test_tareo_sintetico_sin_horario_no_fabrica_tardanza(self):
        """El `estado` que adivinamos al crear el tareo debe ser inerte: sin
        horario programado el motor corta antes de evaluar tolerancia, así que
        no puede inventar una tardanza retroactiva."""
        ConfiguracionTolerancia.objects.create(
            sede=self.sede, tipo_horario='O', minutos_tolerancia=0,
        )
        fecha = timezone.localdate() - timedelta(days=30)

        respuesta = self._marcar(timestamp=self._instante(fecha, 11, 30))

        self.assertEqual(respuesta.status_code, 201)
        tareo = TareoDiario.objects.get(trabajador=self.trabajador, fecha=fecha)
        self.assertEqual(tareo.etiqueta_estado, 'SIN_HORARIO')
        self.assertEqual(tareo.resultado, 'A')
        self.assertEqual(float(tareo.horas_tardanza), 0.0)

    def test_timestamp_futuro_se_rechaza_sin_registrar_fraude(self):
        """Un reloj adelantado tras meses sin NTP no es prueba de manipulación."""
        futuro = timezone.now() + timedelta(days=2)

        respuesta = self._marcar(timestamp=futuro)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data['codigo'], 'MARCA_FUTURA')
        self.assertEqual(Asistencia.objects.count(), 0)
        self.assertEqual(IntentoFraude.objects.count(), 0)

    def test_marca_nocturna_se_imputa_al_dia_de_lima(self):
        """Regresión del bug ya corregido en este archivo: a las 20:00 de Lima
        el UTC ya es el día siguiente, y `.date()` sobre el datetime crudo
        imputaría la marca al día equivocado."""
        fecha = timezone.localdate() - timedelta(days=3)
        TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=fecha, estado='O',
        )

        respuesta = self._marcar(timestamp=self._instante(fecha, 20, 0), tipo='Salida')

        self.assertEqual(respuesta.status_code, 201)
        self.assertFalse(
            TareoDiario.objects.filter(
                trabajador=self.trabajador, fecha=fecha + timedelta(days=1)
            ).exists(),
            'La marca de las 20:00 de Lima se imputó al día siguiente (UTC).',
        )

    def test_marca_en_tiempo_real_en_dia_libre_sigue_siendo_fraude(self):
        """El control antifraude no se debilita para las marcas de hoy."""
        TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=timezone.localdate(), estado='D',
        )

        respuesta = self._marcar(timestamp=timezone.now())

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(IntentoFraude.objects.count(), 1)
        self.assertEqual(
            IntentoFraude.objects.first().motivo_detectado,
            'Intento de marcacion en dia libre',
        )

    def test_marca_en_tiempo_real_sin_turno_sigue_siendo_fraude(self):
        respuesta = self._marcar(timestamp=timezone.now())

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(IntentoFraude.objects.count(), 1)
        self.assertEqual(
            IntentoFraude.objects.first().motivo_detectado,
            'Intento de marcacion sin turno programado',
        )

    def test_sin_timestamp_cae_a_hoy_y_conserva_el_candado(self):
        """Sin timestamp en el payload el comportamiento previo se mantiene."""
        respuesta = self.client.post(
            self.url,
            {'device_id': self.DEVICE_ID, 'tipo_marcacion': 'Entrada'},
            format='json',
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(IntentoFraude.objects.count(), 1)


class MarcacionIdempotenciaTests(_MarcacionBaseTests):
    """Reenviar la misma marca no duplica planilla.

    Al volver de faena se suben cientos de marcas sobre una conexión mala: las
    respuestas perdidas a mitad de camino son la norma, y sin idempotencia cada
    reintento del worker creaba un registro nuevo.
    """

    def setUp(self):
        super().setUp()
        self.fecha = timezone.localdate() - timedelta(days=10)
        self.uuid = str(uuid.uuid4())

    def test_reenviar_el_mismo_client_uuid_no_duplica(self):
        primera = self._marcar(
            timestamp=self._instante(self.fecha, 8, 0), client_uuid=self.uuid
        )
        segunda = self._marcar(
            timestamp=self._instante(self.fecha, 8, 0), client_uuid=self.uuid
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertEqual(segunda.data['id'], primera.data['id'])

    def test_client_uuid_en_camelcase_tambien_deduplica(self):
        primera = self._marcar(
            timestamp=self._instante(self.fecha, 8, 0), clientUuid=self.uuid
        )
        segunda = self._marcar(
            timestamp=self._instante(self.fecha, 8, 0), clientUuid=self.uuid
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertEqual(str(Asistencia.objects.get().client_uuid), self.uuid)

    def test_marca_sin_client_uuid_sigue_funcionando(self):
        """Biométrico y manual no traen client_uuid; no deben romperse."""
        respuesta = self._marcar(timestamp=self._instante(self.fecha, 8, 0))

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertIsNone(Asistencia.objects.get().client_uuid)

    def test_varias_marcas_sin_client_uuid_conviven(self):
        """El unique es nullable: varios NULL no chocan entre sí."""
        self._marcar(timestamp=self._instante(self.fecha, 8, 0))
        self._marcar(timestamp=self._instante(self.fecha, 17, 0), tipo='Salida')

        self.assertEqual(Asistencia.objects.count(), 2)

    def test_el_reintento_no_vuelve_a_recalcular_el_tareo(self):
        """El corte por idempotencia va antes de toda la lógica: un reintento no
        debe poder alterar el tareo ni generar un 403 sobre una marca ya buena."""
        self._marcar(timestamp=self._instante(self.fecha, 8, 0), client_uuid=self.uuid)
        tareo = TareoDiario.objects.get(trabajador=self.trabajador, fecha=self.fecha)
        entrada_original = tareo.hora_entrada_real

        # Entre el primer envío y el reintento, RRHH marca el día como libre.
        tareo.estado = 'D'
        tareo.save()

        segunda = self._marcar(
            timestamp=self._instante(self.fecha, 8, 0), client_uuid=self.uuid
        )

        self.assertEqual(segunda.status_code, 200)
        tareo.refresh_from_db()
        self.assertEqual(tareo.hora_entrada_real, entrada_original)
        self.assertEqual(Asistencia.objects.count(), 1)


class MarcacionCargaFaenaTests(_MarcacionBaseTests):
    """Volver de faena no es subir una marca: son cientos de golpe."""

    def test_500_marcas_de_meses_distintos_no_degradan_el_recalculo(self):
        hoy = timezone.localdate()
        fechas = [hoy - timedelta(days=3 * (i + 1)) for i in range(500)]

        with CaptureQueriesContext(connection) as primera:
            self._marcar(timestamp=self._instante(fechas[0], 8, 0),
                         client_uuid=str(uuid.uuid4()))

        for fecha in fechas[1:-1]:
            respuesta = self._marcar(timestamp=self._instante(fecha, 8, 0),
                                     client_uuid=str(uuid.uuid4()))
            self.assertEqual(respuesta.status_code, 201)

        with CaptureQueriesContext(connection) as ultima:
            self._marcar(timestamp=self._instante(fechas[-1], 8, 0),
                         client_uuid=str(uuid.uuid4()))

        self.assertEqual(Asistencia.objects.count(), 500)
        self.assertEqual(TareoDiario.objects.count(), 500)

        # El costo por marca no debe crecer con el volumen ya acumulado: si
        # alguien reintroduce un N+1 o una consulta que barre toda la tabla,
        # este assert lo detecta antes que producción.
        self.assertLessEqual(
            len(ultima.captured_queries), len(primera.captured_queries),
            'El costo por marca crece con el volumen acumulado.',
        )
