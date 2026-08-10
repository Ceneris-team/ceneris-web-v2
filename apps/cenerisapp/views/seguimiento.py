"""Vistas de seguimiento diario.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import calendar

from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from cenerisapp.forms import SeguimientoDiarioForm
from cenerisapp.models import Dispositivo, Programa, SeguimientoDiario


@login_required
def gestionar_seguimiento_diario(request):

    anos_disponibles = Programa.objects.values_list('ano', flat=True).distinct().order_by('-ano')
    areas_generales_disponibles = Dispositivo.objects.filter(
        tipoDisp__iexact="Portatil" # Asumiendo que 'tipo_dispositivo' es el campo para "Portatil"
    ).values_list('area_general', flat=True).distinct().order_by('area_general')
    
    meses_disponibles = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    today = date.today()
    try:
        ano_seleccionado = int(request.GET.get('ano', today.year))
        mes_seleccionado = int(request.GET.get('mes', today.month))
    except (ValueError, TypeError):
        ano_seleccionado = today.year
        mes_seleccionado = today.month
        
    area_general_seleccionada = request.GET.get('area_general')

    # 2. PROCESAR EL GUARDADO (SI ES POST)
    if request.method == 'POST':
        print("\n--- INICIO PROCESO POST (Guardar Seguimiento) ---")
    
        # --- 1. OBTENEMOS EL ESTADO "ANTES" DEL CAMBIO ---
        # Reconstruimos la matriz de datos tal como estaba antes del envío.
        seguimientos_previos = SeguimientoDiario.objects.filter(
            dispositivo__area_general=area_general_seleccionada,
            fecha__year=ano_seleccionado,
            fecha__month=mes_seleccionado
        )
        matriz_previa = {}
        for s in seguimientos_previos:
            if s.dispositivo_id not in matriz_previa:
                matriz_previa[s.dispositivo_id] = {}
            matriz_previa[s.dispositivo_id][s.fecha] = s.estado_texto

        items_guardados = 0
        items_actualizados = 0
        items_borrados = 0

        # Iteramos sobre los datos enviados en el POST
        for key, new_value in request.POST.items():
            if key.startswith('estado_D'):
                try:
                    parts = key.split('_')
                    dispositivo_id = int(parts[1].replace('D', ''))
                    fecha_str = parts[2].replace('F', '')
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()

                    # --- 2. COMPARAMOS EL ESTADO "NUEVO" CON EL "ANTIGUO" ---
                    old_value = matriz_previa.get(dispositivo_id, {}).get(fecha_obj, '')
                    
                    # Solo actuamos si el valor ha cambiado
                    if new_value != old_value:
                        if new_value:
                            # Si el nuevo valor NO está vacío, creamos o actualizamos.
                            obj, created = SeguimientoDiario.objects.update_or_create(
                                dispositivo_id=dispositivo_id,
                                fecha=fecha_obj,
                                defaults={'estado_texto': new_value}
                            )
                            if created: items_guardados += 1
                            else: items_actualizados += 1
                        else:
                            # Si el nuevo valor ESTÁ vacío, significa que el usuario lo borró.
                            SeguimientoDiario.objects.filter(dispositivo_id=dispositivo_id, fecha=fecha_obj).delete()
                            items_borrados += 1
                            
                except (ValueError, IndexError):
                    continue
        
        messages.success(request, f"Seguimiento guardado. Creados: {items_guardados}, Actualizados: {items_actualizados}, Borrados: {items_borrados}.")
        return redirect(f"{request.path}?ano={ano_seleccionado}&mes={mes_seleccionado}&area_general={area_general_seleccionada or ''}")

    historial_qs = SeguimientoDiario.objects.exclude(
        estado_texto__isnull=True
    ).exclude(
        estado_texto__exact=''
    ).select_related('dispositivo').order_by('-fecha', '-id_seguimiento')
    
    # Capturar filtros para el historial
    historial_q = request.GET.get('historial_q', '')
    historial_fecha_desde = request.GET.get('historial_fecha_desde', '')
    historial_fecha_hasta = request.GET.get('historial_fecha_hasta', '')
    
    # Aplicar filtros al historial
    if historial_q:
        historial_qs = historial_qs.filter(dispositivo__nomDisp__icontains=historial_q)
    if historial_fecha_desde:
        historial_qs = historial_qs.filter(fecha__gte=historial_fecha_desde)
    if historial_fecha_hasta:
        historial_qs = historial_qs.filter(fecha__lte=historial_fecha_hasta)

    # Paginación para el historial
    historial_paginator = Paginator(historial_qs, 10)
    page_number_historial = request.GET.get('page_historial') # <-- Usamos un param diferente
    historial_page_obj = historial_paginator.get_page(page_number_historial)


    # 3. PREPARAR DATOS PARA LA PLANTILLA (PETICIÓN GET)
    context = {
        'titulo': 'Gestión de Seguimiento Diario',
        # Pasamos las listas de opciones a la plantilla
        'anos_disponibles': anos_disponibles,
        'meses_disponibles': meses_disponibles,
        'areas_generales_disponibles': [area for area in areas_generales_disponibles if area],
        # Pasamos los valores seleccionados para que los <select> los recuerden
        'ano_seleccionado': ano_seleccionado,
        'mes_seleccionado': mes_seleccionado,
        'area_general_seleccionada': area_general_seleccionada,

        'historial_page_obj': historial_page_obj,
        'filtros_historial_aplicados': {
            'q': historial_q,
            'fecha_desde': historial_fecha_desde,
            'fecha_hasta': historial_fecha_hasta,
        }
    }
    
    # Solo construimos la matriz si el usuario ha seleccionado un área
    if area_general_seleccionada:
        num_dias = calendar.monthrange(ano_seleccionado, mes_seleccionado)[1]
        dias_del_mes = [date(ano_seleccionado, mes_seleccionado, dia) for dia in range(1, num_dias + 1)]
        
        dispositivos_qs = Dispositivo.objects.filter(
            area_general=area_general_seleccionada,
            tipoDisp='Portatil'
        ).order_by('nomDisp') # Es bueno tener un orden consistente

        # 2. Creamos el paginador
        matriz_paginator = Paginator(dispositivos_qs, 15) # Nuevo nombre
        page_number_matriz = request.GET.get('page_matriz') # <-- Usamos un param diferente
        matriz_page_obj = matriz_paginator.get_page(page_number_matriz) # <-- Nuevo nombre
        
        seguimientos = SeguimientoDiario.objects.filter(
            dispositivo__in=matriz_page_obj,
            fecha__year=ano_seleccionado,
            fecha__month=mes_seleccionado
        )
        
        matriz_seguimiento = {}
        for s in seguimientos:
            dispositivo_id = s.dispositivo.id_dispositivo # Obtenemos el ID
            if dispositivo_id not in matriz_seguimiento:
                matriz_seguimiento[dispositivo_id] = {}
            matriz_seguimiento[dispositivo_id][s.fecha] = s.estado_texto
            
        # Añadimos los datos de la matriz al contexto
        context.update({
            'matriz_page_obj': matriz_page_obj,
            'dias_del_mes': dias_del_mes,
            'matriz_seguimiento': matriz_seguimiento,
            'opciones_estado': SeguimientoDiarioForm.ESTADO_CHOICES,
        })

    return render(request, 'seguimiento/gestionar_seguimiento.html', context)
