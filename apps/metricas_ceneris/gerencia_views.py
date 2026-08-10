from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

import json

from recursoshumanos.models import Area, Sede, TareoDiario, Trabajador

from .models import EvaluacionMensual
from .views import (
    _anio_semestre_por_fecha,
    _calcular_score_total,
    _es_gerente_puro,
    _es_responsable,
    _es_supervisor,
    _es_trabajador_base,
    _estado_evaluacion_para_fecha,
    _esta_en_periodo_prueba,
    _fecha_referencia_periodo,
    _q_responsable,
    _q_supervisor,
    _q_trabajador_base,
    _resolver_cascada_objetivos_gerencia,
    _resolver_filtro_periodo_request,
    _responsables_activos_por_area,
    _serializar_item_ranking_tabla,
    _supervisores_activos_por_area,
)


@login_required
def dashboard_gerente(request):
    try:
        usuario = request.user.trabajador
        if not _es_gerente_puro(usuario):
            return redirect('metricas_ceneris:inicio_metricas')
    except Exception:
        return redirect('metricas_ceneris:inicio_metricas')

    hoy = timezone.now().date()
    _, semestre_hoy = _anio_semestre_por_fecha(hoy)
    filtro_periodo = _resolver_filtro_periodo_request(request, hoy, periodo_default='semestre')
    periodo_tabla_defecto = filtro_periodo['periodo']
    anio_tabla_defecto = filtro_periodo['anio']
    mes_tabla_defecto = filtro_periodo['mes'] or hoy.month
    semestre_tabla_defecto = filtro_periodo['semestre'] or semestre_hoy

    parametros_periodo = {'anio': anio_tabla_defecto}
    if periodo_tabla_defecto == 'mes':
        parametros_periodo['mes'] = mes_tabla_defecto
    else:
        parametros_periodo['semestre'] = semestre_tabla_defecto

    sede_id = request.GET.get('sede', 'todas')

    todos_trabajadores = Trabajador.objects.filter(activo=True).select_related('area', 'sede')
    if sede_id != 'todas' and sede_id:
        try:
            todos_trabajadores = todos_trabajadores.filter(sede_id=int(sede_id))
        except ValueError:
            pass

    ranking_trabajadores_periodo = []
    ranking_jefes_periodo = []
    scores_por_area_periodo = {}
    fecha_ref_periodo = _fecha_referencia_periodo(
        hoy,
        periodo_tabla_defecto,
        **parametros_periodo,
    )

    for t in todos_trabajadores:
        datos_periodo = _calcular_score_total(
            t,
            hoy,
            periodo_tabla_defecto,
            **parametros_periodo,
        )
        puntaje = datos_periodo['score_total']
        promedio_eval = datos_periodo['desempeno_compuesto']
        promedio_mensual = datos_periodo['promedio_mensual']
        promedio_semestral = datos_periodo['promedio_semestral']
        porc_asistencia = datos_periodo['asistencia_pct']

        if t.area and puntaje > 0:
            if t.area.nombre not in scores_por_area_periodo:
                scores_por_area_periodo[t.area.nombre] = []
            scores_por_area_periodo[t.area.nombre].append(puntaje)

        if _es_trabajador_base(t):
            if puntaje > 0 and not _esta_en_periodo_prueba(t, fecha_ref_periodo):
                ranking_trabajadores_periodo.append({
                    'trabajador': t,
                    'score': round(puntaje, 2),
                    'eval_avg': round(promedio_eval, 2),
                    'promedio_mensual': round(promedio_mensual, 2),
                    'promedio_semestral': round(promedio_semestral, 2),
                    'asistencia_avg': round(porc_asistencia / 10, 1),
                    'score_porc': round(puntaje * 10, 1),
                    'eval_porc': round(promedio_eval * 10, 1),
                    'promedio_mensual_porc': round(promedio_mensual * 10, 1),
                    'promedio_semestral_porc': round(promedio_semestral * 10, 1),
                    'area_nombre': t.area.nombre if t.area else 'Sin Area',
                })
        elif _es_supervisor(t) or _es_responsable(t):
            if puntaje > 0 and not _esta_en_periodo_prueba(t, fecha_ref_periodo):
                ranking_jefes_periodo.append({
                    'trabajador': t,
                    'score': round(puntaje, 2),
                    'eval_avg': round(promedio_eval, 2),
                    'promedio_mensual': round(promedio_mensual, 2),
                    'promedio_semestral': round(promedio_semestral, 2),
                    'asistencia_avg': round(porc_asistencia / 10, 1),
                    'score_porc': round(puntaje * 10, 1),
                    'eval_porc': round(promedio_eval * 10, 1),
                    'promedio_mensual_porc': round(promedio_mensual * 10, 1),
                    'promedio_semestral_porc': round(promedio_semestral * 10, 1),
                    'area_nombre': t.area.nombre if t.area else 'Sin Area',
                })

    ranking_trabajadores_periodo.sort(key=lambda x: x['score'], reverse=True)
    ranking_jefes_periodo.sort(key=lambda x: x['score'], reverse=True)

    podio_trabajadores_periodo = ranking_trabajadores_periodo[:3]
    podio_jefes_periodo = ranking_jefes_periodo[:3]

    mejor_trabajador_periodo = ranking_trabajadores_periodo[0] if ranking_trabajadores_periodo else None
    mejor_jefe_periodo = ranking_jefes_periodo[0] if ranking_jefes_periodo else None

    lista_areas_promedio = []
    for nombre_area, puntajes in scores_por_area_periodo.items():
        promedio = sum(puntajes) / len(puntajes)
        lista_areas_promedio.append({
            'nombre': nombre_area,
            'promedio': round(promedio, 2),
            'promedio_porc': round(promedio * 10, 1),
        })

    lista_areas_promedio.sort(key=lambda x: x['promedio'], reverse=True)

    labels_areas = [item['nombre'] for item in lista_areas_promedio]
    data_areas = [item['promedio'] for item in lista_areas_promedio]
    mejor_area_periodo = lista_areas_promedio[0] if lista_areas_promedio else None

    sedes = Sede.objects.filter(activo=True).order_by('nombre')

    min_eval = EvaluacionMensual.objects.aggregate(valor=Min('fecha_evaluacion'))['valor']
    min_tareo = TareoDiario.objects.aggregate(valor=Min('fecha'))['valor']
    candidatos_inicio = [d.year for d in [min_eval, min_tareo] if d]
    anio_inicio = min(candidatos_inicio) if candidatos_inicio else max(hoy.year - 2, 2020)
    anios_disponibles = list(range(hoy.year, anio_inicio - 1, -1))
    meses_disponibles = [
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ]

    return render(request, 'metricas_ceneris/gerente/dashboard_gerente.html', {
        'usuario': usuario,
        'anio': anio_tabla_defecto,
        'podio_trabajadores_anio': podio_trabajadores_periodo,
        'podio_trabajadores_mes': podio_trabajadores_periodo,
        'podio_jefes_anio': podio_jefes_periodo,
        'podio_jefes_mes': podio_jefes_periodo,
        'mejor_trabajador_anio': mejor_trabajador_periodo,
        'mejor_trabajador_mes': mejor_trabajador_periodo,
        'mejor_jefe_anio': mejor_jefe_periodo,
        'mejor_jefe_mes': mejor_jefe_periodo,
        'mejor_area': mejor_area_periodo,
        'mejor_area_mes': mejor_area_periodo,
        'labels_areas': labels_areas,
        'data_areas': data_areas,
        'labels_areas_json': json.dumps(labels_areas, ensure_ascii=False),
        'data_areas_json': json.dumps(data_areas),
        'sedes': sedes,
        'sede_seleccionada': sede_id,
        'anios_disponibles': anios_disponibles,
        'meses_disponibles': meses_disponibles,
        'periodo_tabla_defecto': periodo_tabla_defecto,
        'anio_tabla_defecto': anio_tabla_defecto,
        'mes_tabla_defecto': mes_tabla_defecto,
        'semestre_tabla_defecto': semestre_tabla_defecto,
    })


