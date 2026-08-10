from django.shortcuts import render, redirect, get_object_or_404
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import ProtectedError
from django.contrib import messages
from django.db.models import Sum, F, OuterRef, Subquery, Count, Q
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from dateutil.relativedelta import relativedelta

from .models import Insumo, RegistroReparacion, AsignacionInsumo, ItemInsumo, Accesorio
from .forms import CrearInsumoForm, InsumoUpdateForm, RegistroReparacionForm, ItemInsumoForm
from proyectos.models import Proyecto, TareaP


@login_required 
def lista_insumos(request):
    insumos_qs = Insumo.objects.annotate(
        stock_disponible_calculado=Count('items', filter=Q(items__estado='EN STOCK'))
    )

    # --- 2. APLICAR FILTROS ---
    # Buscador por nombre de insumo
    query = request.GET.get('q', '')
    if query:
        insumos_qs = insumos_qs.filter(nombre__icontains=query)
        
    # --- 3. APLICAR ORDENAMIENTO ---
    sort_by = request.GET.get('sort_by', 'nombre') # Por defecto, ordena por nombre A-Z

    if sort_by == 'stock_asc':
        insumos_qs = insumos_qs.order_by('stock_disponible_calculado')
    elif sort_by == 'stock_desc':
        insumos_qs = insumos_qs.order_by('-stock_disponible_calculado')
    else:
        # Ordenamiento por defecto (nombre A-Z)
        insumos_qs = insumos_qs.order_by('nombre')

    # --- Lógica para el reporte de costos (sin cambios) ---
    proyecto_seleccionado = None
    tareas_con_costos = None
    costo_total_proyecto = 0
    proyecto_id = request.GET.get('proyecto_id')

    proyecto_id = request.GET.get('proyecto_id')
    if proyecto_id:
        try:
            proyecto_seleccionado = Proyecto.objects.get(pk=proyecto_id)
            
            tareas = TareaP.objects.filter(proyecto=proyecto_seleccionado)

            subtarea_cost_subquery = AsignacionInsumo.objects.filter(
                subtarea__tarea=OuterRef('pk')
            ).values('subtarea__tarea').annotate(
                total=Sum(F('cantidad_asignada') * F('costo_unitario_registrado'))
            ).values('total')

            tareas_con_costos = tareas.annotate(
                costo_total=Subquery(subtarea_cost_subquery)
            )

            if tareas_con_costos:
                costo_total_proyecto = sum(tarea.costo_total or 0 for tarea in tareas_con_costos)

        except Proyecto.DoesNotExist:
            proyecto_seleccionado = None

    context = {
        'insumos': insumos_qs, # Pasamos el queryset ya filtrado y ordenado
        'proyecto_seleccionado': proyecto_seleccionado,
        'tareas_con_costos': tareas_con_costos,
        'costo_total_proyecto': costo_total_proyecto,
        'filtros_aplicados': {
            'query': query,
            'sort_by': sort_by,
        }
    }
    return render(request, 'lista_insumos.html', context)

