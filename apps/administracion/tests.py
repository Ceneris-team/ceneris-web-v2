import json
from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import FeriadoForm
from .models import Feriado
from .services.feriados import es_feriado, obtener_feriados_rango

MSG_DUPLICADO = "Ya existe un feriado registrado para la fecha seleccionada"


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


class FeriadoFormTests(TestCase):
    """CAV-53 / CAV-54: formulario de registro y validación de duplicados."""

    def _datos(self, **overrides):
        datos = {
            'fecha': '2026-01-01',
            'nombre': 'Año Nuevo',
            'tipo': Feriado.Tipo.NACIONAL,
            'ambito': Feriado.Ambito.NACIONAL,
        }
        datos.update(overrides)
        return datos

    def test_form_valido(self):
        form = FeriadoForm(self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_nombre_requerido(self):
        form = FeriadoForm(self._datos(nombre=''))
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_form_fecha_requerida(self):
        form = FeriadoForm(self._datos(fecha=''))
        self.assertFalse(form.is_valid())
        self.assertIn('fecha', form.errors)

    def test_form_rechaza_fecha_duplicada(self):
        Feriado.objects.create(
            fecha=date(2026, 1, 1), nombre='Año Nuevo',
            tipo=Feriado.Tipo.NACIONAL, ambito=Feriado.Ambito.NACIONAL,
        )
        form = FeriadoForm(self._datos())
        self.assertFalse(form.is_valid())
        self.assertIn(MSG_DUPLICADO, form.errors['fecha'])

    def test_form_permite_misma_fecha_al_editar_el_mismo(self):
        feriado = Feriado.objects.create(
            fecha=date(2026, 1, 1), nombre='Año Nuevo',
            tipo=Feriado.Tipo.NACIONAL, ambito=Feriado.Ambito.NACIONAL,
        )
        form = FeriadoForm(self._datos(nombre='Año Nuevo (editado)'), instance=feriado)
        self.assertTrue(form.is_valid(), form.errors)


class FeriadoCrearEndpointTests(TestCase):
    """CAV-54 / CAV-158: endpoint de registro vía vista."""

    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='clave12345')
        self.client.force_login(self.user)
        self.url = reverse('administracion:feriado_api_crear')

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type='application/json'
        )

    def test_registro_exitoso(self):
        resp = self._post({
            'fecha': '2026-07-28', 'nombre': 'Fiestas Patrias',
            'tipo': Feriado.Tipo.NACIONAL, 'ambito': Feriado.Ambito.NACIONAL,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')
        self.assertTrue(Feriado.objects.filter(fecha=date(2026, 7, 28)).exists())

    def test_rechazo_fecha_duplicada_mensaje_exacto(self):
        Feriado.objects.create(
            fecha=date(2026, 7, 28), nombre='Fiestas Patrias',
            tipo=Feriado.Tipo.NACIONAL, ambito=Feriado.Ambito.NACIONAL,
        )
        resp = self._post({
            'fecha': '2026-07-28', 'nombre': 'Otro',
            'tipo': Feriado.Tipo.NACIONAL, 'ambito': Feriado.Ambito.NACIONAL,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['message'], MSG_DUPLICADO)
        self.assertEqual(Feriado.objects.filter(fecha=date(2026, 7, 28)).count(), 1)

    def test_rechazo_campos_requeridos(self):
        resp = self._post({
            'fecha': '2026-07-28', 'nombre': '',
            'tipo': Feriado.Tipo.NACIONAL, 'ambito': Feriado.Ambito.NACIONAL,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')
        self.assertFalse(Feriado.objects.exists())

    def test_rechazo_fecha_invalida(self):
        resp = self._post({
            'fecha': 'no-es-fecha', 'nombre': 'X',
            'tipo': Feriado.Tipo.NACIONAL, 'ambito': Feriado.Ambito.NACIONAL,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')

    def test_requiere_login(self):
        self.client.logout()
        resp = self._post({
            'fecha': '2026-07-28', 'nombre': 'Fiestas Patrias',
            'tipo': Feriado.Tipo.NACIONAL, 'ambito': Feriado.Ambito.NACIONAL,
        })
        self.assertIn(resp.status_code, (301, 302))
        self.assertFalse(Feriado.objects.exists())


class FeriadoPaginaTests(TestCase):
    """CAV-55: la página y su template renderizan sin errores."""

    def setUp(self):
        self.user = User.objects.create_user(username='tester2', password='clave12345')
        self.client.force_login(self.user)

    def test_pagina_gestion_renderiza(self):
        resp = self.client.get(reverse('administracion:gestion_feriados'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'administracion/feriados/gestion_feriados.html')
        self.assertContains(resp, 'Gestión de Feriados')

    def test_api_list_devuelve_json(self):
        Feriado.objects.create(
            fecha=date(2026, 1, 1), nombre='Año Nuevo',
            tipo=Feriado.Tipo.NACIONAL, ambito=Feriado.Ambito.NACIONAL,
        )
        resp = self.client.get(reverse('administracion:feriados_api_list'), {'anio': 2026})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(len(data['feriados']), 1)
        self.assertEqual(data['feriados'][0]['ambito_display'], 'Nacional')