@login_required
def panel_evaluacion_gerente(request):
    try:
        perfil = request.user.trabajador
    except Exception:
        return render(request, 'metricas_ceneris/error.html', {'mensaje': 'No tienes perfil asignado.'})

    if not _es_gerente_puro(perfil):
        return redirect('metricas_ceneris:inicio_metricas')

    hoy = timezone.now().date()
    cascada = _resolver_cascada_objetivos_gerencia(perfil, hoy)

    jefes_qs = cascada['lideres_objetivo']
    areas_asignadas_gerencia = cascada['areas_con_liderazgo']
    areas_directas = cascada['areas_directas']
    areas_con_responsable = [
        item for item in areas_asignadas_gerencia
        if item.get('nivel_cascada') == 'RESPONSABLE'
    ]
    areas_con_supervisor_sin_responsable = [
        item for item in areas_asignadas_gerencia
        if item.get('nivel_cascada') == 'SUPERVISOR'
    ]

    area_activa_id = None
    area_id_param = request.GET.get('area_id')
    if area_id_param:
        try:
            area_id_param = int(area_id_param)
        except (TypeError, ValueError):
            area_id_param = None

        if area_id_param and any(item['area'].id == area_id_param for item in areas_asignadas_gerencia):
            area_activa_id = area_id_param
            jefes_qs = jefes_qs.filter(
                Q(area_id=area_activa_id) | Q(areas_supervisadas__id=area_activa_id)
            ).distinct()

    for item in areas_asignadas_gerencia:
        item['activa'] = bool(area_activa_id and item['area'].id == area_activa_id)

    jefes = list(jefes_qs)

    tipo_lider = (request.GET.get('tipo_lider') or 'todos').strip().lower()
    if tipo_lider not in ['todos', 'responsable', 'supervisor']:
        tipo_lider = 'todos'

    busqueda = (request.GET.get('q') or '').strip()
    busqueda_norm = busqueda.lower()

    total_evaluaciones_mes = 0
    promedios_jefes = []
    mejor_jefe = None
    mejor_nota = -1

    promedios_por_categoria = {'OPERACIONAL': [], 'ADMINISTRATIVO': [], 'HABILIDADES': []}

    for t in jefes:
        evals = t.evaluaciones.all()
        ultima_ev = evals.first()

        estado_eval = _estado_evaluacion_para_fecha(t, hoy)
        t.es_nuevo = estado_eval['es_nuevo']
        t.hito_tipo = estado_eval['hito_tipo']
        t.btn_hito_activo = estado_eval['btn_hito_activo']
        t.btn_mensual_activo = estado_eval['btn_mensual_activo']

        if _es_responsable(t):
            t.tipo_lider_label = 'Responsable'
            t.tipo_lider_badge = 'bg-indigo-50 text-indigo-700 border border-indigo-200'
        else:
            t.tipo_lider_label = 'Supervisor'
            t.tipo_lider_badge = 'bg-purple-50 text-purple-700 border border-purple-200'

        if ultima_ev:
            t.ultima_nota = ultima_ev.promedio_final
            promedios_jefes.append(t.ultima_nota)
            total_evaluaciones_mes += 1

            if t.ultima_nota > mejor_nota:
                mejor_nota = t.ultima_nota
                mejor_jefe = t

            for cat in ['OPERACIONAL', 'ADMINISTRATIVO', 'HABILIDADES']:
                avg_cat = ultima_ev.puntajes.filter(categoria=cat).aggregate(Avg('nota'))['nota__avg']
                if avg_cat:
                    promedios_por_categoria[cat].append(avg_cat)
        else:
            t.ultima_nota = 0

    jefes_filtrados = []
    for t in jefes:
        if tipo_lider == 'responsable' and not _es_responsable(t):
            continue
        if tipo_lider == 'supervisor' and not _es_supervisor(t):
            continue
        nombre_busqueda = f"{t.nombres or ''} {t.apellido_paterno or ''} {t.apellido_materno or ''}".strip().lower()
        if busqueda_norm and busqueda_norm not in nombre_busqueda:
            continue
        jefes_filtrados.append(t)

    jefes_filtrados = sorted(
        jefes_filtrados,
        key=lambda x: (
            -(x.ultima_nota or 0),
            (x.apellido_paterno or '').lower(),
            (x.nombres or '').lower(),
        )
    )

    promedio_area_total = round(sum(promedios_jefes) / len(promedios_jefes), 1) if promedios_jefes else 0

    radar_data = []
    for cat in ['OPERACIONAL', 'ADMINISTRATIVO', 'HABILIDADES']:
        lista = promedios_por_categoria[cat]
        promedio = round(sum(lista) / len(lista), 1) if lista else 0
        radar_data.append(promedio)

    total_responsables_objetivo = len([t for t in jefes if _es_responsable(t)])
    total_supervisores_objetivo = len([t for t in jefes if _es_supervisor(t)])
    total_responsables_filtrados = len([t for t in jefes_filtrados if _es_responsable(t)])
    total_supervisores_filtrados = len([t for t in jefes_filtrados if _es_supervisor(t)])
    total_equipos_directos = sum(item['total_colaboradores'] for item in areas_directas)
    total_pendientes_directos = sum(item['pendientes_mes'] for item in areas_directas)

    return render(request, 'metricas_ceneris/gerencia/panel_cascada_gerente.html', {
        'trabajadores': jefes_filtrados,
        'promedio_area': promedio_area_total,
        'total_evaluaciones': total_evaluaciones_mes,
        'mejor_trabajador': mejor_jefe,
        'radar_data': radar_data,
        'areas_asignadas_gerencia': areas_asignadas_gerencia,
        'areas_con_responsable': areas_con_responsable,
        'areas_con_supervisor_sin_responsable': areas_con_supervisor_sin_responsable,
        'areas_directas': areas_directas,
        'area_activa_id': area_activa_id,
        'total_responsables_objetivo': total_responsables_objetivo,
        'total_supervisores_objetivo': total_supervisores_objetivo,
        'total_responsables_filtrados': total_responsables_filtrados,
        'total_supervisores_filtrados': total_supervisores_filtrados,
        'total_lideres_filtrados': len(jefes_filtrados),
        'total_equipos_directos': total_equipos_directos,
        'total_pendientes_directos': total_pendientes_directos,
        'tipo_lider': tipo_lider,
        'busqueda': busqueda,
    })


