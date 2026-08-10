"""Vistas de dashboards e indices generales.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import json

from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from cenerisapp.models import (
    Alarma,
    AreaTrabajo,
    Certificado,
    Dispositivo,
    Mantenimiento,
    Modificacion,
    OtroComponente,
    Registro,
    Sensor,
)


@login_required
def inicio(request):
    return render(request, 'inicio_supervisor/inicio.html')


@never_cache
@login_required 
def home(request):
    return render(request, 'index.html')


@login_required
def dashboard_portatiles(request):
    
    # --- PARTE 1: DATOS GENERALES PARA EL DASHBOARD ---
    # (Se calculan siempre, se busque o no un dispositivo)
    
    portatiles_qs = Dispositivo.objects.filter(tipoDisp='Portatil')
    
    # 1.1 Conteo total
    total_portatiles = portatiles_qs.count()
    
    # 1.2 Gráfico de estados
    conteo_por_estado = portatiles_qs.values('estadoD').annotate(total=Count('estadoD')).order_by('-total')
    
    # 1.3 Gráfico de modificaciones por mes (últimos 6 meses)
    modificaciones_por_mes = Modificacion.objects.filter(id_dispositivo__tipoDisp='Portatil') \
        .annotate(mes=TruncMonth('fecInstalacionMod')) \
        .values('mes') \
        .annotate(total=Count('id_modificacion')) \
        .order_by('mes')[:6] # Solo los últimos 6 meses
    
    # 1.4 Dispositivos que NUNCA han sido revisados en Cardex
    pendientes_cardex = portatiles_qs.filter(cardex_revisado=False).count()

    ultimos_mantenimientos = Mantenimiento.objects.filter(
        dispositivo__tipoDisp='Portatil'
    ).select_related('dispositivo', 'tecnico_a_cargo').order_by('-fecha_intervencion')[:4]

    # 1.6 Últimas 7 modificaciones realizadas a portátiles
    ultimas_modificaciones = Modificacion.objects.filter(
        id_dispositivo__tipoDisp='Portatil'
    ).select_related(
        'id_dispositivo', 
        'id_trabajador',
        'parte_saliente',
        'sensor_saliente',
        'componente_entrante'
    ).order_by('-fecInstalacionMod')[:4]

    # --- PARTE 2: BÚSQUEDA Y DATOS ESPECÍFICOS DE UN DISPOSITIVO ---
    
    dispositivo_seleccionado = None
    ultimo_mantenimiento = None
    ultima_modificacion = None
    registros_recientes = None
    certificados_recientes = None
    
    # Obtenemos el ID del dispositivo de la URL (?dispositivo_id=...)
    query_busqueda = request.GET.get('query', '')
    
    if query_busqueda:
        try:
            # prefetch_related es crucial para optimizar y evitar muchas consultas a la BD
            dispositivo_seleccionado = Dispositivo.objects.prefetch_related(
                'mantenimientos__tecnico_a_cargo', 
                'modificacion_set__parte_saliente', 
                'modificacion_set__sensor_saliente', 
                'modificacion_set__componente_entrante',
                'certificados',
                'registro_set__trabajador_receptor'
            ).get(num_serie=query_busqueda, tipoDisp='Portatil')

            # Obtenemos los últimos registros relacionados con este dispositivo
            ultimo_mantenimiento = dispositivo_seleccionado.mantenimientos.first() # Usamos el ordering del modelo
            ultima_modificacion = dispositivo_seleccionado.modificacion_set.first()
            registros_recientes = dispositivo_seleccionado.registro_set.all().order_by('-fecRegistro')[:5]
            certificados_recientes = dispositivo_seleccionado.certificados.all().order_by('-fechCertificado')[:5]
            
        except Dispositivo.DoesNotExist:
            messages.error(request, "El dispositivo portátil seleccionado no existe.")

    # --- PARTE 3: CONTEXTO PARA LA PLANTILLA ---
    
    context = {
        'titulo': 'Dashboard de Dispositivos Portátiles',
        
        # Datos Generales
        'total_portatiles': total_portatiles,
        'conteo_por_estado_json': json.dumps(list(conteo_por_estado)), # Para Chart.js
        'modificaciones_por_mes_json': json.dumps([
            {'mes': m['mes'].strftime('%b %Y'), 'total': m['total']} for m in modificaciones_por_mes
        ]), # Para Chart.js
        'pendientes_cardex': pendientes_cardex,
        'todos_los_portatiles_para_busqueda': portatiles_qs, # Para el <select> de búsqueda

        # Datos Específicos del Dispositivo
        'dispositivo_seleccionado': dispositivo_seleccionado,
        'query_busqueda': query_busqueda, # Para que el <select> recuerde la selección
        'ultimo_mantenimiento': ultimo_mantenimiento,
        'ultima_modificacion': ultima_modificacion,
        'registros_recientes': registros_recientes,
        'certificados_recientes': certificados_recientes,
        'ultimos_mantenimientos': ultimos_mantenimientos,
        'ultimas_modificaciones': ultimas_modificaciones,
    }
    
    return render(request, 'dashboard/dashboard_portatiles.html', context)


@login_required
def dashboard_garantias(request):
    
    # --- 1. Definir los rangos de fechas ---
    today = date.today()
    # "Muy cerca a vencer" es dentro de los próximos 30 días
    un_mes_desde_hoy = today + timedelta(days=30)

    # --- 2. Capturar el filtro de búsqueda (si existe) ---
    query = request.GET.get('q', '')

    # --- 3. Realizar las consultas para Dispositivos ---
    base_dispositivos_qs = Dispositivo.objects.all()
    if query:
        base_dispositivos_qs = base_dispositivos_qs.filter(num_serie__icontains=query)

    # --- 4. Realizar las consultas para Sensores ---
    base_sensores_qs = Sensor.objects.select_related('dispositivo_instalado')
    if query:
        base_sensores_qs = base_sensores_qs.filter(nSerieActual__icontains=query)
    
    # 1. VENCIDAS
    vencidas_dispositivos = base_dispositivos_qs.filter(fecVencimientoGarantia__lt=today).order_by('fecVencimientoGarantia')
    vencidas_sensores = base_sensores_qs.filter(fecVencGarantia__lt=today).exclude(fecVencGarantia__isnull=True).order_by('fecVencGarantia')
    vencidas_items = sorted(
        list(vencidas_dispositivos) + list(vencidas_sensores), 
        key=lambda x: getattr(x, 'fecVencimientoGarantia', None) or getattr(x, 'fecVencGarantia', None)
    )
    vencidas_paginator = Paginator(vencidas_items, 10) # 10 items por página
    vencidas_page_number = request.GET.get('page_vencidas')
    vencidas_page_obj = vencidas_paginator.get_page(vencidas_page_number)
    
    # 2. PRÓXIMAS A VENCER
    proximas_dispositivos = base_dispositivos_qs.filter(fecVencimientoGarantia__range=[today, un_mes_desde_hoy]).order_by('fecVencimientoGarantia')
    proximas_sensores = base_sensores_qs.filter(fecVencGarantia__range=[today, un_mes_desde_hoy]).exclude(fecVencGarantia__isnull=True).order_by('fecVencGarantia')
    proximas_items = sorted(
        list(proximas_dispositivos) + list(proximas_sensores), 
        key=lambda x: getattr(x, 'fecVencimientoGarantia', None) or getattr(x, 'fecVencGarantia', None)
    )
    proximas_paginator = Paginator(proximas_items, 10)
    proximas_page_number = request.GET.get('page_proximas')
    proximas_page_obj = proximas_paginator.get_page(proximas_page_number)

    # 3. VIGENTES
    vigentes_dispositivos = base_dispositivos_qs.filter(fecVencimientoGarantia__gt=un_mes_desde_hoy).order_by('fecVencimientoGarantia')
    vigentes_sensores = base_sensores_qs.filter(fecVencGarantia__gt=un_mes_desde_hoy).exclude(fecVencGarantia__isnull=True).order_by('fecVencGarantia')
    vigentes_items = sorted(
        list(vigentes_dispositivos) + list(vigentes_sensores), 
        key=lambda x: getattr(x, 'fecVencimientoGarantia', None) or getattr(x, 'fecVencGarantia', None)
    )
    vigentes_paginator = Paginator(vigentes_items, 10)
    vigentes_page_number = request.GET.get('page_vigentes')
    vigentes_page_obj = vigentes_paginator.get_page(vigentes_page_number)

    # --- 5. Preparar el contexto para la plantilla ---
    context = {
        'titulo': 'Dashboard de Garantías',
        'query': query,
        
        # Listas de ítems
        'vencidas_page_obj': vencidas_page_obj,
        'proximas_page_obj': proximas_page_obj,
        'vigentes_page_obj': vigentes_page_obj,
        
        # Conteos para las tarjetas principales
        'total_vencidas': vencidas_dispositivos.count() + vencidas_sensores.count(),
        'total_proximas': proximas_dispositivos.count() + proximas_sensores.count(),
        'total_vigentes': vigentes_dispositivos.count() + vigentes_sensores.count(),
        
        # Fecha límite para la categoría "próximas a vencer"
        'fecha_limite_proximas': un_mes_desde_hoy,
    }

    return render(request, 'garantias/dashboard_garantias.html', context)


@login_required
def vista_reporte_fijos(request):
    
    # 1. PREPARAR LOS HEADERS PARA LA PLANTILLA (igual que en el Excel)
    
    # Super-headers para las celdas combinadas
    super_headers = {
        'FECHA DE VENCIMIENTO DEL SENSOR ACTUAL': 2, # Ocupará 2 columnas
        'CALIBRACIÓN ENCONTRADA': 2,                 # Ocupará 2 columnas
        'ALARMAS': 3,                                # Ocupará 3 columnas
        'VALOR SPAM': 3                              # Ocupará 3 columnas
    }

    # Headers principales de cada columna
    headers = [
        'N°', 'NOMBRE DEL DISPOSITIVO', 'MODELO DE SENSOR', 'ÁREA', 'UBICACIÓN EN ÁREA', 'TAG',
        'UBICACIÓN DEL SENSOR EN EL DETECTOR', 'TIPO DE GAS', 
        # Columnas de CALIBRACIÓN ENCONTRADA
        'INFORME', 'ENCONTRADO EN CALIBRACIÓN', 'SENSOR CAMBIADO', 
        # Columnas de FECHA DE VENCIMIENTO
        'MES', 'AÑO',
        # Columnas adicionales de Informe
        'FECHA', 'REALIZADA POR',
        # Columnas de ALARMAS
        '1RA', '2DA', '3RA', 
        # Columnas de VALOR SPAM (ajusta los nombres si son diferentes)
        'EQUIPO', 'CILINDRO', 'UND', 
        # Columnas finales
        'OBSERVACION', 'ESTADO DE CALIBRACIÓN', 'NRO DE CERTIFICADO', 'FECHA DE CALIBRACIÓN POR CENERIS',
    ]

    # --- 1. CAPTURAR VALORES DE FILTRO DE LA URL (request.GET) ---
    busqueda_texto = request.GET.get('q', '')
    area_filtro = request.GET.get('area', '')
    estado_cal_filtro = request.GET.get('estado_cal', '')
    sensor_cambiado_filtro = request.GET.get('sensor_cambiado', '')
    vencimiento_desde = request.GET.get('venc_desde', '')
    vencimiento_hasta = request.GET.get('venc_hasta', '')
    
    # --- 2. CONSTRUIR EL QUERYSET BASE Y APLICAR FILTROS ---
    dispositivos_fijos = Dispositivo.objects.filter(tipoDisp='Fijo').select_related(
        'id_areaTrabajo_fijo'
    ).prefetch_related(
        'sensor_set__certificados_de_componente',
        'sensor_set__informes_calibracion__empresa_realizadora',
        'sensor_set__alarmas',
    ).order_by('nomDisp')

    # Aplicar filtros de texto (Nombre, TAG, Modelo de Sensor)
    if busqueda_texto:
        dispositivos_fijos = dispositivos_fijos.filter(
            Q(nomDisp__icontains=busqueda_texto) |
            Q(tag__icontains=busqueda_texto) |
            Q(sensor__nomComp__icontains=busqueda_texto)
        ).distinct() # .distinct() es importante cuando usamos Q en relaciones

    # Aplicar filtro por Área
    if area_filtro:
        # Asumo que 'area_filtro' contiene el PK de AreaTrabajo
        dispositivos_fijos = dispositivos_fijos.filter(id_areaTrabajo_fijo__pk=area_filtro)
    
    # Aplicar filtro por rango de fecha de vencimiento de garantía del sensor
    if vencimiento_desde:
        dispositivos_fijos = dispositivos_fijos.filter(sensor__fecVencGarantia__gte=vencimiento_desde)
    if vencimiento_hasta:
        dispositivos_fijos = dispositivos_fijos.filter(sensor__fecVencGarantia__lte=vencimiento_hasta)

    paginator = Paginator(dispositivos_fijos, 10) # 15 dispositivos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # --- 3. PROCESAR DATOS PARA LA PLANTILLA (AHORA DESPUÉS DE FILTRAR) ---
    datos_tabla = []
    
    for idx, dispositivo in enumerate(page_obj, start=page_obj.start_index()):
        sensores_del_dispositivo = dispositivo.sensor_set.all()
        
        
        lista_datos_sensores = []
        
        if sensores_del_dispositivo:
            # Si el dispositivo tiene sensores, iteramos sobre ellos
            for sensor in sensores_del_dispositivo:
                ultimo_certificado = sensor.certificados_de_componente.order_by('-fechCertificado').first()
                ultimo_informe = sensor.informes_calibracion.order_by('-fecha_informe').first()
                alarma = sensor.alarmas.first()
                # --- Lógica de Estado de Calibración ---
                estado_calibracion = 'No Calibrado'
                # Asumiendo 6 meses = 183 días para "Calibrado"
                if ultimo_certificado and timezone.now() - ultimo_certificado.fechCertificado <= timedelta(days=183):
                    estado_calibracion = 'Calibrado'
                
                alarma = None
                try:
                    # Hacemos una búsqueda explícita.
                    # Esto es más claro que usar el related_name.
                    alarma = Alarma.objects.get(sensor=sensor)
                    print(f"DEBUG: Alarma encontrada para el Sensor ID: {sensor.pk} ({sensor})")
                except Alarma.DoesNotExist:
                    # Es normal que un sensor no tenga alarma, no hacemos nada.
                    pass 
                except Alarma.MultipleObjectsReturned:
                    # ¡Esto es un problema de datos!
                    # Tienes múltiples alarmas para el mismo sensor.
                    self.stdout.write(self.style.WARNING(f"  - ADVERTENCIA: Se encontraron múltiples alarmas para el sensor {sensor}."))
                    # Tomamos la primera como fallback.
                    alarma = Alarma.objects.filter(sensor=sensor).first()

                # --- PRINT DE DEPURACIÓN ---
                if not alarma:
                    print(f"DEBUG: No se encontró alarma para el Sensor ID: {sensor.pk} ({sensor})")
                # --- FIN DEPURACIÓN ---

                datos_sensor = {
                    'modelo_sensor': sensor.nomComp,
                    'tipo_gas': sensor.tipGas,
                    'informe': ultimo_informe.informe if ultimo_informe else '',
                    'encontrado_calibracion': ultimo_informe.encontrado_calibracion if ultimo_informe else '',
                    'sensor_cambiado': "Sí" if ultimo_informe and ultimo_informe.sensor_cambiado else "No",
                    'mes_vencimiento': sensor.fecVencGarantia.strftime('%B').capitalize() if sensor.fecVencGarantia else '',
                    'anio_vencimiento': sensor.fecVencGarantia.year if sensor.fecVencGarantia else '',
                    'fecha_informe': ultimo_informe.fecha_informe.strftime('%d/%m/%Y') if ultimo_informe and ultimo_informe.fecha_informe else '',
                    'realizada_por': ultimo_informe.empresa_realizadora.nombreE if ultimo_informe and ultimo_informe.empresa_realizadora else '',
                    'observacion': ultimo_informe.observacion if ultimo_informe else '',
                    'estado_calibracion': estado_calibracion,
                    'nro_certificado': ultimo_certificado.nro_certificado if ultimo_certificado else '',
                    'fecha_calibracion_ceneris': ultimo_certificado.fechCertificado.date().strftime('%d/%m/%Y') if ultimo_certificado else '',
                    'alarma_1ra': alarma.primera if alarma else '',
                    'alarma_2da': alarma.segunda if alarma else '',
                    'alarma_3ra': alarma.tercera if alarma else '',
                    'valor_spam_equipo': alarma.equipo if alarma else '',
                    'valor_spam_cilindro': alarma.cilindro if alarma else '',
                    'valor_spam_und': alarma.und if alarma else '',
                }
                lista_datos_sensores.append(datos_sensor)
        else:
            # Si no hay sensores, añadimos una fila de datos vacía para que el dispositivo aparezca
            lista_datos_sensores.append({ 
                'modelo_sensor': 'Sin sensor registrado',
                'estado_calibracion': 'No Calibrado' # Default para filtrado
            })

        # --- FILTROS POST-PROCESAMIENTO (Aplicados a datos calculados en Python) ---
        
        # Filtro 'sensor_cambiado' (a nivel de dispositivo: ¿ALGÚN sensor fue cambiado?)
        #if sensor_cambiado_filtro:
            # Buscamos si ALGÚN informe de CALIBRACIÓN en CUALQUIERA de los sensores tuvo un cambio.
            #hubo_cambio = any(
                #(informe.sensor_cambiado for sensor in dispositivo.sensor_set.all() 
                 #for informe in sensor.informes_calibracion.all())
            #)
            # Convertimos el filtro a booleano (sensor_cambiado_filtro es 'Si' o 'No')
            #filtro_bool = sensor_cambiado_filtro == 'Si'
            #if hubo_cambio != filtro_bool:
                #continue # Saltamos todo el dispositivo si no cumple la condición

        # Filtro 'estado_calibracion' (a nivel de sensor)
        lista_datos_sensores_filtrada = []
        if lista_datos_sensores:
            for sensor_data in lista_datos_sensores:
                if estado_cal_filtro and sensor_data['estado_calibracion'] != estado_cal_filtro:
                    continue # Saltamos este sensor si no cumple con el filtro de estado
                lista_datos_sensores_filtrada.append(sensor_data)
        
        # Si después de filtrar no quedan sensores Y hay un filtro de sensor (para no saltar dispositivos sin filtro)
        # O si el dispositivo no tenía sensores y se está aplicando el filtro de estado de calibración.
        if not lista_datos_sensores_filtrada and (estado_cal_filtro or busqueda_texto):
             continue

        # Si pasamos los filtros, construimos y añadimos el diccionario principal
        num_sensores_final = len(lista_datos_sensores_filtrada) if lista_datos_sensores_filtrada else 1
        
        fila_dispositivo = {
            'numero': idx,
            'objeto_dispositivo': dispositivo,
            'num_sensores': num_sensores_final, # Cuántas filas ocupará
            'datos_comunes': {
                'nombre_dispositivo': dispositivo.nomDisp,
                # Asumo que tienes un campo 'area_general' o lo calculas
                'area': dispositivo.area_general if hasattr(dispositivo, 'area_general') else 'N/A', 
                'ubicacion_area': dispositivo.id_areaTrabajo_fijo.nombreA if dispositivo.id_areaTrabajo_fijo else '',
                'tag': dispositivo.tag,
                'ubicacion_sensor': '', # Este campo debe llenarse con la data de la ubicación del sensor en el detector
            },
            'datos_sensores': lista_datos_sensores_filtrada, # La lista de datos por sensor
        }
        
        # Re-indexamos si el filtro de estado_cal_filtro elimina todos los sensores de un dispositivo
        if fila_dispositivo['datos_sensores']:
            datos_tabla.append(fila_dispositivo)
    
    # --- 4. PREPARAR DATOS PARA LOS DESPLEGABLES DE FILTRO ---
    # Asumo que AreaTrabajo es un modelo disponible
    opciones_areas = AreaTrabajo.objects.all().order_by('nombreA')
    opciones_estado_cal = [('Calibrado', 'Calibrado'), ('No Calibrado', 'No Calibrado')]
    opciones_sensor_cambiado = [('Si', 'Sí'), ('No', 'No')] # Para el filtro booleano
    
    # --- 5. CONSTRUIR EL CONTEXTO FINAL ---
    context = {
        'titulo': 'Reporte de Dispositivos Fijos',
        'headers': headers,
        'super_headers': super_headers,
        'page_obj': page_obj,
        'datos_tabla': datos_tabla,
        'url_exportacion_excel': reverse('cenerisapp:exportar_fijos_excel'),
        
        # Datos para los filtros
        'opciones_areas': opciones_areas,
        'opciones_estado_cal': opciones_estado_cal,
        'opciones_sensor_cambiado': opciones_sensor_cambiado,
        'filtros_aplicados': {
            'q': busqueda_texto,
            'area': int(area_filtro) if area_filtro else None,
            'estado_cal': estado_cal_filtro,
            'sensor_cambiado': sensor_cambiado_filtro,
            'venc_desde': vencimiento_desde,
            'venc_hasta': vencimiento_hasta,
        }
    }
    
    return render(request, 'tabla/vista_reporte_fijos.html', context)


@login_required
def dashboard_fijos(request):
    
    # --- PARTE 1: DATOS GENERALES PARA EL DASHBOARD ---
    
    fijos_qs = Dispositivo.objects.filter(tipoDisp='Fijo')
    
    # 1.1 Conteo de dispositivos fijos
    total_fijos = fijos_qs.count()
    
    # 1.2 Conteo de sensores instalados en dispositivos fijos
    total_sensores_fijos = Sensor.objects.filter(dispositivo_instalado__tipoDisp='Fijo').count()
    
    # 1.3 Conteo de dispositivos "Calibrados"
    # Un dispositivo se considera calibrado si tiene al menos un sensor con un certificado de los últimos 6 meses.
    seis_meses_atras = timezone.now() - timedelta(days=183)
    dispositivos_calibrados_ids = Certificado.objects.filter(
        componente__sensor__dispositivo_instalado__tipoDisp='Fijo',
        fechCertificado__gte=seis_meses_atras
    ).values_list('componente__sensor__dispositivo_instalado_id', flat=True).distinct()
    total_calibrados = len(dispositivos_calibrados_ids)

    # 1.4 Últimos 5 sensores calibrados (basado en la fecha del certificado)
    ultimos_certificados = Certificado.objects.filter(componente__sensor__dispositivo_instalado__tipoDisp='Fijo') \
        .select_related('componente__sensor', 'componente__sensor__dispositivo_instalado') \
        .order_by('-fechCertificado')[:5]

    # 1.5 Gráfico de cantidad de fijos por área de trabajo
    dispositivos_por_area = fijos_qs.values('id_areaTrabajo_fijo__nombreA') \
        .annotate(total=Count('id_dispositivo')).order_by('-total')
    
    # --- PARTE 2: BÚSQUEDA Y DATOS ESPECÍFICOS ---
    dispositivo_seleccionado = None
    lista_certificados_ordenada = []
    query_busqueda = request.GET.get('query', '')
    
    if query_busqueda:
        try:
            dispositivo_seleccionado = Dispositivo.objects.prefetch_related(
                'sensor_set__certificados_de_componente'
            ).get(num_serie__iexact=query_busqueda, tipoDisp='Fijo')

            todos_los_certificados = []
            for sensor in dispositivo_seleccionado.sensor_set.all():
                for cert in sensor.certificados_de_componente.all():
                    # Añadimos el certificado y una referencia a su sensor padre
                    todos_los_certificados.append({'cert': cert, 'sensor': sensor})
            
            # Ordenamos la lista combinada por fecha, de más reciente a más antigua
            todos_los_certificados.sort(key=lambda x: x['cert'].fechCertificado, reverse=True)
            
            # Nos quedamos solo con los 5 más recientes
            lista_certificados_ordenada = todos_los_certificados[:5]

        except Dispositivo.DoesNotExist:
            messages.error(request, f"No se encontró ningún dispositivo fijo con el N° de Serie '{query_busqueda}'.")

    # --- PARTE 3: CONTEXTO PARA LA PLANTILLA ---
    context = {
        'titulo': 'Dashboard de Dispositivos Fijos',
        
        # Datos Generales
        'total_fijos': total_fijos,
        'total_sensores_fijos': total_sensores_fijos,
        'total_calibrados': total_calibrados,
        'ultimos_certificados': ultimos_certificados,
        'dispositivos_por_area_json': json.dumps([
            {'area': item['id_areaTrabajo_fijo__nombreA'] or 'Sin Área', 'total': item['total']}
            for item in dispositivos_por_area
        ]),
        
        # Datos para Búsqueda
        'todos_los_fijos_para_busqueda': fijos_qs,
        'query_busqueda': query_busqueda,
        'dispositivo_seleccionado': dispositivo_seleccionado,
        'lista_certificados_ordenada': lista_certificados_ordenada,
    }
    
    return render(request, 'dashboard/dashboard_fijos.html', context)


@login_required
def vista_inoperativos(request):
    
    # --- 1. CONSULTAS BASE ---
    dispositivos_inoperativos_qs = Dispositivo.objects.filter(estadoD__in=['Inoperativo', 'Extraviado']).order_by('nomDisp')
    sensores_inoperativos_qs = Sensor.objects.filter(estComp__in=['Inoperativo', 'Inoperativo por cambio']).order_by('nomComp')
    otros_componentes_inoperativos_qs = OtroComponente.objects.filter(estComp='Inoperativo').order_by('nomComp')

    # --- 2. PAGINACIÓN INDEPENDIENTE ---
    # Paginador para Dispositivos
    disp_paginator = Paginator(dispositivos_inoperativos_qs, 5) # 5 por página
    disp_page_number = request.GET.get('page_disp')
    disp_page_obj = disp_paginator.get_page(disp_page_number)

    # Paginador para Sensores
    sensor_paginator = Paginator(sensores_inoperativos_qs, 5)
    sensor_page_number = request.GET.get('page_sensor')
    sensor_page_obj = sensor_paginator.get_page(sensor_page_number)

    # Paginador para Otros Componentes
    otro_paginator = Paginator(otros_componentes_inoperativos_qs, 5)
    otro_page_number = request.GET.get('page_otro')
    otro_page_obj = otro_paginator.get_page(otro_page_number)

    # --- 3. CONTEXTO PARA LA PLANTILLA ---
    context = {
        'titulo': 'Dashboard de Ítems Inoperativos',
        
        # Objetos de Paginación para cada sección
        'disp_page_obj': disp_page_obj,
        'sensor_page_obj': sensor_page_obj,
        'otro_page_obj': otro_page_obj,
        
        # Conteos para las tarjetas KPI (usamos los querysets completos, es eficiente)
        'total_dispositivos_inop': dispositivos_inoperativos_qs.count(),
        'total_sensores_inop': sensores_inoperativos_qs.count(),
        'total_otros_inop': otros_componentes_inoperativos_qs.count(),
    }
    return render(request, 'inoperativos/inoperativos.html', context)


@login_required
def vista_tabla_portatiles(request):
    base_query = Dispositivo.objects.filter(tipoDisp='Portatil')
    
    opciones_modelos = base_query.values_list('nomDisp', flat=True).distinct().order_by('nomDisp')
    opciones_estados = base_query.values_list('estadoD', flat=True).distinct().order_by('estadoD')
    opciones_areas = base_query.exclude(area_general__isnull=True).exclude(area_general__exact='')\
                               .values_list('area_general', flat=True).distinct().order_by('area_general')

    # Opciones para los nuevos filtros (no necesitan consulta a la BD)
    opciones_garantia = [('Vigente', 'Vigente'), ('Caducado', 'Caducado')]
    opciones_observaciones = [('Con', 'Con Observaciones'), ('Sin', 'Sin Observaciones')]

    opciones_tipo_gas = Sensor.objects.filter(dispositivo_instalado__tipoDisp='Portatil')\
                                    .values_list('tipGas', flat=True).distinct().order_by('tipGas')
    opciones_estado_sensor = Sensor.objects.filter(dispositivo_instalado__tipoDisp='Portatil')\
                                       .values_list('estComp', flat=True).distinct().order_by('estComp')
    opciones_garantia_sensor = [('Vigente', 'Vigente'), ('Caducado', 'Caducado')]

    # ========================================================================
    # 2. CAPTURAR TODOS LOS VALORES DE FILTRO DE LA URL (request.GET)
    # ========================================================================
    modelo_filtro = request.GET.get('modelo', '')
    serie_filtro = request.GET.get('serie', '')
    estado_filtro = request.GET.get('estado', '')
    area_filtro = request.GET.get('area', '')
    fecha_desde_filtro = request.GET.get('fecha_desde', '')
    fecha_hasta_filtro = request.GET.get('fecha_hasta', '')
    ingreso_desde_filtro = request.GET.get('ingreso_desde', '')
    ingreso_hasta_filtro = request.GET.get('ingreso_hasta', '')
    
    # --- FECHA DE VENCIMIENTO DE GARANTÍA (RANGO) ---
    vencimiento_desde_filtro = request.GET.get('vencimiento_desde', '')
    vencimiento_hasta_filtro = request.GET.get('vencimiento_hasta', '')

    # Nuevos filtros
    modificacion_desde_filtro = request.GET.get('modificacion_desde', '')
    mantenimiento_desde_filtro = request.GET.get('mantenimiento_desde', '')
    garantia_filtro = request.GET.get('garantia', '')
    irreparable_desde_filtro = request.GET.get('irreparable_desde', '')
    inoperativo_desde_filtro = request.GET.get('inoperativo_desde', '')
    observaciones_filtro = request.GET.get('observaciones', '')

    sensor_gas_filtro = request.GET.get('sensor_gas', '')
    sensor_serie_filtro = request.GET.get('sensor_serie', '')
    sensor_estado_filtro = request.GET.get('sensor_estado', '')
    sensor_instalacion_desde_filtro = request.GET.get('sensor_instalacion_desde', '')
    sensor_instalacion_hasta_filtro = request.GET.get('sensor_instalacion_hasta', '')
    sensor_garantia_filtro = request.GET.get('sensor_garantia', '')

    # ========================================================================
    # 3. CONSTRUIR EL QUERYSET BASE Y APLICAR FILTROS
    # ========================================================================
    dispositivos_portatiles = Dispositivo.objects.filter(tipoDisp='Portatil').select_related(
        'id_areaTrabajo_fijo'
    ).prefetch_related(
        'sensor_set',
        'modificacion_set__id_trabajador',
        'modificacion_set__sensor_saliente',
        'modificacion_set__componente_entrante',
        'partes',
        'mantenimientos__tecnico_a_cargo',
        'observaciones'
    ).order_by('id_dispositivo')
    
    # Bandera para saber si necesitamos usar .distinct() al final
    needs_distinct = False

    # Filtros existentes (con 'modelo' actualizado)
    if modelo_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(nomDisp=modelo_filtro)
    if serie_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(num_serie__icontains=serie_filtro)
    if estado_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(estadoD=estado_filtro)
    if area_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(area_general=area_filtro)
    if fecha_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecIngreso__gte=fecha_desde_filtro)
    if fecha_hasta_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecIngreso__lte=fecha_hasta_filtro)

    # --- LÓGICA DE FILTRADO PARA FECHA DE INGRESO ---
    if ingreso_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecIngreso__gte=ingreso_desde_filtro)
    if ingreso_hasta_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecIngreso__lte=ingreso_hasta_filtro)
        
    # --- LÓGICA DE FILTRADO PARA VENCIMIENTO DE GARANTÍA ---
    if vencimiento_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecVencimientoGarantia__gte=vencimiento_desde_filtro)
    if vencimiento_hasta_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fecVencimientoGarantia__lte=vencimiento_hasta_filtro)
        
    # --- APLICACIÓN DE NUEVOS FILTROS ---
    if modificacion_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(modificacion__fecInstalacionMod__gte=modificacion_desde_filtro)
        needs_distinct = True
    if mantenimiento_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(mantenimientos__fecha_intervencion__gte=mantenimiento_desde_filtro)
        needs_distinct = True
    if irreparable_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fec_irreparable__gte=irreparable_desde_filtro)
    if inoperativo_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(fec_inoperativo__gte=inoperativo_desde_filtro)
        
    # Filtro de Estatus de Garantía (lógica especial)
    if garantia_filtro:
        hoy = date.today()
        if garantia_filtro == 'Vigente':
            dispositivos_portatiles = dispositivos_portatiles.filter(fecVencimientoGarantia__gte=hoy)
        elif garantia_filtro == 'Caducado':
            dispositivos_portatiles = dispositivos_portatiles.filter(fecVencimientoGarantia__lt=hoy)
            
    # Filtro por existencia de observaciones
    if observaciones_filtro:
        if observaciones_filtro == 'Con':
            dispositivos_portatiles = dispositivos_portatiles.filter(observaciones__isnull=False)
            needs_distinct = True
        elif observaciones_filtro == 'Sin':
            dispositivos_portatiles = dispositivos_portatiles.filter(observaciones__isnull=True)

    if sensor_gas_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(sensor__tipGas=sensor_gas_filtro)
        needs_distinct = True
    if sensor_serie_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(sensor__nSerieActual__icontains=sensor_serie_filtro)
        needs_distinct = True
    if sensor_estado_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(sensor__estComp=sensor_estado_filtro)
        needs_distinct = True
    if sensor_instalacion_desde_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(sensor__fecInst__gte=sensor_instalacion_desde_filtro)
        needs_distinct = True
    if sensor_instalacion_hasta_filtro:
        dispositivos_portatiles = dispositivos_portatiles.filter(sensor__fecInst__lte=sensor_instalacion_hasta_filtro)
        needs_distinct = True
        
    # Filtro de Estatus de Garantía del Sensor (lógica especial)
    if sensor_garantia_filtro:
        hoy = date.today()
        if sensor_garantia_filtro == 'Vigente':
            dispositivos_portatiles = dispositivos_portatiles.filter(sensor__fecVencGarantia__gte=hoy)
        elif sensor_garantia_filtro == 'Caducado':
            dispositivos_portatiles = dispositivos_portatiles.filter(sensor__fecVencGarantia__lt=hoy)
        needs_distinct = True
            
    # Aplicamos distinct() solo si es necesario para evitar duplicados por los joins
    if needs_distinct:
        dispositivos_portatiles = dispositivos_portatiles.distinct()

    paginator = Paginator(dispositivos_portatiles, 10) # 15 dispositivos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ----------------- El resto de la lógica de la vista permanece igual -----------------

    sensores_unicos_qs = Sensor.objects.filter(dispositivo_instalado__in=dispositivos_portatiles)\
                                      .values('tipGas', 'nomComp')\
                                      .distinct()
    
    ORDEN_SENSORES = ['LEL', 'O2', 'DUAL', 'SO2', 'CO2', 'NH3', 'CL2', 'HCN']
    
    tipos_presentes = [s['tipGas'] for s in sensores_unicos_qs if s['tipGas']]
    tipos_de_sensor_unicos = [tipo for tipo in ORDEN_SENSORES if tipo in tipos_presentes]

    SENSOR_HEADER_CONFIG = {
        sensor_data.get('tipGas'): f"SENSOR {sensor_data.get('tipGas')}"
        for sensor_data in sensores_unicos_qs
    }

    CAMPOS_POR_SENSOR_DETALLES = [
        'Nº DE SERIE ANTERIOR', 'Nº DE SERIE ACTUAL', 'FECHA DE FABRICACIÓN', 'FECHA DE INSTALACIÓN',
        'RESPONSABLE DEL CAMBIO', 'NÚMERO DE GUÍA DE INGRESO', 'ITEM DE GÚIA',
        'VENCIMIENTO DE GARANTIA', 'ESTATUS DE GARANTIA', 'ESTATUS DEL SENSOR'
    ]
    
    hoy = date.today()

    headers_fijos_inicio = [
        'N°', 'MODELO', 'NÚMERO SERIE', 'Fecha de Fabricación', 'Fecha de ingreso',
        'Fecha de vencimiento de garantía', 'NS', 'CÓDIGO DEL EQUIPO', 'Última fecha de Mantto',
        'Responsable de Mantto', 'SENSOR', 'UBICACIÓN DEL EQUIPO', 'OBSERVACION',
        'ESTATUS GARANTÍA DEL EQUIPO'
    ]
    headers_dinamicos_estatus = tipos_de_sensor_unicos
    headers_fijos_finales = [
        'Número de Guía', 'OBSERVACION POR FALTA DE MANTENIMIENTO INDICADO POR MSA',
        'FECHA QUE PASA A IRREPARABLE', 'FECHA QUE PASA A INOPEATIVO', 'ESTADO DEL EQUIPO',
        'PROPIEDAD DEL EQUIPO', 'FECHA DE ULTIMA MODIFICACIÓN'
    ]
    headers_dinamicos_detalles_flat = []
    for tipo in tipos_de_sensor_unicos:
        headers_dinamicos_detalles_flat.extend([f'{campo} {tipo}' for campo in CAMPOS_POR_SENSOR_DETALLES])

    headers_fijos_finales_finales = ['PLACA ELECTRÓNICA - FECHA FABRICACIÓN', 'SENSOR CANIBALIZADO',
        'PCBA', 'CARCASA', 'CLIP', 'CARDEX']
        
    headers_completos = headers_fijos_inicio + headers_dinamicos_estatus + headers_fijos_finales + headers_dinamicos_detalles_flat + headers_fijos_finales_finales

    # ========================================================================
    # OPTIMIZACIÓN: Cachear consultas fuera del loop
    # ========================================================================
    dispositivos_ids = [d.id_dispositivo for d in page_obj]
    
    # Pre-cargar todas las modificaciones relacionadas con sensores de estos dispositivos
    modificaciones_por_sensor = {}
    modificaciones_qs = Modificacion.objects.filter(
        Q(id_dispositivo__in=dispositivos_ids) & 
        (Q(sensor_saliente__isnull=False) | Q(componente_entrante__isnull=False))
    ).select_related('sensor_saliente', 'id_trabajador', 'componente_entrante').order_by('-fecInstalacionMod')
    
    for mod in modificaciones_qs:
        if mod.sensor_saliente:
            sensor_id = mod.sensor_saliente.id_componente
            if sensor_id not in modificaciones_por_sensor:
                modificaciones_por_sensor[sensor_id] = mod
        if mod.componente_entrante:
            comp_id = mod.componente_entrante.id_componente
            if comp_id not in modificaciones_por_sensor:
                modificaciones_por_sensor[comp_id] = mod
    
    # Pre-cargar sensores canibalizados
    sensores_canibalizados = {}
    for sensor in Sensor.objects.filter(
        dispositivo_instalado__in=dispositivos_ids,
        info_canibalizado__isnull=False
    ).exclude(info_canibalizado__exact=''):
        sensores_canibalizados[sensor.dispositivo_instalado_id] = sensor.info_canibalizado

    datos_tabla = []
    for idx, dispositivo in enumerate(page_obj, start=page_obj.start_index()):
        ultima_modificacion = dispositivo.modificacion_set.order_by('-fecInstalacionMod').first()
        sensores_del_dispositivo = {s.tipGas: s for s in dispositivo.sensor_set.all()}
        ultimo_mantenimiento = dispositivo.mantenimientos.order_by('-fecha_intervencion').first()
        estatus_garantia_equipo = 'VIGENTE' if dispositivo.fecVencimientoGarantia and dispositivo.fecVencimientoGarantia >= hoy else 'CADUCADO'
        ns_codigo = ''.join(filter(str.isdigit, dispositivo.tag or ''))
        placa_electronica = next((p for p in dispositivo.partes.all() if 'placa electrónica' in p.nomPart.lower()), None)
        fecha_fab_placa = placa_electronica.fecFab if placa_electronica and placa_electronica.fecFab else ''
        # Usar cache de sensores canibalizados
        sensor_canibalizado_info = sensores_canibalizados.get(dispositivo.id_dispositivo, '')
        ultima_fecha_mant_str = ''
        if ultimo_mantenimiento and ultimo_mantenimiento.fecha_intervencion:
            fecha_local = timezone.localtime(ultimo_mantenimiento.fecha_intervencion)
            ultima_fecha_mant_str = fecha_local.strftime('%d/%m/%Y')
        cambios_partes_clave = { 'PCBA': None, 'CARCASA': None, 'CLIP': None }
        todas_mods_partes = dispositivo.modificacion_set.filter(MotivoCambio__in=cambios_partes_clave.keys()).order_by('MotivoCambio', '-fecInstalacionMod')
        for mod in todas_mods_partes:
            motivo = mod.MotivoCambio.upper()
            if motivo in cambios_partes_clave and cambios_partes_clave[motivo] is None:
                cambios_partes_clave[motivo] = mod
        
        cardex_status = "Revisado" if getattr(dispositivo, 'cardex_revisado', False) else ""
        observacion_html = f"""
            <button type="button" class="btn btn-sm btn-info btn-observacion" 
                    data-bs-toggle="modal" data-bs-target="#observacionesModal"
                    data-device-id="{dispositivo.id_dispositivo}"
                    data-device-name="{dispositivo.nomDisp}"
                    
                    // --- ¡NUEVOS ATRIBUTOS DATA CON LAS URLS! ---
                    data-get-url="{ reverse('cenerisapp:get_observaciones_json', args=[dispositivo.pk]) }"
                    data-add-url="{ reverse('cenerisapp:add_observacion_json', args=[dispositivo.pk]) }">
                Ver/Añadir
            </button>
        """
        row_data = [
            idx, dispositivo.nomDisp, dispositivo.num_serie, dispositivo.fecFabricacion,
            dispositivo.fecIngreso, dispositivo.fecVencimientoGarantia, ns_codigo, dispositivo.tag,
            ultima_fecha_mant_str if ultima_fecha_mant_str else '',
            ultimo_mantenimiento.tecnico_a_cargo.nomEmpleado if ultimo_mantenimiento and ultimo_mantenimiento.tecnico_a_cargo else '',
            ", ".join(sensores_del_dispositivo.keys()),
            dispositivo.area_general if dispositivo.area_general else '',
            observacion_html,
            estatus_garantia_equipo,
        ]
        
        for tipo in tipos_de_sensor_unicos:
            sensor = sensores_del_dispositivo.get(tipo)
            row_data.append('VIGENTE' if sensor and sensor.fecVencGarantia and sensor.fecVencGarantia >= hoy else ('CADUCADO' if sensor else 'N/A'))

        row_data.extend([
            "",
            ultimo_mantenimiento.observacion_msa if ultimo_mantenimiento else '',
            dispositivo.fec_irreparable, dispositivo.fec_inoperativo, dispositivo.estadoD,
            getattr(dispositivo, 'propiedad', 'SMCV'),
            ultima_modificacion.fecInstalacionMod if ultima_modificacion else ''
        ])
        
        for tipo in tipos_de_sensor_unicos:
            sensor = sensores_del_dispositivo.get(tipo)
            if sensor:
                # Usar cache de modificaciones en lugar de consultar
                mod_sensor = modificaciones_por_sensor.get(sensor.id_componente)
                row_data.extend([
                    mod_sensor.sensor_saliente.nSerieActual if mod_sensor and mod_sensor.sensor_saliente else '',
                    sensor.nSerieActual, sensor.fecFabComp, sensor.fecInst,
                    mod_sensor.id_trabajador.nomEmpleado if mod_sensor and mod_sensor.id_trabajador else '',
                    sensor.nro_guia_ingreso, sensor.item_guia, sensor.fecVencGarantia,
                    'VIGENTE' if sensor.fecVencGarantia and sensor.fecVencGarantia >= hoy else 'CADUCADO',
                    sensor.estComp
                ])
            else:
                row_data.extend([''] * len(CAMPOS_POR_SENSOR_DETALLES))
        
        pcba_mod = cambios_partes_clave['PCBA']
        carcasa_mod = cambios_partes_clave['CARCASA']
        clip_mod = cambios_partes_clave['CLIP']
        row_data.extend([
            fecha_fab_placa, sensor_canibalizado_info,
            f"Se cambió por {pcba_mod.id_trabajador.nomEmpleado}" if pcba_mod and pcba_mod.id_trabajador else '',
            f"Se cambió por {carcasa_mod.id_trabajador.nomEmpleado}" if carcasa_mod and carcasa_mod.id_trabajador else '',
            f"Se cambió por {clip_mod.id_trabajador.nomEmpleado}" if clip_mod and clip_mod.id_trabajador else '',
            cardex_status
        ])
        
        datos_tabla.append(row_data)

    # ========================================================================
    # 4. PREPARAR CONTEXTO FINAL PARA LA PLANTILLA
    # ========================================================================
    context = {
        'titulo': 'Base de Datos de Equipos Portátiles',
        'page_obj': page_obj,
        'datos_tabla': datos_tabla,
        'headers_completos': headers_completos,
        # Datos para construir las cabeceras complejas
        'headers_fijos_inicio': headers_fijos_inicio,
        'tipos_de_sensor_unicos': tipos_de_sensor_unicos,
        'headers_fijos_finales': headers_fijos_finales,
        'CAMPOS_POR_SENSOR_DETALLES': CAMPOS_POR_SENSOR_DETALLES,
        'SENSOR_HEADER_CONFIG': SENSOR_HEADER_CONFIG,
        'headers_fijos_finales_finales': headers_fijos_finales_finales,
        
        # --- AÑADIR DATOS PARA EL FORMULARIO DE FILTROS ---
        'opciones_modelos': opciones_modelos,
        'opciones_estados': opciones_estados,
        'opciones_areas': opciones_areas,
        'opciones_garantia': opciones_garantia,
        'opciones_observaciones': opciones_observaciones,
        'opciones_tipo_gas': opciones_tipo_gas,
        'opciones_estado_sensor': opciones_estado_sensor,
        'opciones_garantia_sensor': opciones_garantia_sensor,
        'filtros_aplicados': {
            'modelo': modelo_filtro,
            'serie': serie_filtro,
            'estado': estado_filtro,
            'area': area_filtro,
            'ingreso_desde': ingreso_desde_filtro,       # <-- Añadido/Actualizado
            'ingreso_hasta': ingreso_hasta_filtro,       # <-- Añadido/Actualizado
            'vencimiento_desde': vencimiento_desde_filtro, # <-- Nuevo
            'vencimiento_hasta': vencimiento_hasta_filtro, # <-- Nuevo
            'fecha_desde': fecha_desde_filtro,
            'fecha_hasta': fecha_hasta_filtro,
            'modificacion_desde': modificacion_desde_filtro,
            'mantenimiento_desde': mantenimiento_desde_filtro,
            'garantia': garantia_filtro,
            'irreparable_desde': irreparable_desde_filtro,
            'inoperativo_desde': inoperativo_desde_filtro,
            'observaciones': observaciones_filtro,
            'sensor_gas': sensor_gas_filtro,
            'sensor_serie': sensor_serie_filtro,
            'sensor_estado': sensor_estado_filtro,
            'sensor_instalacion_desde': sensor_instalacion_desde_filtro,
            'sensor_instalacion_hasta': sensor_instalacion_hasta_filtro,
            'sensor_garantia': sensor_garantia_filtro,
        }
    }
    
    return render(request, 'tabla/tabla_portatiles.html', context)


@login_required
def dashboard_index(request):
    # Asegúrate de que los campos 'tipoDisp' y 'estadoD' estén en mayúsculas
    # si los estás comparando/agrupando directamente contra cadenas de texto.
    from django.db.models.functions import Upper, Lower
    from django.db.models import Count

    total_dispositivos = Dispositivo.objects.count()
    
    # Aplicar Upper a tipoDisp para agrupar de forma consistente
    dispositivo_por_tipo = Dispositivo.objects.annotate(
        tipo_upper=Upper('tipoDisp')
    ).values('tipo_upper').annotate(
        total=Count('tipo_upper')
    ).order_by('tipo_upper')
    
    entregas_por_empresa = Registro.objects.values(
        'trabajador_receptor__empresa_id__nombreE'
    ).annotate(
        total=Count('id_registro')
    ).order_by('-total')

    # --- CÁLCULO DE OPERATIVOS/INOPERATIVOS ---
    # Usar icontains o una función Upper para la comprobación en el filtro es más robusto si los datos son inconsistentes.
    # Si quieres estrictamente 'Operativo' o 'Inoperativo', el filtro es suficiente si la data está limpia.
    # Asumimos que los datos de estadoD son correctos, pero normalizamos para el conteo:
    dispositivo_por_estado = Dispositivo.objects.annotate(
        estado_upper=Upper('estadoD')
    ).values('estado_upper').annotate(
        total=Count('estado_upper')
    ).order_by('estado_upper')
    
    # Recalculamos los contadores exactos usando Upper() para la consistencia
    operativo = Dispositivo.objects.filter(estadoD__iexact='operativo').count()
    inoperativo = Dispositivo.objects.filter(estadoD__iexact='inoperativo').count()
    
    # === Estadísticas de Préstamos (sin cambios) ===
    prestados = Registro.objects.filter(fecDevol__isnull=True).count()
    
    # Usamos __iexact (case-insensitive) para la disponibilidad
    disponibles_operativos = Dispositivo.objects.filter(estadoD__iexact='operativo').count() - prestados

    
    # --- PROCESAMIENTO POR ÁREA Y ESTADO ---
    datos_crudos_area_estado = Dispositivo.objects.filter(
        tipoDisp__iexact='portatil' # Usamos iexact para el filtro de tipoDisp
    ).exclude(
        area_general__isnull=True
    ).exclude(
        area_general__exact=''
    ).annotate(
        area_upper=Upper('area_general'), # Normalizamos el área para agrupar
        estado_upper=Upper('estadoD')    # Normalizamos el estado
    ).values(
        'area_upper', 'estado_upper'
    ).annotate(
        total=Count('id_dispositivo')
    ).order_by('area_upper')
    
    datos_procesados = {}
    
    for item in datos_crudos_area_estado:
        # Usamos los campos normalizados del ORM
        area = item['area_upper']
        estado = item['estado_upper']
        total = item['total']
        
        # El mapeo de estado debe usar mayúsculas
        if area not in datos_procesados:
            datos_procesados[area] = {'OPERATIVO': 0, 'INOPERATIVO': 0}
        
        # El estado 'Operativo' se convierte en 'OPERATIVO', y 'Inoperativo' en 'INOPERATIVO'
        if estado in datos_procesados[area]:
            datos_procesados[area][estado] = total

    labels_area_estado = list(datos_procesados.keys())
    # NOTA: Debes cambiar 'Operativo'/'Inoperativo' a 'OPERATIVO'/'INOPERATIVO' en esta línea
    data_operativos = [datos['OPERATIVO'] for datos in datos_procesados.values()]
    data_inoperativos = [datos['INOPERATIVO'] for datos in datos_procesados.values()]
    
    # --- PRÉSTAMOS POR TURNO ---
    turnos = ['A', 'B']

    # Normalizamos el turno en el ORM para agrupar de forma consistente
    data_dispositivos = Registro.objects.filter(
        id_dispositivo__tipoDisp__iexact='portatil', # iexact para el filtro
        turno__in=turnos
    ).annotate(
        turno_upper=Upper('turno') # Normalizamos el turno para agrupar
    ).values('turno_upper').annotate(total=Count('id_registro'))
    
    # Contamos los préstamos de COMPONENTES (bombas) por cada turno
    data_bombas = Registro.objects.filter(
        id_componente__nomComp__icontains='bomba', 
        turno__in=turnos
    ).annotate(
        turno_upper=Upper('turno') # Normalizamos el turno para agrupar
    ).values('turno_upper').annotate(total=Count('id_registro'))

    # Convertimos los resultados a un formato fácil de usar para el gráfico
    # Usamos los campos normalizados 'turno_upper'
    dispositivos_por_turno = {item['turno_upper']: item['total'] for item in data_dispositivos}
    bombas_por_turno = {item['turno_upper']: item['total'] for item in data_bombas}
    
    # Las etiquetas de los turnos deben coincidir con la normalización si el input es distinto
    labels_turnos = [t.upper() for t in turnos] # Normalizamos las etiquetas
    values_dispositivos = [dispositivos_por_turno.get(t, 0) for t in labels_turnos]
    values_bombas = [bombas_por_turno.get(t, 0) for t in labels_turnos]


    context = {
        'total_dispositivos': total_dispositivos,
        'por_tipo': list(dispositivo_por_tipo),
        'por_estado': list(dispositivo_por_estado),
        'entregas_por_empresa': list(entregas_por_empresa),
        'operativo': operativo,
        'inoperativo': inoperativo,
        'prestados': prestados,
        'disponibles': disponibles_operativos,
        'labels_area_estado': labels_area_estado,
        'data_operativos': data_operativos,
        'data_inoperativos': data_inoperativos,

        'labels_turnos': labels_turnos,
        'values_dispositivos': values_dispositivos,
        'values_bombas': values_bombas,
    }
    return render(request, 'dashboard/index.html', context)
