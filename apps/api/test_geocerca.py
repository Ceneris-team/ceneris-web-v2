"""Geocerca validada en el servidor, con politica de OBSERVAR (no rechazar).

Estos tests nacieron como una auditoria que demostraba lo contrario: que el
backend aceptaba con 201 una marca hecha desde Madrid, porque la geocerca solo
se evaluaba en el celular. Ahora fijan el comportamiento corregido.

Lo que se protege aca es el par completo:
  - la marca SIEMPRE se guarda (rechazarla perderia planilla real cuando el
    GPS deriva, que en faena es lo normal), y
  - la marca fuera de zona queda ETIQUETADA para que RRHH decida.

Si alguien cambia la politica a "rechazar", estos tests deben fallar: esa es su
razon de existir.
"""
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from recursoshumanos.models import Asistencia, IntentoFraude, TareoDiario, Trabajador, Ubicacion
from recursoshumanos.servicios_geocerca import distancia_metros

# Puerta de la zona del piloto y un punto a ~9 550 km de ahi.
LIMA = (-12.116985, -77.009743)
MADRID = (40.416775, -3.703790)


class GeocercaBase(TestCase):
    dni = '30000099'
    username = 'geo_user'
    radio = 500

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username=self.username, password='x')
        self.trabajador = Trabajador.objects.create(
            dni=self.dni, apellido_paterno='Geo', apellido_materno='Test',
            nombres='Auditoria', user=self.user,
        )
        self.ubicacion = Ubicacion.objects.create(
            nombre='CENERIS MIRAFLORES',
            latitud=LIMA[0], longitud=LIMA[1], radio=self.radio,
        )
        self.trabajador.ubicaciones_permitidas.add(self.ubicacion)
        self.client = APIClient()
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def crear_tareo(self, fecha=None):
        """Turno abierto, para aislar la geocerca de la validacion de turno."""
        return TareoDiario.objects.create(
            trabajador=self.trabajador, fecha=fecha or timezone.localdate(),
            estado='O', resultado='F',
        )

    def marcar(self, lat=None, lon=None, nombre='CENERIS MIRAFLORES', timestamp=None):
        payload = {
            'tipo_marcacion': 'Entrada',
            'device_id': 'device-geocerca-test',
            'nombre_ubicacion': nombre,
            'timestamp': (timestamp or timezone.now()).isoformat(),
            'client_uuid': str(uuid.uuid4()),
        }
        if lat is not None:
            payload['latitud'] = lat
            payload['longitud'] = lon
        return self.client.post(reverse('registrar-asistencia'), payload, format='json')