@login_required
def panel_area_directa_gerencia(request, area_id):
    try:
        perfil = request.user.trabajador
    except Exception:
        return render(request, 'metricas_ceneris/error.html', {'mensaje': 'No tienes perfil asignado.'})

    if not _es_gerente_puro(perfil):
        return redirect('metricas_ceneris:inicio_metricas')

    area = get_object_or_404(Area, id=area_id)

    if _supervisores_activos_por_area(area).exclude(id=perfil.id).exists() or _responsables_activos_por_area(area).exclude(id=perfil.id).exists():
        messages.warning(request, 'Esta area ya tiene jerarquia asignada (supervisor/responsable). Evalua al lider correspondiente desde el panel gerencial.')
        return redirect('metricas_ceneris:panel_evaluacion_gerente')

    trabajadores = Trabajador.objects.filter(
        area=area,
        activo=True,
    ).filter(_q_trabajador_base())

    if not trabajadores.exists():
        messages.warning(request, 'El area seleccionada no tiene trabajadores activos para evaluar.')
        return redirect('metricas_ceneris:panel_evaluacion_gerente')

    total_evaluaciones_mes = 0
    promedios_area = []
    mejor_trabajador = None
    mejor_nota = -1
    promedios_por_categoria = {'OPERACIONAL': [], 'ADMINISTRATIVO': [], 'HABILIDADES': []}

    hoy = timezone.now().date()

    for t in trabajadores:
        evals = t.evaluaciones.all()
        ultima_ev = evals.first()

        estado_eval = _estado_evaluacion_para_fecha(t, hoy)
        t.es_nuevo = estado_eval['es_nuevo']
        t.hito_tipo = estado_eval['hito_tipo']
        t.btn_hito_activo = estado_eval['btn_hito_activo']
        t.btn_mensual_activo = estado_eval['btn_mensual_activo']
        t.en_periodo_prueba = estado_eval['en_periodo_prueba']

        if ultima_ev:
            t.ultima_nota = ultima_ev.promedio_final
            promedios_area.append(t.ultima_nota)
            total_evaluaciones_mes += 1

            if t.ultima_nota > mejor_nota:
                mejor_nota = t.ultima_nota
                mejor_trabajador = t

            for cat in ['OPERACIONAL', 'ADMINISTRATIVO', 'HABILIDADES']:
                avg_cat = ultima_ev.puntajes.filter(categoria=cat).aggregate(Avg('nota'))['nota__avg']
                if avg_cat:
                    promedios_por_categoria[cat].append(avg_cat)
        else:
            t.ultima_nota = 0

    promedio_area_total = round(sum(promedios_area) / len(promedios_area), 1) if promedios_area else 0

    radar_data = []
    for cat in ['OPERACIONAL', 'ADMINISTRATIVO', 'HABILIDADES']:
        lista = promedios_por_categoria[cat]
        promedio = round(sum(lista) / len(lista), 1) if lista else 0
        radar_data.append(promedio)

    return render(request, 'metricas_ceneris/evaluaciones/panel_jefe.html', {
        'area': area,
        'trabajadores': trabajadores,
        'promedio_area': promedio_area_total,
        'total_evaluaciones': total_evaluaciones_mes,
        'mejor_trabajador': mejor_trabajador,
        'radar_data': radar_data,
        'modo_gerencia_directa': True,
        'tarjetas_areas': [],
    })


