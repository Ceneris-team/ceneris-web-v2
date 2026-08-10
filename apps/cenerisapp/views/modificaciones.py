"""Vistas de modificaciones de dispositivos.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from cenerisapp.forms import ModificacionAntiguaForm, ModificacionForm
from cenerisapp.models import (
    Componente,
    Dispositivo,
    FotoDispositivo,
    Modificacion,
    OtroComponente,
    Parte,
    Sensor,
)


@login_required
def cargar_historial_modificaciones(request):
    ModificacionFormSet = formset_factory(ModificacionAntiguaForm, extra=5)

    if request.method == 'POST':
        # CAMBIO IMPORTANTE: Agregar request.FILES para recibir las imágenes
        formset = ModificacionFormSet(request.POST, request.FILES)
        
        if formset.is_valid():
            registros_creados = 0
            registros_omitidos = 0

            for form in formset:
                if not form.cleaned_data:
                    continue

                data = form.cleaned_data
                
                nombre_sensor_saliente = data['sensor_saliente_nombre']
                nombre_sensor_entrante = data['sensor_entrante_nombre']

                # 1. Crear/Obtener Sensores (Igual que antes)
                sensor_saliente, _ = Sensor.objects.get_or_create(
                    nSerieActual=data['sensor_saliente_ns'],
                    defaults={'nomComp': nombre_sensor_saliente, 'tipGas': nombre_sensor_saliente, 'estComp': 'Inoperativo por cambio'}
                )

                sensor_entrante, _ = Sensor.objects.get_or_create(
                    nSerieActual=data['sensor_entrante_ns'],
                    defaults={'nomComp': nombre_sensor_entrante, 'tipGas': nombre_sensor_entrante}
                )
                
                # 2. Verificar duplicados (Igual que antes)
                if Modificacion.objects.filter(
                    id_dispositivo=data['dispositivo'],
                    fecInstalacionMod=data['fecInstalacionMod'],
                    sensor_saliente=sensor_saliente,
                    componente_entrante=sensor_entrante
                ).exists():
                    registros_omitidos += 1
                    continue 
                
                # 3. Crear Modificación
                nueva_modificacion = Modificacion.objects.create(
                    id_dispositivo=data['dispositivo'],
                    fecInstalacionMod=data['fecInstalacionMod'],
                    sensor_saliente=sensor_saliente,
                    componente_entrante=sensor_entrante,
                    id_trabajador=data['id_trabajador'],
                    MotivoCambio=data['MotivoCambio'],
                    tipoServicio='Reparacion'
                )

                # --- 4. NUEVA LÓGICA: GUARDAR LA FOTO Y VINCULARLA ---
                imagen = data.get('evidencia_foto')
                if imagen:
                    # Usamos el nombre del sensor entrante como 'tipo_foto' (ej. 'O2', 'LEL')
                    # Esto asegura que el Excel sepa dónde ponerla.
                    tipo_evidencia = nombre_sensor_entrante if nombre_sensor_entrante else "MANTENIMIENTO"
                    
                    FotoDispositivo.objects.create(
                        dispositivo=data['dispositivo'],
                        modificacion=nueva_modificacion, # ¡VINCULACIÓN CLAVE!
                        imagen_original=imagen,
                        tipo_foto=tipo_evidencia,
                        contexto='CARDEX' # Para que aparezca en el reporte
                    )

                registros_creados += 1
            
            messages.success(request, f"Proceso finalizado. {registros_creados} modificaciones con sus fotos creadas.")
            return redirect('cenerisapp:lista_modificaciones')
        
        else:
            messages.error(request, "Por favor, corrige los errores en los formularios.")
    
    else: 
        formset = ModificacionFormSet()

    context = {
        'titulo': 'Carga Rápida de Historial de Modificaciones',
        'formset': formset,
    }
    return render(request, 'modificaciones/cargar_historial.html', context)


@login_required
def lista_modificaciones(request):
    
    # --- 1. CAPTURAR VALORES DE FILTRO DE LA URL ---
    dispositivo_query = request.GET.get('dispositivo', '')
    trabajador_query = request.GET.get('trabajador', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    tipo_servicio = request.GET.get('tipo', '')

    # --- 2. CONSTRUIR EL QUERYSET BASE Y APLICAR FILTROS ---
    modificaciones = Modificacion.objects.select_related(
        'id_dispositivo', 'sensor_saliente', 'parte_saliente', 
        'componente_entrante', 'id_trabajador'
    ).all() # Empezamos con .all() y aplicamos filtros

    # Filtro por Dispositivo (busca por nombre o N/S)
    if dispositivo_query:
        modificaciones = modificaciones.filter(
            Q(id_dispositivo__nomDisp__icontains=dispositivo_query) |
            Q(id_dispositivo__num_serie__icontains=dispositivo_query)
        )

    # Filtro por Trabajador (busca por nombre)
    if trabajador_query:
        modificaciones = modificaciones.filter(id_trabajador__nomEmpleado__icontains=trabajador_query)
        
    # Filtro por Tipo de Servicio
    if tipo_servicio:
        modificaciones = modificaciones.filter(tipoServicio=tipo_servicio)

    # Filtro por Rango de Fechas
    if fecha_desde:
        modificaciones = modificaciones.filter(fecInstalacionMod__gte=fecha_desde)
    if fecha_hasta:
        modificaciones = modificaciones.filter(fecInstalacionMod__lte=fecha_hasta)

    # Aplicamos el ordenamiento al final
    modificaciones = modificaciones.order_by('-fecInstalacionMod')

    paginator = Paginator(modificaciones, 15) # 15 modificaciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # --- 3. PREPARAR DATOS PARA LOS DESPLEGABLES DE FILTRO ---
    opciones_tipo_servicio = Modificacion.objects.values_list('tipoServicio', flat=True).distinct()
    
    # --- 4. CONSTRUIR EL CONTEXTO FINAL ---
    context = {
        'page_obj': page_obj, 
        'titulo': 'Historial de Modificaciones y Servicios',
        'opciones_tipo_servicio': opciones_tipo_servicio,
        'filtros_aplicados': {
            'dispositivo': dispositivo_query,
            'trabajador': trabajador_query,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'tipo': tipo_servicio,
        }
    }
    return render(request, 'modificaciones/lista_modificaciones.html', context)


@login_required
def crear_modificacion(request):
    opciones_salientes = []

    if request.method == 'POST':
        dispositivo_id = request.POST.get('id_dispositivo')
        if dispositivo_id:
            try:
                # Se necesita Dispositivo.objects.get() para llenar opciones_salientes
                dispositivo = Dispositivo.objects.get(pk=dispositivo_id)
                for parte in dispositivo.partes.all(): 
                    opciones_salientes.append((f'parte_{parte.pk}', f"Parte: {parte.nomPart}"))
                for sensor in dispositivo.sensor_set.all():
                    opciones_salientes.append((f'sensor_{sensor.pk}', f"Sensor: {sensor.nomComp}"))
            except Dispositivo.DoesNotExist:
                pass

        form = ModificacionForm(request.POST, opciones_salientes=opciones_salientes)
        
        if form.is_valid():
            modificacion = form.save(commit=False)
            
            dispositivo = modificacion.id_dispositivo
            item_saliente_str = form.cleaned_data.get('item_saliente')
            tipo_saliente, pk_saliente = item_saliente_str.split('_')
            modificacion.fecInstalacionMod = date.today()
            
            # Recuperamos los nuevos campos del formulario
            pk_entrante = form.cleaned_data.get('reemplazo_id')
            n_serie_nuevo = form.cleaned_data.get('n_serie_reemplazo')

            componente_entrante = None
            if pk_entrante:
                componente_entrante = get_object_or_404(Componente, pk=pk_entrante)
                
            # --- LÓGICA DE ACTUALIZACIÓN DEL N/S ---
            if componente_entrante and n_serie_nuevo:
                # Asignamos el número de serie al componente seleccionado del stock
                componente_entrante.nSerieActual = n_serie_nuevo
                componente_entrante.save() # Guardamos el cambio en el componente

            # --- Lógica para ITEM SALIENTE (Parte o Sensor) ---
            if tipo_saliente == 'parte':
                parte_afectada = get_object_or_404(Parte, pk=pk_saliente)
                modificacion.parte_saliente = parte_afectada
                
                # Guardamos la modificación ANTES de consumir el componente
                modificacion.save()
                
                # Si se usó un componente del stock, se consume (descuenta)
                if componente_entrante:
                    nombre_componente = componente_entrante.nomComp
                    componente_entrante.delete() # Se descuenta del stock
                    messages.success(request, f"Servicio registrado para la parte '{parte_afectada.nomPart}'. El componente '{nombre_componente}' con N/S '{n_serie_nuevo}' fue descontado del stock.")
                else:
                    messages.success(request, f"Servicio registrado para la parte '{parte_afectada.nomPart}'.")
                    
            elif tipo_saliente == 'sensor':
                sensor_saliente = get_object_or_404(Sensor, pk=pk_saliente)
                modificacion.sensor_saliente = sensor_saliente
                
                if componente_entrante and hasattr(componente_entrante, 'sensor'):
                    # El 'componente_entrante' ahora ya tiene su N/S guardado
                    
                    # 1. Marcar el sensor saliente como retirado/inoperativo
                    sensor_saliente.dispositivo_instalado = None
                    sensor_saliente.estComp = 'Inoperativo por cambio'
                    sensor_saliente.save()
                    
                    # 2. Instalar el sensor entrante (Componente -> Sensor)
                    sensor_entrante = componente_entrante.sensor
                    sensor_entrante.dispositivo_instalado = dispositivo
                    sensor_entrante.fecInst = date.today()
                    sensor_entrante.save()
                    
                    # 3. Registrar el sensor entrante en la modificación
                    modificacion.componente_entrante = sensor_entrante

                    messages.success(request, f"Reparación registrada. El sensor '{sensor_saliente.nomComp}' fue reemplazado por N/S '{sensor_entrante.nSerieActual}'.")
                else:
                    messages.success(request, f"Servicio registrado para el sensor '{sensor_saliente.nomComp}'.")
                
                # Guardar la modificación final
                modificacion.save()
                
                # Mensaje final y redirección con enlace de foto
                url_fotos = reverse('cenerisapp:gestionar_fotos_dispositivo', args=[dispositivo.id_dispositivo])
                mensaje = format_html(
                    "Reparación registrada exitosamente. <strong>¡No olvides subir la foto de evidencia!</strong> <a href='{}' class='alert-link'>Cargar foto ahora</a>.",
                    url_fotos
                )
                messages.success(request, mensaje)
                
            return redirect('cenerisapp:lista_modificaciones')
        else:
            # Reutiliza las opciones salientes si el formulario falla, para que no se pierdan
            # (Aunque ModificacionForm debería manejar esto si se pasa en la inicialización)
            messages.error(request, "Por favor, corrige los errores en el formulario.")
            
    else:
        form = ModificacionForm()

    context = {
        'form': form,
        'titulo': 'Registrar Nueva Reparación / Servicio'
    }
    return render(request, 'modificaciones/crear_modificacion.html', context)


@login_required
def editar_modificacion(request, modificacion_id):
    print("\n" + "="*50)
    print(f"INICIO VISTA 'editar_modificacion' - MÉTODO: {request.method}")
    print("="*50)

    modificacion = get_object_or_404(Modificacion, pk=modificacion_id)
    print(f"[PASO 1] Objeto a editar cargado: Modificacion #{modificacion.id_modificacion}")

    opciones = []
    dispositivo = modificacion.id_dispositivo
    
    if dispositivo:
        print(f"[PASO 2] Dispositivo asociado: '{dispositivo}' (ID: {dispositivo.pk})")
        sensores = Sensor.objects.filter(dispositivo_instalado=dispositivo)
        partes = Parte.objects.filter(id_dispositivo=dispositivo)
        
        for s in sensores:
            opciones.append((f'sensor_{s.pk}', f"Sensor: {s.nomComp} ({s.nSerieActual})"))
        for p in partes:
            opciones.append((f'parte_{p.id_parte}', f"Parte: {p.nomPart}"))
        
        print(f"[PASO 3] Lista de 'opciones' generada: {opciones}")
    else:
        print("[PASO 2] ADVERTENCIA: La modificación no tiene un dispositivo asociado.")

    if request.method == 'POST':
        print("\n--- INICIO PROCESO POST ---")
        
        print("[PASO 4] Instanciando el formulario con los datos del POST.")
        form = ModificacionForm(request.POST, instance=modificacion, opciones_involucrados=opciones)
        
        print("[PASO 5] Verificando si el formulario es válido (form.is_valid())...")
        is_valid = form.is_valid()

        if is_valid:
            print("\n  /------------------------------------\\")
            print("  |   ¡EL FORMULARIO ES VÁLIDO!    |")
            print("  \\------------------------------------/")
            form.save()
            messages.success(request, f"Modificación #{modificacion.id_modificacion} actualizada exitosamente.")
            return redirect('cenerisapp:lista_modificaciones')
        else:
            print("\n  /--------------------------------------\\")
            print("  |   ¡EL FORMULARIO NO ES VÁLIDO!     |")
            print("  \\--------------------------------------/")
            print("[PASO 6] Errores del formulario:")
            
            print(form.errors.as_json())
            messages.error(request, "Por favor, corrige los errores en el formulario.")

    else: # Petición GET
        print("\n--- INICIO PROCESO GET ---")
        form = ModificacionForm(instance=modificacion, opciones_involucrados=opciones)
        
        if modificacion.id_sensor:
            initial_value = f'sensor_{modificacion.id_sensor.pk}'
            form.fields['componente_o_parte_involucrada'].initial = initial_value
            print(f"[PASO 4 GET] Pre-seleccionando valor inicial: {initial_value}")
        elif modificacion.id_parte:
            initial_value = f'parte_{modificacion.id_parte.pk}'
            form.fields['componente_o_parte_involucrada'].initial = initial_value
            print(f"[PASO 4 GET] Pre-seleccionando valor inicial: {initial_value}")

    context = {
        'form': form,
        'modificacion': modificacion,
        'titulo': f'Editar Modificación #{modificacion.id_modificacion}'
    }
    print("--- FIN DE LA VISTA. RENDERIZANDO PLANTILLA ---")
    return render(request, 'modificaciones/editar_modificacion.html', context)


@login_required
def get_ns_por_tipo_api(request):
    """
    Dado un nombre de componente, devuelve los N/S disponibles y operativos.
    """
    nombre_componente = request.GET.get('tipo', '')
    results = []
    
    if nombre_componente:
        
        

        
        sensores_disponibles = Sensor.objects.filter(
            nomComp=nombre_componente,
            dispositivo_instalado__isnull=True,
            estComp='Operativo'
        )
        
        
        otros_disponibles = OtroComponente.objects.filter(
            nomComp=nombre_componente,
            estComp='Operativo'
        )

        
        
        componentes_combinados = list(sensores_disponibles) + list(otros_disponibles)
        
        
        componentes_combinados.sort(key=lambda x: x.nSerieActual)

        
        results = [{
            'id': c.pk, 
            'text': f"{c.nSerieActual} (ID: {c.pk})" # Añadir el ID puede ayudar a depurar
        } for c in componentes_combinados]
        
    return JsonResponse(results, safe=False)


@login_required # <-- ¡AÑADE ESTO! Es crucial para la seguridad y para evitar errores.
def get_partes_y_sensores_por_dispositivo(request):
    dispositivo_id = request.GET.get('dispositivo_id')
    opciones = []
    
    if not dispositivo_id:
        # Devuelve un JSON de error si no se proporciona el ID
        return JsonResponse({'error': 'No se proporcionó dispositivo_id'}, status=400)

    try:
        # Verificamos que el dispositivo exista
        dispositivo = Dispositivo.objects.get(pk=dispositivo_id)
        
        partes = Parte.objects.filter(id_dispositivo=dispositivo) # Es más limpio pasar el objeto
        for p in partes:
            opciones.append({'id': f'parte_{p.id_parte}', 'nombre': f"Parte: {p.nomPart}"})

        sensores = Sensor.objects.filter(dispositivo_instalado=dispositivo) # Igual aquí
        for s in sensores:
            opciones.append({'id': f'sensor_{s.pk}', 'nombre': f"Sensor: {s.nomComp} ({s.nSerieActual})"})
            
    except Dispositivo.DoesNotExist:
        # Devuelve un JSON de error si el dispositivo no existe
        return JsonResponse({'error': 'Dispositivo no encontrado'}, status=404)

    return JsonResponse(opciones, safe=False)
