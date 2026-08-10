from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone

from recursoshumanos.models import Sede, Trabajador

from .views import (
    HORA_REFERENCIA_ENTRADA,
    HORA_REFERENCIA_ENTRADA_SABADO,
    TARDANZA_MINIMA_MINUTOS,
    _areas_bajo_responsabilidad,
    _areas_operativas_activas_qs,
    _clasificar_areas_responsable_por_supervision,
    _construir_resumen_asistencia,
    _es_gerente_puro,
    _es_lider,
    _es_responsable,
    _es_supervisor,
    _es_trabajador_base,
    _objetivos_evaluacion_por_area,
    _objetivos_supervisores_consolidados,
    _q_gerente_puro,
    _resolver_cascada_objetivos_gerencia,
    _resolver_filtro_mes_anio,
)


@login_required
def panel_asistencias(request):
    try:
        perfil = request.user.trabajador
    except Exception:
        return render(request, 'metricas_ceneris/error.html', {'mensaje': 'No tienes perfil asignado.'})

    if not _es_lider(perfil):
        return redirect('metricas_ceneris:dashboard_trabajador')

    es_rol_combinado = False
    es_responsable = _es_responsable(perfil)
    es_supervisor = _es_supervisor(perfil)

    ruta_actual = getattr(getattr(request, 'resolver_match', None), 'url_name', '')
    if es_responsable and ruta_actual == 'panel_asistencias':
        return redirect('metricas_ceneris:panel_asistencias_responsable')
    if es_supervisor and ruta_actual == 'panel_asistencias_responsable':
        return redirect('metricas_ceneris:panel_asistencias')

    es_gerente = _es_gerente_puro(perfil)
    modo_asistencia = 'gerencia' if es_gerente else 'equipo'

    modo_responsable = ''
    mostrar_selector_responsable = False
    areas_con_supervisor = []
    areas_sin_supervisor = []
    primera_area_sin_supervisor_id = None
    mostrar_filtro_supervisor = True
    mostrar_filtro_trabajador = True

    hoy = timezone.now().date()
    mes, anio, inicio_mes, fin_mes = _resolver_filtro_mes_anio(request, hoy)

    tipo_colaborador = request.GET.get('tipo_colaborador', 'todos')
    if tipo_colaborador == 'jefe':
        tipo_colaborador = 'supervisor'
    if tipo_colaborador not in ['todos', 'trabajador', 'supervisor']:
        tipo_colaborador = 'todos'

    mostrar_filtro_tipo_colaborador = es_gerente or es_responsable or es_rol_combinado
    if not mostrar_filtro_tipo_colaborador:
        # Supervisor puro: su panel solo maneja trabajadores base.
        tipo_colaborador = 'trabajador'

    filtro_faltas = (request.GET.get('filtro_faltas') or 'todos').strip().lower()
    if filtro_faltas not in ['todos', 'con_faltas', 'sin_faltas']:
        filtro_faltas = 'todos'

    filtro_tardanza = (request.GET.get('filtro_tardanza') or 'todos').strip().lower()
    if filtro_tardanza not in ['todos', 'con_tardanza', 'sin_tardanza']:
        filtro_tardanza = 'todos'

    filtro_asistencia = (request.GET.get('filtro_asistencia') or 'todos').strip().lower()
    if filtro_asistencia not in ['todos', 'alta', 'media', 'baja']:
        filtro_asistencia = 'todos'

    nota_orden = request.GET.get('nota_orden', 'desc')
    if nota_orden not in ['desc', 'asc']:
        nota_orden = 'desc'

    busqueda_nombre = request.GET.get('q', '').strip()

    sedes_disponibles = Sede.objects.filter(activo=True).order_by('nombre')
    sede_id = request.GET.get('sede', 'todas')
    sede_seleccionada = None

    areas_asignadas = []
    areas_filtro_gerencia = []
    area_activa_id = None

    alcance_gerencia = 'todo'
    areas_con_mando_activo = []
    areas_directas_gerencia = []

    if es_gerente:
        alcance_gerencia = (request.GET.get('alcance_gerencia') or 'todo').strip().lower()
        if alcance_gerencia not in ['todo', 'mandos', 'directas']:
            alcance_gerencia = 'todo'

        cascada = _resolver_cascada_objetivos_gerencia(perfil, hoy)
        areas_con_mando_activo = [item['area'] for item in cascada['areas_con_liderazgo']]
        areas_directas_gerencia = [item['area'] for item in cascada['areas_directas']]

        ids_areas_con_mando = [area.id for area in areas_con_mando_activo]
        ids_areas_directas = [area.id for area in areas_directas_gerencia]

        trabajadores = Trabajador.objects.filter(activo=True).filter(~_q_gerente_puro()).select_related('sede', 'area').distinct()

        if alcance_gerencia == 'mandos':
            if ids_areas_con_mando:
                trabajadores = trabajadores.filter(area_id__in=ids_areas_con_mando)
            else:
                trabajadores = Trabajador.objects.none()
        elif alcance_gerencia == 'directas':
            if ids_areas_directas:
                trabajadores = trabajadores.filter(area_id__in=ids_areas_directas)
            else:
                trabajadores = Trabajador.objects.none()

        if alcance_gerencia == 'mandos':
            areas_filtro_gerencia = sorted(areas_con_mando_activo, key=lambda a: (a.nombre or '').lower())
        elif alcance_gerencia == 'directas':
            areas_filtro_gerencia = sorted(areas_directas_gerencia, key=lambda a: (a.nombre or '').lower())
        else:
            areas_filtro_gerencia = list(_areas_operativas_activas_qs())

        area_id_param = request.GET.get('area_id')
        if area_id_param:
            try:
                area_id_gerencia = int(area_id_param)
            except (TypeError, ValueError):
                area_id_gerencia = None

            if area_id_gerencia and any(a.id == area_id_gerencia for a in areas_filtro_gerencia):
                trabajadores = trabajadores.filter(area_id=area_id_gerencia)
                area_activa_id = area_id_gerencia

        if sede_id != 'todas':
            try:
                sede_seleccionada = sedes_disponibles.filter(id=int(sede_id)).first()
                if sede_seleccionada:
                    trabajadores = trabajadores.filter(sede_id=sede_seleccionada.id)
                else:
                    sede_id = 'todas'
            except (TypeError, ValueError):
                sede_id = 'todas'

        def incluir_en_detalle(trabajador, _nota_asistencia):
            if trabajador.id == perfil.id:
                return False
            if tipo_colaborador == 'trabajador':
                return _es_trabajador_base(trabajador)
            if tipo_colaborador == 'supervisor':
                return _es_supervisor(trabajador)
            return True

        resumen_asistencia = _construir_resumen_asistencia(
            trabajadores,
            inicio_mes,
            fin_mes,
            incluir_en_detalle=incluir_en_detalle,
        )

        ambito_base = sede_seleccionada.nombre if sede_seleccionada else 'Empresa Ceneris'
        if alcance_gerencia == 'mandos':
            ambito_nombre = f"{ambito_base} - Áreas con mando activo"
        elif alcance_gerencia == 'directas':
            ambito_nombre = f"{ambito_base} - Áreas directas"
        else:
            ambito_nombre = ambito_base

        if area_activa_id:
            area_filtro = next((a for a in areas_filtro_gerencia if a.id == area_activa_id), None)
            if area_filtro:
                ambito_nombre = f"{ambito_nombre} - {area_filtro.nombre}"

        area = None
    else:
        area = None

        if es_responsable:
            areas_responsable = _areas_bajo_responsabilidad(perfil)
            areas_con_supervisor, areas_sin_supervisor = _clasificar_areas_responsable_por_supervision(
                perfil,
                areas_responsable,
            )
            primera_area_sin_supervisor_id = areas_sin_supervisor[0].id if areas_sin_supervisor else None

            modo_param = (request.GET.get('modo_responsable') or '').strip().lower()
            if modo_param in ['supervisor', 'supervisores']:
                modo_responsable = 'supervisores'
            elif modo_param in ['equipo', 'equipos', 'trabajador', 'trabajadores']:
                modo_responsable = 'equipos'

            if areas_con_supervisor and areas_sin_supervisor:
                mostrar_selector_responsable = True
                if modo_responsable not in ['supervisores', 'equipos']:
                    modo_responsable = 'supervisores'
            elif areas_con_supervisor:
                modo_responsable = 'supervisores'
            else:
                modo_responsable = 'equipos'

            if modo_responsable == 'supervisores':
                areas_asignadas = []
                trabajadores = _objetivos_supervisores_consolidados(perfil, areas_con_supervisor)
                resumen_asistencia = _construir_resumen_asistencia(trabajadores, inicio_mes, fin_mes)
                ambito_nombre = f"Supervisores consolidados ({len(areas_con_supervisor)} áreas)"
                mostrar_filtro_supervisor = True
                mostrar_filtro_trabajador = False
                if tipo_colaborador == 'trabajador':
                    tipo_colaborador = 'supervisor'
            else:
                areas_asignadas = areas_sin_supervisor
                area_id_param = request.GET.get('area_id')

                if areas_asignadas:
                    if area_id_param:
                        try:
                            area_id = int(area_id_param)
                            area = next((a for a in areas_asignadas if a.id == area_id), None)
                        except (TypeError, ValueError):
                            area = None

                    if area is None:
                        area = areas_asignadas[0]

                    area_activa_id = area.id

                trabajadores = _objetivos_evaluacion_por_area(perfil, area)
                resumen_asistencia = _construir_resumen_asistencia(trabajadores, inicio_mes, fin_mes)
                ambito_nombre = area.nombre if area else 'Area sin asignar'
                mostrar_filtro_supervisor = False
                mostrar_filtro_trabajador = True
                if tipo_colaborador == 'supervisor':
                    tipo_colaborador = 'trabajador'
        else:
            areas_asignadas = _areas_bajo_responsabilidad(perfil)

            area_id_param = request.GET.get('area_id')

            if areas_asignadas:
                if area_id_param:
                    try:
                        area_id = int(area_id_param)
                        area = next((a for a in areas_asignadas if a.id == area_id), None)
                    except (TypeError, ValueError):
                        area = None

                if area is None:
                    area = areas_asignadas[0]

                area_activa_id = area.id

            trabajadores = _objetivos_evaluacion_por_area(perfil, area)
            resumen_asistencia = _construir_resumen_asistencia(trabajadores, inicio_mes, fin_mes)
            ambito_nombre = area.nombre if area else 'Area sin asignar'

        if tipo_colaborador == 'supervisor':
            resumen_asistencia['datos'] = [
                item for item in resumen_asistencia['datos']
                if _es_supervisor(item['trabajador'])
            ]
        elif tipo_colaborador == 'trabajador':
            resumen_asistencia['datos'] = [
                item for item in resumen_asistencia['datos']
                if _es_trabajador_base(item['trabajador'])
            ]

    if tipo_colaborador != 'todos' and es_gerente:
        resumen_asistencia['datos'] = list(resumen_asistencia['datos'])

    if busqueda_nombre:
        termino = busqueda_nombre.lower()
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if termino in f"{item['trabajador'].nombres} {item['trabajador'].apellido_paterno} {item['trabajador'].apellido_materno or ''}".lower()
        ]

    if filtro_faltas == 'con_faltas':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['faltas'] > 0
        ]
    elif filtro_faltas == 'sin_faltas':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['faltas'] == 0
        ]

    if filtro_tardanza == 'con_tardanza':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['dias_tarde'] > 0
        ]
    elif filtro_tardanza == 'sin_tardanza':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['dias_tarde'] == 0
        ]

    if filtro_asistencia == 'alta':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['porc_asistencia'] >= 95
        ]
    elif filtro_asistencia == 'media':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if 85 <= item['porc_asistencia'] < 95
        ]
    elif filtro_asistencia == 'baja':
        resumen_asistencia['datos'] = [
            item for item in resumen_asistencia['datos']
            if item['porc_asistencia'] < 85
        ]

    resumen_asistencia['datos'] = sorted(
        resumen_asistencia['datos'],
        key=lambda item: item['nota_asistencia'],
        reverse=(nota_orden == 'desc')
    )

    paginator = Paginator(resumen_asistencia['datos'], 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    filtros_qs = request.GET.copy()
    filtros_qs.pop('page', None)
    filtros_query = filtros_qs.urlencode()
    resumen_asistencia['datos'] = page_obj.object_list

    anios_disponibles = list(range(hoy.year, hoy.year - 3, -1))

    meses_nombres = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    return render(request, 'metricas_ceneris/panel_asistencias.html', {
        'area': area,
        'areas_asignadas': areas_asignadas,
        'areas_filtro_gerencia': areas_filtro_gerencia,
        'areas_con_supervisor': areas_con_supervisor,
        'areas_sin_supervisor': areas_sin_supervisor,
        'primera_area_sin_supervisor_id': primera_area_sin_supervisor_id,
        'area_activa_id': area_activa_id,
        'es_rol_combinado': es_rol_combinado,
        'modo_asistencia': modo_asistencia,
        'modo_responsable': modo_responsable,
        'mostrar_selector_responsable': mostrar_selector_responsable,
        'es_responsable': es_responsable,
        'mostrar_filtro_supervisor': mostrar_filtro_supervisor,
        'mostrar_filtro_trabajador': mostrar_filtro_trabajador,
        'mostrar_filtro_tipo_colaborador': mostrar_filtro_tipo_colaborador,
        'es_gerente': es_gerente,
        'ambito_nombre': ambito_nombre,
        'fecha_actual': hoy,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'mes_nombre': meses_nombres[mes],
        'anios_disponibles': anios_disponibles,
        'inicio_mes': inicio_mes,
        'fin_mes': fin_mes,
        'sedes_disponibles': sedes_disponibles,
        'sede_seleccionada': sede_id,
        'tipo_colaborador': tipo_colaborador,
        'filtro_faltas': filtro_faltas,
        'filtro_tardanza': filtro_tardanza,
        'filtro_asistencia': filtro_asistencia,
        'nota_orden': nota_orden,
        'busqueda_nombre': busqueda_nombre,
        'page_obj': page_obj,
        'filtros_query': filtros_query,
        'alcance_gerencia': alcance_gerencia,
        'areas_con_mando_activo': areas_con_mando_activo,
        'areas_directas_gerencia': areas_directas_gerencia,
        'tardanza_minima_minutos': TARDANZA_MINIMA_MINUTOS,
        'hora_ref_semana': HORA_REFERENCIA_ENTRADA,
        'hora_ref_sabado': HORA_REFERENCIA_ENTRADA_SABADO,
        **resumen_asistencia,
    })
