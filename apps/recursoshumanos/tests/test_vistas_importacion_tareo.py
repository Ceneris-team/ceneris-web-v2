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
import json
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


def libro_con_nombres(nombres):
    """Un bloque de agosto de 2026 con las personas indicadas, 3 días marcados."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '2026'
    ws.cell(2, 5, 'AGOSTO')
    ws.cell(4, 3, 'POSICIÓN')
    ws.cell(4, 4, 'NOMBRE')
    for i, numero in enumerate([3, 4, 5, 6, 7, 8, 9]):
        ws.cell(3, 5 + i, numero)
    for orden, nombre in enumerate(nombres):
        fila = 5 + orden
        ws.cell(fila, 3, f'M{orden + 1}')
        ws.cell(fila, 4, nombre)
        for i in range(3):
            ws.cell(fila, 5 + i, f'M{orden + 1}')

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class AlertasDeFilaTests(TestCase):
    """La previsualización tiene que explicarle a RRHH qué decidir y por qué.

    El Excel no trae DNI: cuando el nombre no resuelve solo, la fila lleva una
    alerta con lo que dice literalmente el archivo, en vez de desaparecer o
    importarse a ciegas.
    """

    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name='Recursos Humanos')
        self.usuario = get_user_model().objects.create_user(
            username='rrhh2', password='clave-de-prueba')
        self.usuario.groups.add(grupo)
        self.area = Area.objects.create(nombre='Operaciones QA')
        Trabajador.objects.create(
            dni='10000001', nombres='DIEGO ARMANDO', apellido_paterno='HERNANI',
            apellido_materno='ROJAS', area=self.area, activo=True)
        self.client.login(username='rrhh2', password='clave-de-prueba')

    def _subir(self, nombres):
        archivo = SimpleUploadedFile(
            'tareo.xlsx', libro_con_nombres(nombres),
            content_type=('application/vnd.openxmlformats-officedocument'
                          '.spreadsheetml.sheet'))
        return self.client.post(reverse('recursoshumanos:importar_tareo'), {
            'mes': '2026-08', 'q': '', 'proyecto': '', 'subproyecto': '',
            'area': str(self.area.id), 'archivo': archivo,
        })

    def _fila(self, respuesta, nombre_excel):
        return next(f for f in respuesta.context['filas']
                    if f['nombre_excel'] == nombre_excel)

    def test_nombre_desconocido_avisa_y_no_desaparece(self):
        respuesta = self._subir(['PERSONA INEXISTENTE'])

        fila = self._fila(respuesta, 'PERSONA INEXISTENTE')
        self.assertEqual(fila['alerta']['tipo'], 'sin_match')
        self.assertIn('PERSONA INEXISTENTE', fila['alerta']['detalle'])
        self.assertEqual(respuesta.context['total_por_revisar'], 1)
        self.assertContains(respuesta, 'data-alerta-tipo="sin_match"')

    def test_nota_entre_parentesis_se_menciona_en_la_alerta(self):
        respuesta = self._subir(['DIEGO HERNANI (vacaciones)'])

        fila = self._fila(respuesta, 'DIEGO HERNANI (vacaciones)')
        # La nota rompe el emparejamiento (el nombre deja de coincidir), y esa
        # es justo la fila que RRHH tiene que decidir: el archivo no dice si
        # esos días son campo o no, así que el aviso cita la nota literal.
        self.assertEqual(fila['alerta']['tipo'], 'sin_match')
        self.assertIn('«vacaciones»', fila['alerta']['detalle'])
        self.assertIn('desmarcar la fila', fila['alerta']['detalle'])

    def test_fila_normal_no_lleva_alerta(self):
        respuesta = self._subir(['DIEGO HERNANI'])

        self.assertIsNone(self._fila(respuesta, 'DIEGO HERNANI')['alerta'])
        self.assertEqual(respuesta.context['total_por_revisar'], 0)
        self.assertNotContains(respuesta, 'data-alerta-tipo')


def libro_con_secciones():
    """Agosto de 2026: una fila de campo y una del turno Vallecito."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '2026'
    ws.cell(2, 5, 'AGOSTO')
    ws.cell(4, 2, 'PERSONAL EN CAMPO')
    ws.merge_cells(start_row=4, end_row=5, start_column=2, end_column=2)
    ws.cell(6, 2, 'PERSONAL VALLECITO\nFINALIZACIÓN DE CADENAS DE CUSTODIA')
    ws.merge_cells(start_row=6, end_row=8, start_column=2, end_column=2)
    ws.cell(4, 3, 'POSICIÓN')
    ws.cell(4, 4, 'NOMBRE')
    for i, numero in enumerate([3, 4, 5, 6, 7, 8, 9]):
        ws.cell(3, 5 + i, numero)

    ws.cell(5, 3, 'M1')
    ws.cell(5, 4, 'DIEGO HERNANI')
    for i in range(3):
        ws.cell(5, 5 + i, 'M1')

    ws.cell(6, 3, 'M17')
    ws.cell(6, 4, 'JULIO HUAMAN')
    for i in (0, 1, 4):
        ws.cell(6, 5 + i, 'M17')

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class PersonalDeOtraSeccionTests(TestCase):
    """El personal que el Excel pone fuera de PERSONAL EN CAMPO se muestra.

    Antes se descartaba en silencio, y como las hojas de junio en adelante ya no
    traen la columna de rótulo, la misma persona entraba o no según el mes.
    Ahora llega marcada y sin asignar: la decisión es de RRHH.
    """

    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name='Recursos Humanos')
        u = get_user_model().objects.create_user(username='rrhh3', password='clave-de-prueba')
        u.groups.add(grupo)
        self.area = Area.objects.create(nombre='Operaciones QA')
        Trabajador.objects.create(
            dni='10000001', nombres='DIEGO ARMANDO', apellido_paterno='HERNANI',
            apellido_materno='ROJAS', area=self.area, activo=True)
        Trabajador.objects.create(
            dni='10000005', nombres='JULIO', apellido_paterno='HUAMAN',
            apellido_materno='CONDORI', area=self.area, activo=True)
        self.client.login(username='rrhh3', password='clave-de-prueba')

        archivo = SimpleUploadedFile(
            'tareo.xlsx', libro_con_secciones(),
            content_type=('application/vnd.openxmlformats-officedocument'
                          '.spreadsheetml.sheet'))
        self.respuesta = self.client.post(
            reverse('recursoshumanos:importar_tareo'), {
                'mes': '2026-08', 'q': '', 'proyecto': '', 'subproyecto': '',
                'area': str(self.area.id), 'archivo': archivo,
            })
        self.filas = {f['nombre_excel']: f for f in self.respuesta.context['filas']}

    def test_la_fila_de_campo_entra_normal(self):
        fila = self.filas['DIEGO HERNANI']
        self.assertTrue(fila['asignada'])
        self.assertFalse(fila['otra_seccion'])
        self.assertIsNone(fila['alerta'])

    def test_la_fila_de_vallecito_entra_como_dia_libre_y_no_como_campo(self):
        fila = self.filas['JULIO HUAMAN']
        self.assertTrue(fila['otra_seccion'])
        self.assertTrue(fila['asignada'])
        # Lo importante: el Excel no dice qué turno es, así que NO se da por
        # bueno trabajo de campo. Entra como día libre y RRHH cambia el tipo.
        self.assertEqual(fila['tipo_inicial'], 'D')
        self.assertEqual({d['estado'] for d in fila['dias'].values()}, {'D'})

    def test_la_fila_de_campo_sigue_siendo_campo(self):
        fila = self.filas['DIEGO HERNANI']
        self.assertEqual(fila['tipo_inicial'], 'C')
        self.assertEqual({d['estado'] for d in fila['dias'].values()}, {'C'})

    def test_la_alerta_dice_la_seccion_el_nombre_y_los_dias(self):
        alerta = self.filas['JULIO HUAMAN']['alerta']
        self.assertEqual(alerta['tipo'], 'otra_seccion')
        self.assertIn('VALLECITO', alerta['titulo'])
        self.assertIn('JULIO HUAMAN', alerta['detalle'])
        self.assertIn('HUAMAN CONDORI, JULIO', alerta['detalle'])
        self.assertIn('3, 4 y 7 de Agosto de 2026', alerta['detalle'])

    def test_el_resumen_cuenta_las_filas_de_otra_seccion(self):
        self.assertEqual(self.respuesta.context['total_otra_seccion'], 1)
        self.assertContains(self.respuesta, 'data-alerta-tipo="otra_seccion"')
        self.assertContains(self.respuesta, 'trabajador-col sticky-col otra-seccion')


