# recursoshumanos/tests/test_recalculo.py
"""Pruebas de integración del recálculo de asistencia (CAV-169).

Verifican que `recalcular_asistencia_diaria` (disparado por el post_save de
Asistencia) persista resultado / horas_tardanza / etiqueta_estado usando el
motor de reglas, incluyendo feriados y la tolerancia configurable por Sede y
horario.
"""
from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from administracion.models import Feriado
from recursoshumanos.models import (
    Asistencia,
    ConfiguracionTolerancia,
    Sede,
    TareoDiario,
    Trabajador,
)
from recursoshumanos.motor_reglas import EstadoMarca

FECHA = date(2026, 8, 13)


class RecalculoAsistenciaTests(TestCase):
    dni_seq = 90000000

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Lima')
        # Tolerancia de 15 min para el turno de Oficina en esta sede.
        ConfiguracionTolerancia.objects.create(
            sede=self.sede, tipo_horario='O', minutos_tolerancia=15
        )

    def _trabajador(self):
        RecalculoAsistenciaTests.dni_seq += 1
        dni = str(RecalculoAsistenciaTests.dni_seq)
        user = User.objects.create_user(username=f'user{dni}', password='clave12345')
        return Trabajador.objects.create(
            user=user, sede=self.sede, dni=dni,
            apellido_paterno='Perez', apellido_materno='Gomez', nombres='Juan',
        )

    def _tareo(self, trabajador, estado='O', fecha=FECHA,
               hora_entrada=time(8, 30), hora_salida=time(18, 0), resultado='F'):
        return TareoDiario.objects.create(
            trabajador=trabajador, fecha=fecha, estado=estado, resultado=resultado,
            hora_entrada=hora_entrada, hora_salida=hora_salida,
        )

    def _marcar(self, trabajador, hora, tipo, fecha=FECHA):
        """Crea una Asistencia en hora LOCAL; dispara el recálculo vía signal."""
        ts = timezone.make_aware(datetime.combine(fecha, hora))
        return Asistencia.objects.create(
            usuario=trabajador.user, timestamp=ts, tipo_marcacion=tipo,
        )

    # --- Casos ---

    def test_marca_a_tiempo_queda_normal(self):
        t = self._trabajador()
        tareo = self._tareo(t)
        self._marcar(t, time(8, 30), 'Entrada')
        self._marcar(t, time(18, 0), 'Salida')

        tareo.refresh_from_db()
        self.assertEqual(tareo.resultado, 'A')
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.NORMAL)
        self.assertEqual(float(tareo.horas_tardanza), 0.0)

    def test_marca_tardia_registra_tardanza(self):
        t = self._trabajador()
        tareo = self._tareo(t)
        self._marcar(t, time(9, 0), 'Entrada')   # 30 min - 15 tol = 15 min
        self._marcar(t, time(18, 0), 'Salida')

        tareo.refresh_from_db()
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.TARDANZA)
        self.assertEqual(float(tareo.horas_tardanza), 0.25)

    def test_feriado_no_genera_tardanza(self):
        Feriado.objects.create(fecha=FECHA, nombre='Prueba Feriado')
        t = self._trabajador()
        tareo = self._tareo(t)
        self._marcar(t, time(10, 0), 'Entrada')  # tardísimo, pero es feriado
        self._marcar(t, time(18, 0), 'Salida')

        tareo.refresh_from_db()
        self.assertEqual(tareo.resultado, 'A')
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.FERIADO)
        self.assertEqual(float(tareo.horas_tardanza), 0.0)

    def test_justificado_no_se_pisa_por_marca(self):
        t = self._trabajador()
        tareo = self._tareo(t, resultado='J')
        self._marcar(t, time(9, 30), 'Entrada')

        tareo.refresh_from_db()
        self.assertEqual(tareo.resultado, 'J')
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.JUSTIFICADO)

    def test_tolerancia_por_sede_horario_cambia_el_veredicto(self):
        # Con la config amplia (45 min) la misma marca 9:00 deja de ser tardanza.
        config = ConfiguracionTolerancia.objects.get(sede=self.sede, tipo_horario='O')
        config.minutos_tolerancia = 45
        config.save(update_fields=['minutos_tolerancia'])

        t = self._trabajador()
        tareo = self._tareo(t)
        self._marcar(t, time(9, 0), 'Entrada')
        self._marcar(t, time(18, 0), 'Salida')

        tareo.refresh_from_db()
        self.assertEqual(tareo.etiqueta_estado, EstadoMarca.NORMAL)
        self.assertEqual(float(tareo.horas_tardanza), 0.0)
