from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Feriado
from .services.feriados import es_feriado, obtener_feriados_rango


class FeriadoModelTests(TestCase):
    def test_creacion_feriado(self):
        feriado = Feriado.objects.create(
            fecha=date(2026, 1, 1),
            nombre='Año Nuevo',
            tipo=Feriado.Tipo.NACIONAL,
            ambito=Feriado.Ambito.NACIONAL,
        )
        self.assertEqual(str(feriado), 'Año Nuevo (01/01/2026)')
        self.assertIsNotNone(feriado.creado_en)
        self.assertIsNotNone(feriado.actualizado_en)

    def test_defaults_tipo_y_ambito(self):
        feriado = Feriado.objects.create(fecha=date(2026, 5, 1), nombre='Día del Trabajo')
        self.assertEqual(feriado.tipo, Feriado.Tipo.NACIONAL)
        self.assertEqual(feriado.ambito, Feriado.Ambito.NACIONAL)

    def test_fecha_unica(self):
        Feriado.objects.create(fecha=date(2026, 5, 1), nombre='Día del Trabajo')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Feriado.objects.create(fecha=date(2026, 5, 1), nombre='Duplicado')

    def test_ordering_por_fecha_descendente(self):
        Feriado.objects.create(fecha=date(2026, 1, 1), nombre='Año Nuevo')
        Feriado.objects.create(fecha=date(2026, 12, 25), nombre='Navidad')
        fechas = list(Feriado.objects.values_list('fecha', flat=True))
        self.assertEqual(fechas, [date(2026, 12, 25), date(2026, 1, 1)])


class FeriadosServiceTests(TestCase):
    def setUp(self):
        Feriado.objects.create(fecha=date(2026, 1, 1), nombre='Año Nuevo')
        Feriado.objects.create(fecha=date(2026, 5, 1), nombre='Día del Trabajo')
        Feriado.objects.create(fecha=date(2026, 7, 28), nombre='Fiestas Patrias')

    def test_es_feriado_true(self):
        self.assertTrue(es_feriado(date(2026, 1, 1)))

    def test_es_feriado_false(self):
        self.assertFalse(es_feriado(date(2026, 1, 2)))

    def test_obtener_feriados_rango(self):
        resultado = obtener_feriados_rango(date(2026, 1, 1), date(2026, 6, 1))
        self.assertEqual(resultado, {date(2026, 1, 1), date(2026, 5, 1)})

    def test_obtener_feriados_rango_vacio(self):
        resultado = obtener_feriados_rango(date(2020, 1, 1), date(2020, 12, 31))
        self.assertEqual(resultado, set())

    def test_obtener_feriados_rango_limites_inclusivos(self):
        resultado = obtener_feriados_rango(date(2026, 1, 1), date(2026, 1, 1))
        self.assertEqual(resultado, {date(2026, 1, 1)})