class TiposDeJornadaAlConfirmarTests(TestCase):
    """RRHH puede reclasificar la fila antes de importar.

    El Excel solo sabe de campo; el tipo real (oficina, personalizado, jornada
    por horas, libre) lo decide RRHH en la previsualización, y P y J pueden
    llevar sus horas desde ahí.
    """

    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name='Recursos Humanos')
        u = get_user_model().objects.create_user(username='rrhh4', password='clave-de-prueba')
        u.groups.add(grupo)
        self.area = Area.objects.create(nombre='Operaciones QA')
        self.trabajador = Trabajador.objects.create(
            dni='10000001', nombres='DIEGO ARMANDO', apellido_paterno='HERNANI',
            apellido_materno='ROJAS', area=self.area, activo=True)
        self.client.login(username='rrhh4', password='clave-de-prueba')
        self.url = reverse('recursoshumanos:importar_tareo_confirmar')

    def _confirmar(self, estado, extra=None):
        datos = json.dumps({'3': {'e': estado, 'u': None},
                            '4': {'e': estado, 'u': None}})
        campos = {
            'mes': '2026-08', 'q': '', 'proyecto': '', 'subproyecto': '',
            'area': str(self.area.id),
            'incluir_0': 'on', 'dni_0': self.trabajador.dni, 'datos_0': datos,
        }
        campos.update(extra or {})
        return self.client.post(self.url, campos)

    def test_dia_libre_se_guarda_como_libre(self):
        self._confirmar('D')
        dias = TareoDiario.objects.filter(trabajador=self.trabajador)
        self.assertEqual(dias.count(), 2)
        self.assertEqual({d.estado for d in dias}, {'D'})

    def test_oficina_toma_el_horario_de_oficina(self):
        self._confirmar('O')
        # 3 y 4 de agosto de 2026 son lunes y martes: 08:30 a 18:00.
        for dia in TareoDiario.objects.filter(trabajador=self.trabajador):
            self.assertEqual(dia.estado, 'O')
            self.assertEqual(dia.hora_entrada.strftime('%H:%M'), '08:30')
            self.assertEqual(dia.hora_salida.strftime('%H:%M'), '18:00')

    def test_personalizado_guarda_las_horas_que_escribio_rrhh(self):
        self._confirmar('P', {'hora_entrada_0': '07:15', 'hora_salida_0': '15:45'})
        for dia in TareoDiario.objects.filter(trabajador=self.trabajador):
            self.assertEqual(dia.estado, 'P')
            self.assertEqual(dia.hora_entrada.strftime('%H:%M'), '07:15')
            self.assertEqual(dia.hora_salida.strftime('%H:%M'), '15:45')

    def test_jornada_por_horas_guarda_las_horas(self):
        self._confirmar('J', {'jornada_horas_0': '6.5'})
        for dia in TareoDiario.objects.filter(trabajador=self.trabajador):
            self.assertEqual(dia.estado, 'J')
            self.assertEqual(float(dia.jornada_horas), 6.5)

    def test_personalizado_sin_horas_entra_igual_para_completarlo_luego(self):
        self._confirmar('P')
        for dia in TareoDiario.objects.filter(trabajador=self.trabajador):
            self.assertEqual(dia.estado, 'P')
            self.assertIsNone(dia.hora_entrada)

    def test_un_estado_inventado_no_entra(self):
        respuesta = self._confirmar('F')
        self.assertEqual(TareoDiario.objects.count(), 0)
        self.assertEqual(respuesta.status_code, 302)
