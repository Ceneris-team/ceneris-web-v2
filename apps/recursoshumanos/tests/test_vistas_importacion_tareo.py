"""Pruebas de las vistas de importación de tareo.

Cubren dos fallos vistos en uso real:

* recargar la previsualización (F5) devolvía un 405 en blanco, porque la URL
  solo aceptaba POST y el navegador la pedía por GET;
* la sospecha de que importar cerraba la sesión del usuario. No es así: en
  esta instalación `SESION_UNICA_EXIMIR_SUPERUSUARIO=0`, y lo que cerraba
  sesiones era iniciar sesión con la misma cuenta desde otro sitio. Esta
  prueba deja fijado que la importación no la toca.
"""

import io
from datetime import date

import openpyxl
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accesos.models import SesionCerradaRemotamente
from recursoshumanos.models import (Area, AsignacionProyecto, Proyecto,
                                    TareoDiario, Trabajador)


def libro_de_una_semana():
    """Un bloque semanal de agosto de 2026 con una sola persona marcada."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '2026'
    ws.cell(2, 5, 'AGOSTO')
    ws.cell(4, 3, 'POSICIÓN')
    ws.cell(4, 4, 'NOMBRE')
    for i, numero in enumerate([3, 4, 5, 6, 7, 8, 9]):
        ws.cell(3, 5 + i, numero)
    ws.cell(5, 3, 'M1')
    ws.cell(5, 4, 'DIEGO HERNANI')
    for i in range(3):
        ws.cell(5, 5 + i, 'M1')

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class ImportacionTareoVistaTests(TestCase):
    def setUp(self):
        # El grupo ya lo crea una migración del proyecto.
        grupo, _ = Group.objects.get_or_create(name='Recursos Humanos')
        self.usuario = get_user_model().objects.create_user(
            username='rrhh', password='clave-de-prueba')
        self.usuario.groups.add(grupo)

        self.area = Area.objects.create(nombre='Operaciones QA')
        self.trabajador = Trabajador.objects.create(
            dni='10000001', nombres='DIEGO ARMANDO', apellido_paterno='HERNANI',
            apellido_materno='ROJAS', area=self.area, activo=True)

        self.url_importar = reverse('recursoshumanos:importar_tareo')
        self.url_tareo = reverse('recursoshumanos:gestion_tareo')
        self.client.login(username='rrhh', password='clave-de-prueba')

    def _subir(self):
        archivo = SimpleUploadedFile(
            'tareo.xlsx', libro_de_una_semana(),
            content_type=('application/vnd.openxmlformats-officedocument'
                          '.spreadsheetml.sheet'))
        return self.client.post(self.url_importar, {
            'mes': '2026-08', 'q': '', 'proyecto': '', 'subproyecto': '',
            'area': str(self.area.id), 'archivo': archivo,
        })

    # ---- recarga de la previsualización ----

    def test_get_a_importar_redirige_al_tareo_en_vez_de_dar_405(self):
        respuesta = self.client.get(
            self.url_importar, {'mes': '2026-08', 'area': str(self.area.id)})

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(self.url_tareo, respuesta['Location'])
        self.assertIn('mes=2026-08', respuesta['Location'])
        self.assertIn(f'area={self.area.id}', respuesta['Location'])

    def test_get_a_confirmar_redirige_al_tareo_en_vez_de_dar_405(self):
        respuesta = self.client.get(
            reverse('recursoshumanos:importar_tareo_confirmar'), {'mes': '2026-08'})

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(self.url_tareo, respuesta['Location'])

    def test_get_sin_mes_no_revienta_y_vuelve_al_tareo(self):
        respuesta = self.client.get(self.url_importar)

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(self.url_tareo, respuesta['Location'])

    # ---- la previsualización mantiene la estructura de la matriz ----

    def test_la_previsualizacion_conserva_la_cabecera_de_la_matriz(self):
        """El título y los cinco filtros con sus dos botones son los mismos
        que en la matriz: la previsualización no cambia de página, solo cambia
        lo que se ve dentro de ella."""
        respuesta = self._subir()
        contenido = respuesta.content.decode()

        self.assertIn('Planificación Matricial', contenido)
        for control in ('id="buscadorTrabajador"', 'id="mes"', 'id="proyecto"',
                        'id="subproyecto"', 'id="area"',
                        'id="filtrarBtn"', 'id="limpiarFiltrosBtn"'):
            self.assertIn(control, contenido)

    def test_los_filtros_reciben_area_y_proyectos_de_cada_trabajador(self):
        """Los filtros de la previsualización corren en el navegador, así que
        necesitan por DNI lo mismo que filtra la matriz. Quien está asignado a
        un subproyecto también cuenta como del proyecto padre."""
        padre = Proyecto.objects.create(nombre='Monitoreo QA')
        hijo = Proyecto.objects.create(nombre='Monitoreo QA - Fase 2', parent=padre)
        AsignacionProyecto.objects.create(
            trabajador=self.trabajador, proyecto=hijo, activo=True)

        respuesta = self._subir()
        meta = respuesta.context['meta_trabajadores'][self.trabajador.dni]

        self.assertEqual(meta['a'], str(self.area.id))
        self.assertEqual(set(meta['p']), {str(hijo.id), str(padre.id)})

    # ---- la importación no toca la sesión ----

    def test_previsualizar_no_cierra_la_sesion(self):
        clave_antes = self.client.session.session_key

        respuesta = self._subir()

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.session.session_key, clave_antes)
        self.assertEqual(SesionCerradaRemotamente.objects.count(), 0)
        self.assertEqual(
            int(self.client.session['_auth_user_id']), self.usuario.pk)

    def test_confirmar_escribe_el_tareo_y_mantiene_la_sesion(self):
        previa = self._subir()
        fila = previa.context['filas'][0]
        clave_antes = self.client.session.session_key

        respuesta = self.client.post(
            reverse('recursoshumanos:importar_tareo_confirmar'), {
                'mes': '2026-08', 'q': '', 'proyecto': '', 'subproyecto': '',
                'area': str(self.area.id),
                'incluir_0': 'on', 'dni_0': self.trabajador.dni,
                'datos_0': fila['datos_json'],
            })

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session.session_key, clave_antes)
        self.assertEqual(SesionCerradaRemotamente.objects.count(), 0)

        dias = TareoDiario.objects.filter(trabajador=self.trabajador)
        self.assertEqual(dias.count(), 3)
        self.assertEqual(sorted(d.fecha for d in dias),
                         [date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)])
        self.assertEqual({d.estado for d in dias}, {'C'})