class GeocercaValidadaEnServidorTests(GeocercaBase):
    def setUp(self):
        super().setUp()
        self.crear_tareo()

    def test_marca_dentro_de_la_zona_queda_limpia(self):
        """El caso feliz: no se observa nada y se registra la zona que valido."""
        r = self.marcar(*LIMA)

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_DENTRO)
        self.assertEqual(marca.ubicacion_validada, self.ubicacion)
        self.assertLess(marca.distancia_geocerca_m, 10)
        self.assertFalse(marca.geocerca_observada)
        self.assertNotIn('advertencia', r.data)

    def test_marca_en_el_borde_de_la_zona_sigue_siendo_valida(self):
        """~445 m del centro, dentro de un radio de 500 m: no se observa.

        Fija el limite por el lado bueno, para que endurecer la geocerca en el
        futuro no empiece a observar a gente que si esta en planta.
        """
        # ~0.004 grados de latitud son ~445 m.
        r = self.marcar(LIMA[0] + 0.004, LIMA[1])

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_DENTRO)
        self.assertFalse(marca.geocerca_observada)

    def test_marca_a_miles_de_kilometros_se_guarda_pero_queda_observada(self):
        """El agujero original, ahora acotado.

        La marca NO se rechaza (esa es la politica), pero deja de ser
        indistinguible de una marca legitima.
        """
        r = self.marcar(*MADRID, nombre='Offline')

        # 1. Se guarda: no se pierde planilla.
        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.latitud, MADRID[0])

        # 2. Pero queda observada, con el dato que RRHH necesita para juzgar.
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_FUERA)
        self.assertTrue(marca.geocerca_observada)
        self.assertEqual(marca.ubicacion_validada, self.ubicacion)
        self.assertGreater(marca.distancia_geocerca_m, 9_000_000)

        # 3. Y al trabajador se le avisa en el momento, no en planilla.
        self.assertEqual(r.data['advertencia']['tipo'], 'FUERA_DE_ZONA')

    def test_fuera_de_zona_no_registra_intento_de_fraude(self):
        """Observar no es acusar.

        `IntentoFraude` significa "intento bloqueado". Llenarlo de deriva de
        GPS lo volveria ilegible justo para los casos en que sirve.
        """
        self.marcar(*MADRID)

        self.assertEqual(IntentoFraude.objects.count(), 0)

    def test_el_nombre_de_zona_que_manda_el_celular_no_decide_nada(self):
        """La etiqueta del cliente es decorativa; manda la coordenada.

        Antes bastaba con mandar un `nombre_ubicacion` cualquiera para que la
        marca luciera normal en los reportes.
        """
        r = self.marcar(*MADRID, nombre='CENERIS MIRAFLORES')

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.nombre_ubicacion, 'CENERIS MIRAFLORES')
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_FUERA)

    def test_el_movil_no_puede_declararse_dentro_de_zona(self):
        """El estado lo escribe el servidor, no el payload.

        Si el campo fuera escribible, la validacion volveria a depender del
        cliente y esto no habria arreglado nada.
        """
        r = self.client.post(reverse('registrar-asistencia'), {
            'tipo_marcacion': 'Entrada',
            'latitud': MADRID[0], 'longitud': MADRID[1],
            'device_id': 'device-geocerca-test',
            'timestamp': timezone.now().isoformat(),
            'client_uuid': str(uuid.uuid4()),
            'estado_geocerca': Asistencia.GEOCERCA_DENTRO,
            'distancia_geocerca_m': 0,
        }, format='json')

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_FUERA)
        self.assertGreater(marca.distancia_geocerca_m, 9_000_000)

    def test_marca_sin_coordenadas_se_guarda_y_se_observa(self):
        """Sin GPS no hay validacion posible, pero tampoco silencio.

        Antes esto pasaba como marca normal. Ahora se distingue de FUERA
        porque no es lo mismo: no hay evidencia en ninguna direccion.
        """
        r = self.marcar()

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_SIN_COORDENADAS)
        self.assertTrue(marca.geocerca_observada)
        self.assertIsNone(marca.distancia_geocerca_m)


class GeocercaSinZonasAsignadasTests(GeocercaBase):
    dni = '30000097'
    username = 'geo_sin_zonas'

    def setUp(self):
        super().setUp()
        # RRHH nunca le cargo zonas a este trabajador.
        self.trabajador.ubicaciones_permitidas.clear()
        self.crear_tareo()

    def test_sin_zonas_asignadas_no_se_marca_como_fuera_de_zona(self):
        """Un vacio de configuracion no es una marca sospechosa.

        Si se reportara como FUERA, RRHH veria un pico de "fraude" que en
        realidad es trabajo administrativo pendiente.
        """
        r = self.marcar(*MADRID)

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_SIN_ZONAS)
        self.assertIsNone(marca.ubicacion_validada)


class GeocercaEnSincronizacionOfflineTests(GeocercaBase):
    dni = '30000098'
    username = 'geo_offline'

    def test_marca_atrasada_fuera_de_zona_se_guarda_y_se_observa(self):
        """La cola offline no puede ser una via de escape a la geocerca.

        Una marca de hace 3 dias entra igual (ese fix existe para no perder
        planilla de faena sin senal), pero se evalua con el mismo criterio.
        """
        hace_tres_dias = timezone.now() - timedelta(days=3)
        r = self.marcar(*MADRID, nombre='Offline', timestamp=hace_tres_dias)

        self.assertIn(r.status_code, (200, 201), r.data)
        marca = Asistencia.objects.get()
        self.assertEqual(marca.estado_geocerca, Asistencia.GEOCERCA_FUERA)
        self.assertTrue(marca.geocerca_observada)
        # El tareo se sigue creando al vuelo: observar no bloquea el flujo.
        self.assertTrue(
            TareoDiario.objects.filter(trabajador=self.trabajador).exists()
        )


class DistanciaHaversineTests(TestCase):
    """El calculo puro, aislado de la vista."""

    def test_distancia_lima_madrid(self):
        d = distancia_metros(LIMA[0], LIMA[1], MADRID[0], MADRID[1])
        # ~9 550 km segun cualquier calculadora de gran circulo.
        self.assertAlmostEqual(d / 1000, 9550, delta=100)

    def test_distancia_a_si_mismo_es_cero(self):
        self.assertAlmostEqual(distancia_metros(LIMA[0], LIMA[1], LIMA[0], LIMA[1]), 0, places=6)
