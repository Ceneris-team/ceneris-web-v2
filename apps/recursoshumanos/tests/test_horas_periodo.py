"""Pruebas del acumulado de horas por período."""
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from recursoshumanos.models import TareoDiario, Trabajador
from recursoshumanos.servicios_horas import (
    resumen_horas_por_periodo,
    totales_generales,
)


def crear_trabajador(dni, apellido='Perez'):
    return Trabajador.objects.create(
        dni=dni,
        apellido_paterno=apellido,
        apellido_materno='Lopez',
        nombres='Juan',
    )


def crear_tareo(trabajador, fecha, horas, estado='O', entrada=time(8, 30), salida=time(18, 0)):
    return TareoDiario.objects.create(
        trabajador=trabajador,
        fecha=fecha,
        estado=estado,
        resultado='A',
        hora_entrada=entrada,
        hora_salida=salida,
        hora_entrada_real=entrada,
        hora_salida_real=salida,
        horas_trabajadas_validas=Decimal(str(horas)),
    )


class ResumenHorasPorPeriodoTests(TestCase):

    def setUp(self):
        # Todo el período va en el pasado: el servicio recorta a hoy, y con
        # fechas futuras las horas no se sumarían.
        self.hoy = timezone.localdate()
        self.inicio = self.hoy - timedelta(days=5)
        self.fin = self.hoy - timedelta(days=1)

    def test_suma_las_horas_validas_del_rango(self):
        trabajador = crear_trabajador('10000001')
        crear_tareo(trabajador, self.inicio, 8)
        crear_tareo(trabajador, self.inicio + timedelta(days=1), 7.5)

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(len(resumenes), 1)
        self.assertEqual(resumenes[0].total_horas, Decimal('15.50'))

    def test_ignora_dias_fuera_del_rango(self):
        trabajador = crear_trabajador('10000002')
        crear_tareo(trabajador, self.inicio, 8)
        crear_tareo(trabajador, self.inicio - timedelta(days=1), 8)  # anterior al rango

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes[0].total_horas, Decimal('8.00'))

    def test_promedio_diario_sobre_dias_esperados(self):
        trabajador = crear_trabajador('10000003')
        crear_tareo(trabajador, self.inicio, 8)
        crear_tareo(trabajador, self.inicio + timedelta(days=1), 4)

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes[0].total_horas, Decimal('12.00'))
        self.assertEqual(resumenes[0].dias_esperados, 2)
        self.assertEqual(resumenes[0].promedio_diario, Decimal('6.00'))

    def test_promedio_diario_sin_dias_esperados_no_divide_por_cero(self):
        trabajador = crear_trabajador('10000004')
        TareoDiario.objects.create(
            trabajador=trabajador, fecha=self.inicio, estado='D', resultado='A',
        )

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes[0].dias_esperados, 0)
        self.assertEqual(resumenes[0].promedio_diario, Decimal('0.00'))

    def test_los_dias_futuros_no_se_cuentan(self):
        """Los tareos programados a futuro existen con 0 horas; incluirlos
        ensuciaría el conteo de días con jornadas que aún no ocurrieron."""
        trabajador = crear_trabajador('10000005')
        crear_tareo(trabajador, self.inicio, 8)
        crear_tareo(trabajador, self.hoy + timedelta(days=3), 0)

        resumenes = resumen_horas_por_periodo(self.inicio, self.hoy + timedelta(days=5))

        self.assertEqual(resumenes[0].total_horas, Decimal('8.00'))
        self.assertEqual(resumenes[0].dias_esperados, 1)
        self.assertEqual(resumenes[0].dias_sin_marca, 0)

    def test_dia_libre_no_cuenta_como_dia_esperado(self):
        trabajador = crear_trabajador('10000006')
        crear_tareo(trabajador, self.inicio, 8)
        TareoDiario.objects.create(
            trabajador=trabajador, fecha=self.inicio + timedelta(days=1),
            estado='D', resultado='A',
        )

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes[0].dias_esperados, 1)
        self.assertEqual(resumenes[0].dias_sin_marca, 0)

    def test_marca_dias_con_entrada_pero_sin_salida(self):
        """Ese día suma 0 h porque no hay par Entrada→Salida; RRHH tiene que
        verlo porque el total queda por debajo de lo real."""
        trabajador = crear_trabajador('10000007')
        TareoDiario.objects.create(
            trabajador=trabajador, fecha=self.inicio, estado='O', resultado='A',
            hora_entrada=time(8, 30), hora_salida=time(18, 0),
            hora_entrada_real=time(8, 25), hora_salida_real=None,
            horas_trabajadas_validas=Decimal('0'),
        )

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes[0].dias_incompletos, 1)
        self.assertTrue(resumenes[0].tiene_alerta)
        self.assertEqual(resumenes[0].total_horas, Decimal('0.00'))

    def test_filtra_por_trabajador(self):
        uno = crear_trabajador('10000008', 'Aaa')
        dos = crear_trabajador('10000009', 'Bbb')
        crear_tareo(uno, self.inicio, 8)
        crear_tareo(dos, self.inicio, 8)

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin, trabajador_id=dos.id)

        self.assertEqual(len(resumenes), 1)
        self.assertEqual(resumenes[0].trabajador.id, dos.id)

    def test_solo_con_alerta_deja_fuera_las_marcaciones_completas(self):
        completo = crear_trabajador('10000010', 'Aaa')
        incompleto = crear_trabajador('10000011', 'Bbb')
        crear_tareo(completo, self.inicio, 8)
        TareoDiario.objects.create(
            trabajador=incompleto, fecha=self.inicio, estado='O', resultado='A',
            hora_entrada=time(8, 30), hora_salida=time(18, 0),
            hora_entrada_real=time(8, 25), hora_salida_real=None,
            horas_trabajadas_validas=Decimal('0'),
        )

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin, solo_con_alerta=True)

        self.assertEqual([r.trabajador.id for r in resumenes], [incompleto.id])

    def test_rango_invertido_por_el_recorte_devuelve_vacio(self):
        """Un período que empieza después de hoy no tiene días evaluables."""
        trabajador = crear_trabajador('10000012')
        crear_tareo(trabajador, self.inicio, 8)

        resumenes = resumen_horas_por_periodo(
            self.hoy + timedelta(days=1), self.hoy + timedelta(days=5)
        )

        self.assertEqual(resumenes, [])

    def test_trabajador_sin_tareo_en_el_rango_no_aparece(self):
        crear_trabajador('10000013')

        resumenes = resumen_horas_por_periodo(self.inicio, self.fin)

        self.assertEqual(resumenes, [])

    def test_totales_generales(self):
        uno = crear_trabajador('10000014', 'Aaa')
        dos = crear_trabajador('10000015', 'Bbb')
        crear_tareo(uno, self.inicio, 8)
        crear_tareo(dos, self.inicio, 2)

        totales = totales_generales(resumen_horas_por_periodo(self.inicio, self.fin))

        self.assertEqual(totales['trabajadores'], 2)
        self.assertEqual(totales['total_horas'], Decimal('10.00'))
        self.assertEqual(totales['con_alerta'], 0)


