# recursoshumanos/tests/test_motor_reglas.py
"""Pruebas unitarias PURAS del motor de reglas (CAV-169).

No tocan la base de datos: usan SimpleTestCase y construyen el
ContextoMarcacion a mano. Cubren el orden de prioridad y los casos límite
documentados en docs/motor_reglas_marcacion.md.
"""
from datetime import date, time

from django.test import SimpleTestCase

from recursoshumanos.motor_reglas import (
    ContextoMarcacion,
    EstadoMarca,
    evaluar_marcacion,
)


def _contexto(**overrides):
    """ContextoMarcacion base (día normal de oficina con marca a tiempo)."""
    datos = dict(
        fecha=date(2026, 8, 13),
        estado_jornada='O',
        resultado_previo='F',
        hora_entrada_programada=time(8, 30),
        hora_salida_programada=time(18, 0),
        hora_entrada_real=time(8, 30),
        hora_salida_real=time(18, 0),
        minutos_tolerancia=15,
        es_feriado=False,
        tiene_marcas=True,
    )
    datos.update(overrides)
    return ContextoMarcacion(**datos)


class MotorNormalYTardanzaTests(SimpleTestCase):
    def test_marca_dentro_de_horario_es_normal(self):
        r = evaluar_marcacion(_contexto())
        self.assertEqual(r.resultado, 'A')
        self.assertEqual(r.etiqueta, EstadoMarca.NORMAL)
        self.assertEqual(r.horas_tardanza, 0.0)

    def test_dentro_de_tolerancia_no_es_tardanza(self):
        # Entra 8:44, tolerancia 15 -> 14 min, dentro de la gracia.
        r = evaluar_marcacion(_contexto(hora_entrada_real=time(8, 44)))
        self.assertEqual(r.etiqueta, EstadoMarca.NORMAL)
        self.assertEqual(r.minutos_tardanza, 0)

    def test_limite_exacto_de_tolerancia_no_es_tardanza(self):
        # Entra 8:45 = 8:30 + 15 exactos -> umbral estricto, NO es tardanza.
        r = evaluar_marcacion(_contexto(hora_entrada_real=time(8, 45)))
        self.assertEqual(r.etiqueta, EstadoMarca.NORMAL)
        self.assertEqual(r.minutos_tardanza, 0)

    def test_pasada_la_tolerancia_es_tardanza(self):
        # Entra 9:00 -> 30 min - 15 tolerancia = 15 min de tardanza.
        r = evaluar_marcacion(_contexto(hora_entrada_real=time(9, 0)))
        self.assertEqual(r.resultado, 'A')
        self.assertEqual(r.etiqueta, EstadoMarca.TARDANZA)
        self.assertEqual(r.minutos_tardanza, 15)
        self.assertEqual(r.horas_tardanza, 0.25)

    def test_tolerancia_por_configuracion_cambia_el_veredicto(self):
        # Misma marca (9:00), distinta tolerancia -> distinto resultado.
        tarde = evaluar_marcacion(_contexto(hora_entrada_real=time(9, 0), minutos_tolerancia=15))
        a_tiempo = evaluar_marcacion(_contexto(hora_entrada_real=time(9, 0), minutos_tolerancia=45))
        self.assertEqual(tarde.etiqueta, EstadoMarca.TARDANZA)
        self.assertEqual(a_tiempo.etiqueta, EstadoMarca.NORMAL)


class MotorFueraDeHorarioTests(SimpleTestCase):
    def test_salida_posterior_es_fuera_de_horario(self):
        r = evaluar_marcacion(_contexto(hora_salida_real=time(20, 0)))
        self.assertEqual(r.etiqueta, EstadoMarca.FUERA_DE_HORARIO)
        self.assertIn(EstadoMarca.FUERA_DE_HORARIO, r.etiquetas)

    def test_entrada_anticipada_es_fuera_de_horario(self):
        r = evaluar_marcacion(_contexto(hora_entrada_real=time(7, 0)))
        self.assertIn(EstadoMarca.FUERA_DE_HORARIO, r.etiquetas)

    def test_tardanza_y_fuera_de_horario_conviven(self):
        # Entra tarde (9:00) y sale tarde (20:00): ambas etiquetas.
        r = evaluar_marcacion(_contexto(hora_entrada_real=time(9, 0), hora_salida_real=time(20, 0)))
        self.assertEqual(r.etiqueta, EstadoMarca.TARDANZA)  # principal
        self.assertIn(EstadoMarca.TARDANZA, r.etiquetas)
        self.assertIn(EstadoMarca.FUERA_DE_HORARIO, r.etiquetas)

    def test_sin_horario_programado(self):
        r = evaluar_marcacion(_contexto(hora_entrada_programada=None))
        self.assertEqual(r.resultado, 'A')
        self.assertEqual(r.etiqueta, EstadoMarca.SIN_HORARIO)
        self.assertEqual(r.minutos_tardanza, 0)


class MotorFeriadoTests(SimpleTestCase):
    def test_feriado_con_marca_no_calcula_tardanza(self):
        # Entra tardísimo, pero es feriado -> FERIADO, sin tardanza.
        r = evaluar_marcacion(_contexto(es_feriado=True, hora_entrada_real=time(11, 0)))
        self.assertEqual(r.resultado, 'A')
        self.assertEqual(r.etiqueta, EstadoMarca.FERIADO)
        self.assertEqual(r.minutos_tardanza, 0)

    def test_feriado_sin_marca_no_penaliza(self):
        r = evaluar_marcacion(_contexto(es_feriado=True, tiene_marcas=False, resultado_previo='F'))
        self.assertEqual(r.etiqueta, EstadoMarca.FERIADO)
        # No se fuerza a Falta ni a Asistió.
        self.assertEqual(r.resultado, 'F')


class MotorCasosBaseTests(SimpleTestCase):
    def test_sin_marcas_dia_normal_es_falta(self):
        r = evaluar_marcacion(_contexto(tiene_marcas=False))
        self.assertEqual(r.resultado, 'F')
        self.assertEqual(r.etiqueta, EstadoMarca.FALTA)

    def test_justificado_manda_sobre_las_marcas(self):
        r = evaluar_marcacion(_contexto(resultado_previo='J', hora_entrada_real=time(11, 0)))
        self.assertEqual(r.resultado, 'J')
        self.assertEqual(r.etiqueta, EstadoMarca.JUSTIFICADO)
        self.assertEqual(r.minutos_tardanza, 0)

    def test_dia_libre_con_marca(self):
        r = evaluar_marcacion(_contexto(estado_jornada='D', hora_entrada_real=time(9, 0)))
        self.assertEqual(r.etiqueta, EstadoMarca.DIA_LIBRE)
        self.assertEqual(r.resultado, 'A')
        self.assertEqual(r.minutos_tardanza, 0)