@login_required 
def detalle_insumo(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    
    if request.method == 'POST':
        form = ItemInsumoForm(request.POST)
        if form.is_valid():
            nuevo_item = form.save(commit=False)
            
            # 2. Asignamos los campos que faltan y que el sistema conoce.
            nuevo_item.insumo_padre = insumo
            nuevo_item.estado = 'EN STOCK'
            
            # 3. Ahora que el objeto está completo, lo guardamos en la base de datos.
            nuevo_item.save()
            
            # 4. Ahora SÍ podemos usar la variable 'nuevo_item' en el mensaje.
            messages.success(request, f"Nuevo item S/N: {nuevo_item.numero_serie} añadido correctamente.")
            
            # Redirigimos a la misma página para ver el nuevo item en la lista.
            return redirect('inventario:detalle_insumo', pk=insumo.pk)
        else:
            # --- ¡CAMBIO CLAVE! ---
            # Si hay errores, los añadimos a los mensajes de Django
            # y redirigimos. El JS se encargará de volver a abrir el modal.
            for field, errors in form.errors.items():
                # Obtenemos el label del campo para un mensaje más amigable
                label = form.fields.get(field).label if form.fields.get(field) else field
                for error in errors:
                    messages.error(request, f"{label}: {error}")
            # Guardamos los datos incorrectos en la sesión para rellenar el formulario
            request.session['invalid_item_form_data'] = request.POST
            return redirect('inventario:detalle_insumo', pk=insumo.pk)

    items_qs = insumo.items.all()

    # 2. Recogemos los valores de los filtros de la URL
    query_codigo = request.GET.get('q_codigo', '')
    query_marca = request.GET.get('q_marca', '')
    query_modelo = request.GET.get('q_modelo', '')
    query_serie = request.GET.get('q_serie', '')
    filter_prox_calibracion = request.GET.get('prox_calibracion')

    # 3. Aplicamos los filtros al queryset
    if query_codigo:
        items_qs = items_qs.filter(codigo_interno__icontains=query_codigo)
    if query_marca:
        items_qs = items_qs.filter(marca__icontains=query_marca)
    if query_modelo:
        items_qs = items_qs.filter(modelo__icontains=query_modelo)
    if query_serie:
        items_qs = items_qs.filter(numero_serie__icontains=query_serie)

    if filter_prox_calibracion:
        today = timezone.now().date()
        if filter_prox_calibracion == 'vencido':
            items_qs = items_qs.filter(fecha_prox_calibracion__lt=today)
        elif filter_prox_calibracion == 'proximo_mes':
            limite_mes = today + timedelta(days=30)
            items_qs = items_qs.filter(fecha_prox_calibracion__gte=today, fecha_prox_calibracion__lte=limite_mes)

    # 4. Ordenamos los resultados
    items_individuales = items_qs.order_by('numero_serie')
    
    # Lógica para el formulario del modal (no cambia)
    invalid_data = request.session.pop('invalid_item_form_data', None)
    form = ItemInsumoForm(initial=invalid_data) if invalid_data else ItemInsumoForm()

    context = {
        'insumo': insumo,
        'items_individuales': items_individuales,
        'form': form,
        # Pasamos los filtros aplicados para mantener la selección en el formulario
        'filtros_aplicados': {
            'q_codigo': query_codigo,
            'q_marca': query_marca,
            'q_modelo': query_modelo,
            'q_serie': query_serie,
            'prox_calibracion': filter_prox_calibracion,
        }
    }
    return render(request, 'detalle_insumo.html', context)

@login_required 
def crear_insumo(request):
    if request.method == 'POST':
        form = CrearInsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventario:lista_insumos')
    else: 
        form = CrearInsumoForm()
    return render(request, 'crear_insumo.html', {'form': form})

@login_required 
@require_POST # Asegura que esta vista solo acepte peticiones POST
def update_insumo(request, insumo_id):
    insumo = get_object_or_404(Insumo, pk=insumo_id)
    
    # Leemos los datos JSON que envía nuestro script
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON inválido'}, status=400)

    form = InsumoUpdateForm(data, instance=insumo)

    if form.is_valid():
        updated_insumo = form.save()
        # Devolvemos una respuesta exitosa con los nuevos datos
        return JsonResponse({
            'status': 'success',
            'message': 'Insumo actualizado correctamente.',
            'insumo': {
                'id': updated_insumo.id,
                'stock_disponible': updated_insumo.stock_disponible,
                'costo_unitario_actual': f'{updated_insumo.costo_unitario_actual:.2f}', # Formateado a 2 decimales
                'unidad_medida': updated_insumo.unidad_medida,
            }
        })
    else:
        # Devolvemos los errores del formulario
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required 
def registrar_reparacion(request, pk):
    """
    Página dedicada con un formulario para registrar una reparación para un ItemInsumo específico.
    """
    item_insumo = get_object_or_404(ItemInsumo, pk=pk)
    
    if request.method == 'POST':
        form = RegistroReparacionForm(request.POST)
        if form.is_valid():
            reparacion = form.save(commit=False)
            reparacion.item_insumo = item_insumo
            reparacion.save()

            item_insumo.estado = 'EN REPARACION'
            item_insumo.save()
            
            messages.success(request, f"Reparación registrada para S/N: {item_insumo.numero_serie}.")
            # Vuelve a la página de detalle del insumo PADRE para ver el estado actualizado
            return redirect('inventario:detalle_insumo', pk=item_insumo.insumo_padre.pk)
    else:
        form = RegistroReparacionForm()

    # Historial de reparaciones para este item específico
    historial = item_insumo.reparaciones.all()
    
    context = {
        'form': form,
        'item_insumo': item_insumo,
        'historial': historial,
    }
    return render(request, 'registrar_reparacion.html', context)

@login_required 
@require_POST
def api_delete_item_insumo(request, pk):
    """
    API para eliminar un ItemInsumo específico.
    """
    item = get_object_or_404(ItemInsumo, pk=pk)
    
    if item.estado == 'INSTALADO':
        return JsonResponse({
            'status': 'error',
            'message': 'No se puede eliminar un item que está instalado en una tarea.'
        }, status=400)
    
    try:
        numero_serie = item.numero_serie
        item.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Item S/N: {numero_serie} eliminado correctamente.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def search_insumos(request):
    # El término de búsqueda viene de un parámetro GET (ej: ?term=tornillo)
    term = request.GET.get('term', '').strip()
    
    # Buscamos insumos cuyo nombre contenga el término, sin importar mayúsculas/minúsculas
    insumos = Insumo.objects.filter(nombre__icontains=term)[:10] # Limitamos a 10 resultados

    # Formateamos los resultados para que Select2 los entienda
    results = [{'id': insumo.id, 'text': insumo.nombre} for insumo in insumos]
    
    return JsonResponse({'results': results})

def api_get_asignacion_data(request, pk):
    asignacion = get_object_or_404(AsignacionInsumo, pk=pk)
    data = {
        'id': asignacion.id,
        'insumo_nombre': asignacion.insumo.nombre,
        'subtarea_titulo': asignacion.subtarea.titulo,
        'cantidad_asignada': asignacion.cantidad_asignada,
        'costo_total': asignacion.costo_total,
    }
    return JsonResponse(data)

@login_required 
@require_POST
@transaction.atomic
def api_devolver_insumo(request, pk):
    asignacion = get_object_or_404(AsignacionInsumo, pk=pk)
    
    try:
        data = json.loads(request.body)
        cantidad_a_devolver = int(data.get('cantidad_a_devolver'))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    # --- VALIDACIÓN ---
    if cantidad_a_devolver <= 0:
        return JsonResponse({'status': 'error', 'message': 'La cantidad debe ser mayor que cero.'}, status=400)
    
    if cantidad_a_devolver > asignacion.cantidad_asignada:
        return JsonResponse({
            'status': 'error', 
            'message': f'No se puede devolver más de lo asignado ({asignacion.cantidad_asignada}).'
        }, status=400)

    # --- LÓGICA DE ACTUALIZACIÓN ---
    # Reponer el stock
    insumo = asignacion.insumo
    insumo.stock_disponible += cantidad_a_devolver
    insumo.save()
    
    # Actualizar o eliminar la asignación
    if cantidad_a_devolver == asignacion.cantidad_asignada:
        # Si se devuelve todo, se elimina la asignación
        asignacion.delete()
        accion = 'eliminada'
    else:
        # Si se devuelve una parte, se resta la cantidad
        asignacion.cantidad_asignada -= cantidad_a_devolver
        asignacion.save()
        accion = 'actualizada'
        
    return JsonResponse({
        'status': 'success',
        'message': f'Devolución procesada. La asignación ha sido {accion}.',
    })

def api_get_items_for_insumo(request, insumo_id):
    """
    Devuelve una lista de Items (con su número de serie) que pertenecen
    a un tipo de Insumo general.
    """
    items = ItemInsumo.objects.filter(insumo_padre_id=insumo_id)
    results = [
        {'id': item.id, 'numero_serie': item.numero_serie}
        for item in items
    ]
    return JsonResponse({'items': results})

@login_required 
def notificaciones_calibracion(request):
    today = timezone.now().date()
    
    # --- 1. RECOGER PARÁMETROS DE FILTRADO DE LA URL ---
    query_serie = request.GET.get('q_serie', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # --- 2. CONSTRUIR LOS QUERYSETS BASE (PARA ITEMS Y ACCESORIOS) ---
    items_base_qs = ItemInsumo.objects.select_related('insumo_padre')
    accesorios_base_qs = Accesorio.objects.select_related('item_insumo__insumo_padre')
    
    # --- 3. APLICAR FILTROS A LOS QUERYSETS BASE ---
    if query_serie:
        # ¡LA CORRECCIÓN ESTÁ AQUÍ!
        # Buscamos en 3 campos para los Items:
        # 1. El nombre del Insumo padre (ej: "Detector")
        # 2. El número de serie del Item (ej: "SN-DET-123")
        # 3. El código interno del Item (ej: "DET-001")
        items_base_qs = items_base_qs.filter(
            Q(insumo_padre__nombre__icontains=query_serie) |
            Q(numero_serie__icontains=query_serie) |
            Q(codigo_interno__icontains=query_serie)
        )
        
        # Hacemos lo mismo para los Accesorios
        accesorios_base_qs = accesorios_base_qs.filter(
            Q(nombre__icontains=query_serie) | # Nombre del accesorio (ej: "Batería")
            Q(numero_serie__icontains=query_serie) | # S/N del accesorio
            Q(item_insumo__insumo_padre__nombre__icontains=query_serie) | # Nombre del equipo al que pertenece
            Q(item_insumo__numero_serie__icontains=query_serie) # S/N del equipo al que pertenece
        )

    if start_date:
        items_base_qs = items_base_qs.filter(fecha_prox_calibracion__gte=start_date)
        accesorios_base_qs = accesorios_base_qs.filter(fecha_prox_calibracion__gte=start_date)
        
    if end_date:
        items_base_qs = items_base_qs.filter(fecha_prox_calibracion__lte=end_date)
        accesorios_base_qs = accesorios_base_qs.filter(fecha_prox_calibracion__lte=end_date)

    # --- 4. CLASIFICAR LOS RESULTADOS FILTRADOS (la lógica de clasificación no cambia) ---
    vencidos = []
    muy_cerca = []
    cerca_de_vencer = []

    # Combinamos ambos querysets en una sola lista para iterar
    # El diccionario 'tipo' nos ayudará en la plantilla
    items_a_revisar = [
        {'objeto': item, 'es_accesorio': False} for item in items_base_qs
    ] + [
        {'objeto': acc, 'es_accesorio': True} for acc in accesorios_base_qs
    ]

    for item_info in items_a_revisar:
        fecha_a_revisar = item_info['objeto'].fecha_prox_calibracion
        if not fecha_a_revisar: continue
        
        # Lógica de clasificación
        if fecha_a_revisar < today:
            vencidos.append(item_info)
        elif fecha_a_revisar <= today + timedelta(days=7):
            muy_cerca.append(item_info)
        elif fecha_a_revisar <= today + timedelta(days=30):
            cerca_de_vencer.append(item_info)
    
    context = {
        'vencidos': vencidos,
        'muy_cerca': muy_cerca,
        'cerca_de_vencer': cerca_de_vencer,
        'filtros_aplicados': {
            'q_serie': query_serie,
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    return render(request, 'notificaciones_calibracion.html', context)

@login_required 
def gestionar_accesorios(request, pk):
    item_insumo = get_object_or_404(ItemInsumo, pk=pk)
    
    if request.method == 'POST':
        # Lógica para AÑADIR un nuevo accesorio
        nombre = request.POST.get('nombre')
        serie = request.POST.get('numero_serie')
        
        if nombre:
            Accesorio.objects.create(item_insumo=item_insumo, nombre=nombre, numero_serie=serie)
            messages.success(request, "Accesorio añadido correctamente.")
        else:
            messages.error(request, "El nombre del accesorio no puede estar vacío.")
        
        return redirect('inventario:gestionar_accesorios', pk=item_insumo.pk)

    # Lógica GET: Muestra la lista de accesorios existentes
    accesorios = item_insumo.accesorios_list.all()
    
    context = {
        'item_insumo': item_insumo,
        'accesorios': accesorios,
    }
    return render(request, 'gestionar_accesorios.html', context)

@login_required 
@require_POST
def api_delete_accesorio(request, pk):
    """
    Endpoint de API para eliminar un accesorio específico.
    """
    accesorio = get_object_or_404(Accesorio, pk=pk)
    
    try:
        nombre_accesorio = accesorio.nombre
        accesorio.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'El accesorio "{nombre_accesorio}" ha sido eliminado.'
        })
    except Exception as e:
        # Captura cualquier error inesperado durante la eliminación
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@transaction.atomic
def api_registrar_calibracion(request, model_type, pk):
    """
    Endpoint de API para registrar una nueva calibración para un ItemInsumo o un Accesorio.
    Actualiza la fecha de calibración a hoy y calcula la próxima calibración en 1 año.
    """
    today = timezone.now().date()
    obj_a_calibrar = None

    # 1. Identificamos el objeto a calibrar basándonos en el model_type
    if model_type == 'iteminsumo':
        obj_a_calibrar = get_object_or_404(ItemInsumo, pk=pk)
    elif model_type == 'accesorio':
        obj_a_calibrar = get_object_or_404(Accesorio, pk=pk)
    else:
        return JsonResponse({'status': 'error', 'message': 'Tipo de objeto no válido.'}, status=400)

    # --- LÓGICA DE ACTUALIZACIÓN ---
    
    # Verificación para evitar recalibrar algo que no está cerca de vencer
    # (Esta lógica es opcional pero es una buena práctica)
    if not obj_a_calibrar.calibracion_vencida and not obj_a_calibrar.necesita_calibracion_pronto:
        return JsonResponse({
            'status': 'warning',
            'message': 'Este equipo no requiere calibración en este momento.'
        }, status=400)
    
    # 2. Actualizamos las fechas
    obj_a_calibrar.fecha_calibracion = today
    # Calculamos la próxima calibración exactamente 1 año después
    obj_a_calibrar.fecha_prox_calibracion = today + relativedelta(years=1)
    
    # 3. (Opcional) Si estaba 'EN REPARACION' o 'DAÑADO', lo ponemos de nuevo 'EN STOCK'
    if obj_a_calibrar.estado in ['EN REPARACION', 'DAÑADO']:
        obj_a_calibrar.estado = 'EN STOCK'
        
    obj_a_calibrar.save()

    return JsonResponse({
        'status': 'success',
        'message': f'Calibración registrada. Próxima calibración: {obj_a_calibrar.fecha_prox_calibracion.strftime("%d-%m-%Y")}',
        'new_state': obj_a_calibrar.get_estado_display() if hasattr(obj_a_calibrar, 'get_estado_display') else None,
    })