class ReporteHorasPeriodoViewTests(TestCase):
    """Smoke test de la pantalla: que RRHH pueda fijar el período y ver el total."""

    def setUp(self):
        self.hoy = timezone.localdate()
        self.inicio = self.hoy - timedelta(days=5)
        self.fin = self.hoy - timedelta(days=1)

        self.usuario = User.objects.create_user('rrhh_test', password='x')
        grupo, _ = Group.objects.get_or_create(name='Recursos Humanos')
        self.usuario.groups.add(grupo)
        self.client.force_login(self.usuario)

        self.trabajador = crear_trabajador('20000001')
        crear_tareo(self.trabajador, self.inicio, 8)
        crear_tareo(self.trabajador, self.inicio + timedelta(days=1), 8)

    def url(self):
        return reverse('recursoshumanos:reporte_horas_periodo')

    def test_sin_filtros_muestra_el_formulario_vacio(self):
        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context['busqueda_realizada'])

    def test_con_periodo_muestra_las_horas_totales(self):
        respuesta = self.client.get(self.url(), {
            'inicio': self.inicio.isoformat(),
            'fin': self.fin.isoformat(),
        })

        self.assertEqual(respuesta.status_code, 200)
        resumenes = respuesta.context['resumenes']
        self.assertEqual(len(resumenes), 1)
        self.assertEqual(resumenes[0].total_horas, Decimal('16.00'))
        self.assertEqual(respuesta.context['totales']['total_horas'], Decimal('16.00'))
        self.assertContains(respuesta, 'Horas totales')

    def test_la_pantalla_ya_no_habla_de_minimo_ni_cumplimiento(self):
        respuesta = self.client.get(self.url(), {
            'inicio': self.inicio.isoformat(),
            'fin': self.fin.isoformat(),
        })

        self.assertNotContains(respuesta, 'CUMPLE')
        self.assertNotContains(respuesta, 'Mínimo')

    def test_rango_invertido_avisa_y_no_calcula(self):
        respuesta = self.client.get(self.url(), {
            'inicio': self.fin.isoformat(),
            'fin': self.inicio.isoformat(),
        })

        self.assertFalse(respuesta.context['busqueda_realizada'])
        mensajes = [str(m) for m in respuesta.context['messages']]
        self.assertTrue(any('posterior' in m for m in mensajes), mensajes)

    def test_detalle_por_trabajador_lista_los_dias(self):
        respuesta = self.client.get(
            reverse('recursoshumanos:detalle_horas_trabajador',
                    kwargs={'trabajador_id': self.trabajador.id}),
            {'inicio': self.inicio.isoformat(), 'fin': self.fin.isoformat()},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['dias']), 2)
        self.assertEqual(respuesta.context['total_horas'], Decimal('16.00'))

    def test_usuario_sin_grupo_no_entra(self):
        self.client.logout()
        self.client.force_login(User.objects.create_user('ajeno', password='x'))

        respuesta = self.client.get(self.url())

        self.assertNotEqual(respuesta.status_code, 200)