@login_required
def ajax_datos_ranking(request):
    try:
        usuario = request.user.trabajador
        if not _es_gerente_puro(usuario):
            return JsonResponse({'error': 'No autorizado'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=403)

    hoy = timezone.now().date()
    filtro_periodo = _resolver_filtro_periodo_request(request, hoy, periodo_default='semestre')
    periodo = filtro_periodo['periodo']
    anio = filtro_periodo['anio']
    mes = filtro_periodo['mes']
    semestre = filtro_periodo['semestre']

    parametros_periodo = {'anio': anio}
    if periodo == 'mes':
        parametros_periodo['mes'] = mes
    else:
        parametros_periodo['semestre'] = semestre

    fecha_ref_periodo = _fecha_referencia_periodo(hoy, periodo, **parametros_periodo)

    todos_trabajadores = Trabajador.objects.filter(activo=True).select_related('area', 'sede')
    ranking = []

    for t in todos_trabajadores:
        if _es_gerente_puro(t):
            continue
        if _esta_en_periodo_prueba(t, fecha_ref_periodo):
            continue

        datos = _calcular_score_total(t, hoy, periodo, **parametros_periodo)
        puntaje_final = datos['score_total']

        if puntaje_final <= 0:
            continue

        item = {
            'trabajador': t,
            'score': round(puntaje_final, 2),
            'promedio_mensual': round(datos['promedio_mensual'], 2),
            'promedio_semestral': round(datos['promedio_semestral'], 2),
            'asistencia_avg': round(datos['asistencia_pct'] / 10, 1),
            'promedio_mensual_porc': round(datos['promedio_mensual'] * 10, 1),
            'promedio_semestral_porc': round(datos['promedio_semestral'] * 10, 1),
            'area_nombre': t.area.nombre if t.area else 'Sin Area',
        }

        if _es_trabajador_base(t):
            tipo_persona = 'trabajador'
        elif _es_supervisor(t):
            tipo_persona = 'supervisor'
        elif _es_responsable(t):
            tipo_persona = 'responsable'
        else:
            continue

        ranking.append(_serializar_item_ranking_tabla(item, tipo_persona))

    ranking.sort(key=lambda x: x['score'], reverse=True)

    return JsonResponse({
        'ranking': ranking,
        'periodo': periodo,
        'anio': anio,
        'mes': mes,
        'semestre': semestre,
    })


@login_required
def ajax_datos_grafico_areas(request):
    try:
        usuario = request.user.trabajador
        if not _es_gerente_puro(usuario):
            return JsonResponse({'error': 'No autorizado'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=403)

    hoy = timezone.now().date()

    sede_id = request.GET.get('sede', 'todas')
    filtro_periodo = _resolver_filtro_periodo_request(request, hoy, periodo_default='semestre')
    periodo = filtro_periodo['periodo']
    anio = filtro_periodo['anio']
    mes = filtro_periodo['mes']
    semestre = filtro_periodo['semestre']

    parametros_periodo = {'anio': anio}
    if periodo == 'mes':
        parametros_periodo['mes'] = mes
    else:
        parametros_periodo['semestre'] = semestre

    todos_trabajadores = Trabajador.objects.filter(activo=True).select_related('area', 'sede')
    if sede_id != 'todas' and sede_id:
        try:
            todos_trabajadores = todos_trabajadores.filter(sede_id=int(sede_id))
        except ValueError:
            pass

    scores_por_area = {}

    for t in todos_trabajadores:
        if not t.area:
            continue

        datos_score = _calcular_score_total(t, hoy, periodo, **parametros_periodo)
        puntaje_final = datos_score['score_total']

        if puntaje_final > 0:
            if t.area.nombre not in scores_por_area:
                scores_por_area[t.area.nombre] = []
            scores_por_area[t.area.nombre].append(puntaje_final)

    lista_areas = []
    for nombre_area, puntajes in scores_por_area.items():
        promedio = sum(puntajes) / len(puntajes)
        lista_areas.append({
            'nombre': nombre_area,
            'promedio': round(promedio, 2),
        })

    lista_areas.sort(key=lambda x: x['promedio'], reverse=True)

    labels = [item['nombre'] for item in lista_areas]
    data = [item['promedio'] for item in lista_areas]

    return JsonResponse({
        'labels': labels,
        'data': data,
        'periodo': periodo,
        'anio': anio,
        'mes': mes,
        'semestre': semestre,
    })


@login_required
def ajax_datos_podio(request):
    try:
        usuario = request.user.trabajador
        if not _es_gerente_puro(usuario):
            return JsonResponse({'error': 'No autorizado'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=403)

    hoy = timezone.now().date()

    sede_id = request.GET.get('sede', 'todas')
    categoria = request.GET.get('categoria', 'trabajadores')
    if categoria in ['jefes', 'supervisores']:
        categoria = 'lideres'
    if categoria not in ['trabajadores', 'lideres']:
        categoria = 'trabajadores'

    filtro_periodo = _resolver_filtro_periodo_request(request, hoy, periodo_default='semestre')
    periodo = filtro_periodo['periodo']
    anio = filtro_periodo['anio']
    mes = filtro_periodo['mes']
    semestre = filtro_periodo['semestre']

    parametros_periodo = {'anio': anio}
    if periodo == 'mes':
        parametros_periodo['mes'] = mes
    else:
        parametros_periodo['semestre'] = semestre

    fecha_ref_periodo = _fecha_referencia_periodo(hoy, periodo, **parametros_periodo)

    todos_trabajadores = Trabajador.objects.filter(activo=True).select_related('area', 'sede')
    if sede_id != 'todas' and sede_id:
        try:
            todos_trabajadores = todos_trabajadores.filter(sede_id=int(sede_id))
        except ValueError:
            pass

    if categoria == 'trabajadores':
        todos_trabajadores = todos_trabajadores.filter(_q_trabajador_base())
    else:
        todos_trabajadores = todos_trabajadores.filter(_q_supervisor() | _q_responsable())

    ranking = []

    for t in todos_trabajadores:
        if categoria == 'trabajadores' and not _es_trabajador_base(t):
            continue
        if categoria == 'lideres' and not (_es_supervisor(t) or _es_responsable(t)):
            continue

        if _esta_en_periodo_prueba(t, fecha_ref_periodo):
            continue

        datos_score = _calcular_score_total(t, hoy, periodo, **parametros_periodo)
        puntaje_final = datos_score['score_total']
        promedio_eval = datos_score['desempeno_compuesto']
        promedio_mensual = datos_score['promedio_mensual']
        promedio_semestral = datos_score['promedio_semestral']
        porc_asistencia = datos_score['asistencia_pct']

        if puntaje_final > 0:
            apellidos = f"{(t.apellido_paterno or '').strip()} {(t.apellido_materno or '').strip()}".strip()
            ranking.append({
                'id': t.id,
                'nombres': t.nombres,
                'apellidos': apellidos,
                'iniciales': t.nombres[:2].upper() if t.nombres else '',
                'nombre_corto': t.nombres[:8] if t.nombres else '',
                'nombre_completo_corto': t.nombres[:10] if t.nombres else '',
                'score': round(puntaje_final, 2),
                'eval_avg': round(promedio_eval, 2),
                'promedio_mensual': round(promedio_mensual, 2),
                'promedio_semestral': round(promedio_semestral, 2),
                'asistencia_avg': round(porc_asistencia / 10, 1),
                'area_nombre': t.area.nombre if t.area else 'Sin Area',
                'tipo_lider': 'Responsable' if _es_responsable(t) else ('Supervisor' if _es_supervisor(t) else 'Trabajador'),
            })

    ranking.sort(key=lambda x: x['score'], reverse=True)
    podio = ranking[:3]

    return JsonResponse({
        'podio': podio,
        'periodo': periodo,
        'anio': anio,
        'mes': mes,
        'semestre': semestre,
    })


@login_required
def ajax_datos_area_lider(request):
    try:
        usuario = request.user.trabajador
        if not _es_gerente_puro(usuario):
            return JsonResponse({'error': 'No autorizado'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=403)

    hoy = timezone.now().date()

    sede_id = request.GET.get('sede', 'todas')
    filtro_periodo = _resolver_filtro_periodo_request(request, hoy, periodo_default='semestre')
    periodo = filtro_periodo['periodo']
    anio = filtro_periodo['anio']
    mes = filtro_periodo['mes']
    semestre = filtro_periodo['semestre']

    parametros_periodo = {'anio': anio}
    if periodo == 'mes':
        parametros_periodo['mes'] = mes
    else:
        parametros_periodo['semestre'] = semestre

    todos_trabajadores = Trabajador.objects.filter(activo=True).select_related('area', 'sede')
    if sede_id != 'todas' and sede_id:
        try:
            todos_trabajadores = todos_trabajadores.filter(sede_id=int(sede_id))
        except ValueError:
            pass

    scores_por_area_semestre = {}

    for t in todos_trabajadores:
        if not t.area:
            continue

        puntaje_semestre = _calcular_score_total(t, hoy, periodo, **parametros_periodo)['score_total']

        if puntaje_semestre > 0:
            if t.area.nombre not in scores_por_area_semestre:
                scores_por_area_semestre[t.area.nombre] = []
            scores_por_area_semestre[t.area.nombre].append(puntaje_semestre)

    mejor_area = None
    if scores_por_area_semestre:
        lista_semestre = []
        for nombre, puntajes in scores_por_area_semestre.items():
            promedio = sum(puntajes) / len(puntajes)
            lista_semestre.append({'nombre': nombre, 'promedio': round(promedio, 2)})
        lista_semestre.sort(key=lambda x: x['promedio'], reverse=True)
        mejor_area = lista_semestre[0]

    return JsonResponse({
        'mejor_area': mejor_area,
        'periodo': periodo,
        'anio': anio,
        'mes': mes,
        'semestre': semestre,
    })
