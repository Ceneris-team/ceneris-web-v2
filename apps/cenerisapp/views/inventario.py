"""Vistas de inventario, lotes, componentes y stock.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from cenerisapp.forms import InventarioForm, OtroComponenteForm, SensorLoteForm
from cenerisapp.models import (
    Componente,
    Empleado,
    Inventario,
    Modificacion,
    OtroComponente,
    Sensor,
)


@login_required
def crear_inventario_lote(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            
            nuevo_lote = form.save()
        
            messages.success(request, f"Lote de inventario #{nuevo_lote.id_inventario} creado. Ahora, por favor, añade los detalles de los componentes.")
    
            return redirect('cenerisapp:añadir_componentes_a_lote', lote_id=nuevo_lote.id_inventario)
    else:
        form = InventarioForm()

    context = { 'form': form, 'titulo': 'Registrar Nuevo Lote de Inventario' }
    return render(request, 'inventario_general/crear_lote.html', context)


@login_required
def añadir_componentes_a_lote(request, lote_id):
    lote = get_object_or_404(Inventario, pk=lote_id)
    componente_tipo = request.GET.get('tipo', 'sensor')
    SensorFormSet = formset_factory(SensorLoteForm, extra=lote.cantIngreso)
    OtroComponenteFormSet = formset_factory(OtroComponenteForm, extra=lote.cantIngreso)

    
    formset_sensores = SensorFormSet(prefix='sensor')
    formset_otros = OtroComponenteFormSet(prefix='otro')
 
    if request.method == 'POST':
        nombre_comun = lote.descripInv
 
        formset_sensores = SensorFormSet(request.POST, prefix='sensor')
        formset_otros = OtroComponenteFormSet(request.POST, prefix='otro')
 
 
        if 'guardar_sensores' in request.POST:
            formset_sensores = SensorFormSet(request.POST, prefix='sensor')
            if formset_sensores.is_valid():
                try: # --- INICIO DEL BLOQUE TRY ---
                    for form in formset_sensores:
                        if form.has_changed():
                            sensor = form.save(commit=False)
                            sensor.inventario = lote
                            sensor.nomComp = nombre_comun
                            sensor.estComp = 'Operativo'
                            sensor.save() 
                           
                    messages.success(request, "Sensores añadidos exitosamente.")
                    return redirect('cenerisapp:lista_lotes')
 
                except ValidationError as e: # --- AQUÍ ATRAPAMOS EL ERROR ---
                    
                    
                    for error in e.message_dict['__all__']:
                        messages.error(request, error)
                    
           
            else: # Si el formset no es válido desde el principio
                messages.error(request, "Por favor, corrige los errores en el formulario de sensores.")
 
        elif 'guardar_otros' in request.POST:
            formset_otros = OtroComponenteFormSet(request.POST, prefix='otro')
            if formset_otros.is_valid():
                for form in formset_otros:
                    if form.has_changed():
                        
                        otro_comp = form.save(commit=False)
                        otro_comp.inventario = lote
                        otro_comp.nomComp = nombre_comun
                        otro_comp.save()
                messages.success(request, "Componentes añadidos exitosamente.")
                return redirect('cenerisapp:lista_lotes')
            else:
                messages.error(request, "Por favor, corrige los errores en el formulario de otros componentes.")
               
    context = {
        'lote': lote,
        'formset_sensores': formset_sensores,
        'formset_otros': formset_otros,
        'componente_tipo_seleccionado': componente_tipo
    }
 
    return render(request, 'inventario_general/añadir_componentes.html', context)


@login_required
def lista_inventario(request):
    
    # --- 1. PREPARAR DATOS PARA LOS FILTROS ---
    opciones_ubicaciones = Inventario.objects.values_list('ubiImv', flat=True).distinct().order_by('ubiImv')
    opciones_trabajadores = Empleado.objects.filter(inventario__isnull=False).distinct().order_by('nomEmpleado')

    # --- 2. CAPTURAR VALORES DE FILTRO ---
    query_desc = request.GET.get('q', '')
    ubicacion_filtro = request.GET.get('ubicacion', '')
    trabajador_filtro = request.GET.get('trabajador', '')
    
    # --- 3. CONSTRUIR QUERYSET BASE Y FILTRAR ---
    lotes_qs = Inventario.objects.annotate(
        num_componentes=Count('componentes')
    )
    
    if query_desc:
        lotes_qs = lotes_qs.filter(descripInv__icontains=query_desc)
    if ubicacion_filtro:
        lotes_qs = lotes_qs.filter(ubiImv=ubicacion_filtro)
    if trabajador_filtro:
        lotes_qs = lotes_qs.filter(id_trabajador__pk=trabajador_filtro)

    # Ordenar al final
    lotes_qs = lotes_qs.order_by('-id_inventario')

    # --- 4. APLICAR PAGINACIÓN ---
    paginator = Paginator(lotes_qs, 9) # 9 lotes por página (se ve bien en un grid de 3 columnas)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # --- 5. CONTEXTO ---
    context = {
        'page_obj': page_obj,
        'titulo': 'Gestión de Lotes de Inventario',
        
        # Para los filtros
        'opciones_ubicaciones': opciones_ubicaciones,
        'opciones_trabajadores': opciones_trabajadores,
        'filtros_aplicados': {
            'q': query_desc,
            'ubicacion': ubicacion_filtro,
            'trabajador': int(trabajador_filtro) if trabajador_filtro else None,
        }
    }
    return render(request, 'inventario_general/lista_lotes.html', context)


@login_required
def vista_stock(request):
    
    stock_sensores = Sensor.objects.filter(dispositivo_instalado__isnull=True)\
                                   .values('nomComp')\
                                   .annotate(cantidad=Count('id_componente'))

    stock_otros = OtroComponente.objects.values('nomComp')\
                                        .annotate(cantidad=Count('id_componente'))
        
    stock_combinado = defaultdict(int)
    for item in stock_sensores:
        stock_combinado[item['nomComp']] += item['cantidad']
    for item in stock_otros:
        stock_combinado[item['nomComp']] += item['cantidad']

    stock_con_estado = []
    
    for nombre, cantidad in sorted(stock_combinado.items()):
        
        umbral_bajo = 5
        umbral_medio = 10

        estado = ''
        if cantidad < umbral_bajo:
            estado = 'rojo'
        elif cantidad < umbral_medio:
            estado = 'amarillo'
        else:
            estado = 'verde'
            
        stock_con_estado.append({
            'nomComp': nombre,
            'cantidad_total': cantidad,
            'estado_stock': estado
        })

    context = {
        'stock_items': stock_con_estado,
        'titulo': 'Stock de Componentes Disponibles'
    }
    return render(request, 'inventario_general/vista_stock.html', context)


@login_required
def lista_componentes(request, lote_id):
    lote = get_object_or_404(Inventario, pk=lote_id)
   
    
    componentes_del_lote = lote.componentes.all()
 
    context = {
        'lote': lote,
        'componentes': componentes_del_lote,
        'titulo': f'Componentes del Lote #{lote.id_inventario}'
    }
    return render(request, 'inventario_general/lista_componentes.html', context)


@login_required
def componentes_indice(request):
    """Muestra la página con las dos tarjetas de selección."""
    titulo = "Índice de Componentes"
    return render(request, 'componentes/indice.html', {'titulo': titulo})


@login_required
def lista_sensores(request):
    """Muestra una tabla con todos los datos de los sensores."""
    
    
    sensores = Sensor.objects.select_related('inventario').all().order_by('-id_componente')
   
    context = {
        'sensores': sensores,
        'titulo': 'Lista de Todos los Sensores'
    }
    return render(request, 'componentes/lista_sensores.html', context)


@login_required
def lista_otros_componentes(request):
    """Muestra una tabla con todos los datos de otros componentes."""
    otros_componentes = OtroComponente.objects.select_related('inventario').all().order_by('-id_componente')
   
    context = {
        'otros_componentes': otros_componentes,
        'titulo': 'Lista de Otros Componentes'
    }
    return render(request, 'componentes/lista_otros.html', context)


@login_required
def detalle_componente(request, id_componente):
    componente = get_object_or_404(Componente, pk=id_componente)
    context = {
        'componente': componente,
        'titulo': 'Detalle del Componente'
    }
    return render(request, 'componentes/detalle_componente.html', context)


def modificaciones_componente(request, id_componente):
    componente = Componente.objects.get(pk=id_componente)
    modificaciones = Modificacion.objects.filter(id_componente=componente)
    context = {
        'componente': componente,
        'modificaciones': modificaciones,
    }
    return render(request, 'modificaciones/modificaciones_componente.html', context)


@login_required
def search_componentes_disponibles(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        
        condicion_sensor = Q(
            sensor__isnull=False, 
            sensor__dispositivo_instalado__isnull=True,
            sensor__estComp='Operativo' # <-- ¡ESTE FILTRO ES CRUCIAL!
        )
        
        condicion_otro = Q(
            otrocomponente__isnull=False,
            otrocomponente__estComp='Operativo' # <-- ¡ESTE FILTRO ES CRUCIAL!
        )
        
        componentes_disponibles = Componente.objects.filter(
            Q(nomComp__icontains=query) & (condicion_sensor | condicion_otro)
        ).select_related('sensor', 'otrocomponente').distinct()

        results = [{ 'id': comp.pk, 'text': f"{comp.nomComp} (N/S: {comp.nSerieActual})" } 
                   for comp in componentes_disponibles[:10]]

    return JsonResponse(results, safe=False)


@login_required
def get_tipos_componentes(request):
    """
    Devuelve una lista de todos los NOMBRES de componentes únicos
    que existen en el stock y están disponibles.
    """
    # Buscamos sensores disponibles
    nombres_sensores_qs = Sensor.objects.filter(
        dispositivo_instalado__isnull=True,
        estComp='Operativo',
        nSerieActual__isnull=True # ¡Importante! Solo los que no tienen N/S
    ).values_list('nomComp', flat=True)
    
    # Buscamos otros componentes disponibles
    nombres_otros_qs = OtroComponente.objects.filter(
        estComp='Operativo',
        nSerieActual__isnull=True # ¡Importante! Solo los que no tienen N/S
    ).values_list('nomComp', flat=True)
    
    # Unimos los resultados y eliminamos duplicados
    tipos_unicos_set = set(nombres_sensores_qs) | set(nombres_otros_qs)
    
    # Convertimos a lista y ordenamos
    tipos_unicos = sorted(list(tipos_unicos_set))
    
    return JsonResponse(tipos_unicos, safe=False)


@login_required
def get_componentes_sin_ns(request):
    """
    Busca en el stock componentes de un tipo específico que NO tengan un número de serie asignado.
    """
    tipo = request.GET.get('tipo', None)
    if not tipo:
        return JsonResponse([], safe=False)

    componentes = Componente.objects.filter(
        nomComp=tipo,
        nSerieActual__isnull=True
    ).select_related('inventario')

    data = [
        {
            'id': comp.id_componente,
            # --- LÍNEA CORREGIDA ---
            'text': f"ID: {comp.id_componente} (Lote: {comp.inventario.descripInv if comp.inventario else 'N/A'})"
        } 
        for comp in componentes
    ]
    return JsonResponse(data, safe=False)
