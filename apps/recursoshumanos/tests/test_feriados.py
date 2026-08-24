# recursoshumanos/tests/test_feriados.py
"""Marcación en día feriado, con scope por ámbito (HU-04 / CAV-13).

Cubre CAV-62 (la consulta de feriados entra al flujo de marcación) y CAV-63
(la marca se etiqueta como FERIADO y se propaga al tareo), validando los tres
ámbitos que pide CAV-65: nacional, regional (por sede) y de empresa.

El feriado se ejerce end-to-end: al crear una Asistencia se dispara el
post_save -> recalcular_asistencia_diaria, que consulta el feriado con el scope
del trabajador y persiste resultado / etiqueta_estado / detalle_marca.
"""
from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from administracion.models import Feriado
from administracion.services.feriados import es_feriado, obtener_feriado
from recursoshumanos.models import (
    Asistencia,
    Empresa,
    Sede,
    TareoDiario,
    Trabajador,
)
from recursoshumanos.motor_reglas import EstadoMarca

FECHA = date(2026, 8, 13)


class FeriadoMarcacionTests(TestCase):
    dni_seq = 91000000

    def setUp(self):
        self.sede_lima = Sede.objects.create(nombre='Lima')
        self.sede_cusco = Sede.objects.create(nombre='Cusco')
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')

    # --- helpers ---

    def _trabajador(self, sede=None, empresa=None):
        FeriadoMarcacionTests.dni_seq += 1
        dni = str(FeriadoMarcacionTests.dni_seq)
        user = User.objects.create_user(username=f'user{dni}', password='clave12345')
        return Trabajador.objects.create(
            user=user, sede=sede, empresa=empresa, dni=dni,
            apellido_paterno='Perez', apellido_materno='Gomez', nombres='Juan',
        )

    def _tareo(self, trabajador):
        return TareoDiario.objects.create(
            trabajador=trabajador, fecha=FECHA, estado='O', resultado='F',
            hora_entrada=time(8, 30), hora_salida=time(18, 0),
        )

    def _marcar(self, trabajador, hora, tipo):
        ts = timezone.make_aware(datetime.combine(FECHA, hora))
        return Asistencia.objects.create(
            usuario=trabajador.user, timestamp=ts, tipo_marcacion=tipo,
        )

    def _marca_tardia(self, trabajador):
        # 10:00 con horario 8:30 y tolerancia 15: sin feriado sería TARDANZA.
        self._marcar(trabajador, time(10, 0), 'Entrada')
        self._marcar(trabajador, time(18, 0), 'Salida')

    # --- CAV-65: feriado nacional ---

    def test_feriado_nacional_aplica_a_cualquier_trabajador(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Año Nuevo',
            tipo=Feriado.Tipo.NACIONAL, ambito=Feriado.Ambito.NACIONAL,
        )
        trabajador = self._trabajador(sede=self.sede_lima, empresa=self.empresa_a)
        tareo = self._tareo(trabajador)
        self._marca_tardia(trabajador)

        tareo.refresh_from_db()
        self.assertEqual(tareo.resultado, 'A')
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.FERIADO)
        self.assertEqual(float(tareo.horas_tardanza), 0.0)
        self.assertIn('Año Nuevo', tareo.detalle_marca)

    # --- CAV-65: feriado regional (por sede) ---

    def test_feriado_regional_solo_afecta_a_su_sede(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Inti Raymi', ambito=Feriado.Ambito.REGIONAL,
            sede=self.sede_cusco,
        )
        de_cusco = self._trabajador(sede=self.sede_cusco)
        tareo_cusco = self._tareo(de_cusco)
        self._marca_tardia(de_cusco)

        tareo_cusco.refresh_from_db()
        self.assertEqual(tareo_cusco.etiqueta_estado, EstadoMarca.FERIADO)
        self.assertIn('Inti Raymi', tareo_cusco.detalle_marca)

    def test_feriado_regional_no_afecta_a_otra_sede(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Inti Raymi', ambito=Feriado.Ambito.REGIONAL,
            sede=self.sede_cusco,
        )
        de_lima = self._trabajador(sede=self.sede_lima)
        tareo_lima = self._tareo(de_lima)
        self._marca_tardia(de_lima)

        tareo_lima.refresh_from_db()
        # Para Lima ese día NO es feriado: la marca tardía se juzga normal.
        self.assertEqual(tareo_lima.etiqueta_estado, EstadoMarca.TARDANZA)

    # --- CAV-65: feriado de empresa ---

    def test_feriado_empresa_solo_afecta_a_su_empresa(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Aniversario Empresa A',
            ambito=Feriado.Ambito.EMPRESA, empresa=self.empresa_a,
        )
        de_a = self._trabajador(empresa=self.empresa_a)
        tareo_a = self._tareo(de_a)
        self._marca_tardia(de_a)

        tareo_a.refresh_from_db()
        self.assertEqual(tareo_a.etiqueta_estado, EstadoMarca.FERIADO)
        self.assertIn('Aniversario Empresa A', tareo_a.detalle_marca)

    def test_feriado_empresa_no_afecta_a_otra_empresa(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Aniversario Empresa A',
            ambito=Feriado.Ambito.EMPRESA, empresa=self.empresa_a,
        )
        de_b = self._trabajador(empresa=self.empresa_b)
        tareo_b = self._tareo(de_b)
        self._marca_tardia(de_b)

        tareo_b.refresh_from_db()
        self.assertEqual(tareo_b.etiqueta_estado, EstadoMarca.TARDANZA)


class FeriadoScopeServicioTests(TestCase):
    """Prueba directa del servicio de consulta con scope (CAV-62)."""

    def setUp(self):
        self.sede_cusco = Sede.objects.create(nombre='Cusco')
        self.sede_lima = Sede.objects.create(nombre='Lima')
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')

    def test_nacional_aplica_a_todos(self):
        Feriado.objects.create(fecha=FECHA, nombre='Nacional')
        self.assertTrue(es_feriado(FECHA, sede=self.sede_lima, empresa=self.empresa_a))
        self.assertIsNotNone(obtener_feriado(FECHA, sede=self.sede_cusco))

    def test_regional_solo_su_sede(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Regional', ambito=Feriado.Ambito.REGIONAL,
            sede=self.sede_cusco,
        )
        self.assertTrue(es_feriado(FECHA, sede=self.sede_cusco))
        self.assertFalse(es_feriado(FECHA, sede=self.sede_lima))

    def test_empresa_solo_su_empresa(self):
        Feriado.objects.create(
            fecha=FECHA, nombre='Empresa', ambito=Feriado.Ambito.EMPRESA,
            empresa=self.empresa_a,
        )
        self.assertTrue(es_feriado(FECHA, empresa=self.empresa_a))
        self.assertFalse(es_feriado(FECHA, empresa=self.empresa_b))
