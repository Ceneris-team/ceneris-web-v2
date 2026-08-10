"""Vistas de registros de entrada/salida, reportes y ocurrencias.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import calendar

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from cenerisapp.forms import (
    EmpleadoRapidoForm,
    OcurrenciaForm,
    RegistroSalidaForm,
    ReporteForm,
)
from cenerisapp.models import (
    AreaTrabajo,
    Dispositivo,
    Empleado,
    Empresa,
    Ocurrencia,
    OtroComponente,
    Registro,
    Reporte,
    ReporteDiario,
    Sensor,
)


@login_required
def muro_ocurrencias(request):
    # Procesamos el envío del formulario si la petición es POST
    if request.method == 'POST':
        form = OcurrenciaForm(request.POST)
        if form.is_valid():
            # Creamos la instancia en memoria
            nueva_ocurrencia = form.save(commit=False)
            # ¡Asignamos el usuario de la sesión actual como autor!
            nueva_ocurrencia.autor = request.user
            # Ahora guardamos en la base de datos
            nueva_ocurrencia.save()
            
            messages.success(request, "Ocurrencia publicada exitosamente.")
            # Redirigimos a la misma página para ver el nuevo comentario y limpiar el formulario
            return redirect('cenerisapp:muro_ocurrencias')
        else:
            messages.error(request, "El mensaje no puede estar vacío.")

    # Para peticiones GET (o si el POST falla), preparamos la página
    
    # Obtenemos todas las ocurrencias para mostrarlas
    # Usamos select_related para optimizar la obtención del nombre del autor
    ocurrencias = Ocurrencia.objects.all().select_related('autor')
    
    # Creamos una instancia vacía del formulario para mostrarla en la página
    form = OcurrenciaForm()
    
    context = {
        'titulo': 'Muro de Ocurrencias y Noticias',
        'form': form,
        'ocurrencias': ocurrencias,
    }
    
    return render(request, 'ocurrencias/muro_ocurrencias.html', context)


@login_required
def borrar_ocurrencia(request, ocurrencia_id):
    # Solo aceptamos peticiones POST para esta acción por seguridad.
    if request.method != 'POST':
        # Si alguien intenta acceder por GET, le negamos el acceso.
        return HttpResponseForbidden("Método no permitido.")

    # 1. Obtenemos la ocurrencia que se quiere borrar.
    ocurrencia = get_object_or_404(Ocurrencia, pk=ocurrencia_id)
    
    # --- LA LÓGICA DE SEGURIDAD MÁS IMPORTANTE ---
    # 2. Verificamos si el usuario de la sesión actual es el autor de la ocurrencia.
    if ocurrencia.autor != request.user:
        # Si no es el autor, le negamos el permiso.
        messages.error(request, "No tienes permiso para borrar esta ocurrencia.")
        return HttpResponseForbidden("No tienes permiso para realizar esta acción.")
    
    # 3. Si las comprobaciones pasan, procedemos a borrar.
    ocurrencia.delete()
    
    messages.success(request, "Ocurrencia borrada exitosamente.")
    
    # 4. Redirigimos de vuelta al muro de ocurrencias.
    return redirect('cenerisapp:muro_ocurrencias')


@login_required
def gestor_reportes(request, tipo_reporte):
    # Validamos que el tipo de reporte sea válido
    tipos_validos = [choice[0] for choice in ReporteDiario.TIPO_CHOICES]
    tipo_reporte_upper = tipo_reporte.upper()
    if tipo_reporte_upper not in tipos_validos:
        raise Http404("Tipo de reporte no válido.")

    # Manejo de la carga de archivos (AJAX)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        fecha_str = request.POST.get('fecha')
        archivo = request.FILES.get('archivo')

        if not fecha_str or not archivo:
            return JsonResponse({'error': 'Faltan datos.'}, status=400)
        
        try:
            fecha_obj = date.fromisoformat(fecha_str)
            tipo_reporte_upper = tipo_reporte.upper()

            # --- LÓGICA DE GUARDADO CORREGIDA Y ROBUSTA ---
            
            # 1. Usamos get_or_create para ver si ya existe un registro.
            #    Esto es más explícito que update_or_create para FileFields.
            reporte, created = ReporteDiario.objects.get_or_create(
                tipo_reporte=tipo_reporte_upper,
                fecha=fecha_obj,
                defaults={'archivo': archivo} # Asignamos el archivo solo si se está creando
            )
            
            # 2. Si el registro ya existía, actualizamos el archivo explícitamente.
            if not created:
                # Opcional: Borramos el archivo antiguo de S3 antes de subir el nuevo.
                # Esto evita tener archivos huérfanos.
                if reporte.archivo:
                    reporte.archivo.delete(save=False) # save=False evita una consulta extra
                
                # Asignamos el nuevo archivo y guardamos.
                reporte.archivo = archivo
                reporte.save()
            
            # --- FIN DE LA LÓGICA DE GUARDADO ---
            
            # La URL del archivo ahora se obtendrá correctamente desde S3 en producción.
            file_url = reporte.archivo.url

            return JsonResponse({
                'status': 'ok',
                'message': 'Archivo cargado exitosamente.',
                'file_url': file_url
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Lógica para la vista normal (GET)
    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Construir el calendario
    cal = calendar.Calendar()
    dias_del_mes = cal.monthdatescalendar(year, month)

    # Obtener los archivos ya cargados para este mes y tipo
    archivos_cargados = ReporteDiario.objects.filter(
        tipo_reporte=tipo_reporte.upper(),
        fecha__year=year,
        fecha__month=month
    ) # Obtenemos los objetos completos

    
    # Convertir a un diccionario para búsqueda rápida en la plantilla
    mapa_archivos = {}
    for reporte in archivos_cargados:
        if reporte.archivo:
            # Para cada reporte, llamamos a .url para obtener la URL completa de S3
            mapa_archivos[reporte.fecha] = reporte.archivo.url


    choices_dict = dict(ReporteDiario.TIPO_CHOICES)
    # Obtenemos el texto legible usando la clave
    titulo_legible = choices_dict.get(tipo_reporte_upper, "Reporte Desconocido")

    context = {
        'titulo': f'Gestor de {titulo_legible}',
        'tipo_reporte': tipo_reporte,
        'dias_del_mes': dias_del_mes,
        'current_month': date(year, month, 1),
        'mapa_archivos': mapa_archivos,
        'es_quincenal': tipo_reporte.upper() == 'QUINCENAL',
    }
    
    return render(request, 'archivos/gestor_reportes.html', context)


@login_required
def registro_rapido_in_out(request):
    
    # --- MANEJO DE CONFIGURACIÓN DE SESIÓN (Turno) ---
    if request.method == 'POST' and ('set_turno' in request.POST or 'set_config' in request.POST):
        # Turno
        turno = request.POST.get('turno')
        if turno in ['A', 'B']: request.session['turno_activo'] = turno
        else: request.session.pop('turno_activo', None)
        
        # Área de Trabajo
        area_id = request.POST.get('area_trabajo')
        if area_id: request.session['area_trabajo_id'] = area_id
        else: request.session.pop('area_trabajo_id', None)

        # Punto Exacto
        punto_id = request.POST.get('punto_exacto')
        if punto_id: request.session['punto_exacto_id'] = punto_id
        else: request.session.pop('punto_exacto_id', None)
        
        messages.success(request, "Configuración de sesión actualizada.")
        return redirect('cenerisapp:registro_rapido_in_out')

    # --- FINALIZAR PRÉSTAMO Y LIMPIAR SESIÓN DE TRABAJADOR ---
    if request.method == 'POST' and 'end_prestamo' in request.POST:
        request.session.pop('receptor_prestamo_id', None)
        request.session.pop('receptor_prestamo_nombre', None)
        messages.info(request, "Préstamo finalizado. Escanee el DNI de un nuevo trabajador.")
        return redirect('cenerisapp:registro_rapido_in_out')
        
    # --- PROCESO DE ESCANEO (TRABAJADOR O DISPOSITIVO) ---
    if request.method == 'POST' and 'codigo_escaneado' in request.POST:
        codigo = request.POST.get('codigo_escaneado', '').strip()
        
        if not codigo:
            messages.warning(request, "El campo de escaneo estaba vacío.")
            return redirect('cenerisapp:registro_rapido_in_out')
        
        # Intentamos identificar si es un DNI (8 dígitos numéricos)
        if len(codigo) == 8 and codigo.isdigit():
            # --- LÓGICA PARA FIJAR TRABAJADOR POR DNI ---
            try:
                receptor = Empleado.objects.get(dni=codigo)
                request.session['receptor_prestamo_id'] = receptor.pk
                request.session['receptor_prestamo_nombre'] = receptor.nomEmpleado
                messages.success(request, f"Trabajador receptor fijado: {receptor.nomEmpleado}. Ahora puede escanear los dispositivos.")
            except Empleado.DoesNotExist:
                messages.error(request, f"No se encontró ningún empleado con el DNI '{codigo}'.")
        
        else: # Si no es un DNI, asumimos que es un N° de Serie de dispositivo
            # --- LÓGICA DE PRÉSTAMO/DEVOLUCIÓN DE DISPOSITIVO ---
            try:
                dispositivo = Dispositivo.objects.get(num_serie=codigo)
                registro_abierto = Registro.objects.filter(id_dispositivo=dispositivo, fecDevol__isnull=True).first()
                
                if registro_abierto: # Lógica de DEVOLUCIÓN
                    registro_abierto.fecDevol = timezone.now()
                
                    # 2. Asignamos el operador actual como el que recibe la devolución.
                    registro_abierto.operador_receptor = request.user.empleado
                    
                    # 3. Guardamos los cambios en la base de datos.
                    registro_abierto.save()
    
                    messages.success(request, f"ENTRADA: Dispositivo '{dispositivo.nomDisp}' devuelto.")
                else: # Lógica de PRÉSTAMO
                    receptor_id_sesion = request.session.get('receptor_prestamo_id')
                    turno_sesion = request.session.get('turno_activo')
                    area_id_sesion = request.session.get('area_trabajo_id') # <-- Leemos de la sesión
                    punto_id_sesion = request.session.get('punto_exacto_id')

                    if not receptor_id_sesion:
                        messages.error(request, "Error: Debe escanear primero el DNI de un trabajador antes de prestar un dispositivo.")
                    elif not turno_sesion:
                        messages.error(request, "Error: Debe seleccionar un turno antes de registrar un préstamo.")
                    elif not area_id_sesion: # <-- Nueva validación
                        messages.error(request, "Error: Debe seleccionar un Área de Operación.")
                    else:
                        operador = request.user.empleado
                        receptor = Empleado.objects.get(pk=receptor_id_sesion)
                        Registro.objects.create(
                            id_dispositivo=dispositivo,
                            operador_responsable=operador,
                            trabajador_receptor=receptor,
                            turno=turno_sesion, # ¡Asignamos el turno de la sesión!
                            area_trabajo_operacion_id=area_id_sesion, # <-- Asignamos
                            punto_exacto_operacion_id=punto_id_sesion, # <-- Asignamos
                        )
                        messages.success(request, f"SALIDA: Dispositivo '{dispositivo.nomDisp}' prestado a {receptor.nomEmpleado} en turno {turno_sesion}.")
            
            except Dispositivo.DoesNotExist:
                messages.error(request, f"Dispositivo con N/S '{codigo}' no encontrado.")
            except Empleado.DoesNotExist:
                messages.error(request, "Error de sesión. Por favor, vuelva a escanear al trabajador.")
        
        return redirect('cenerisapp:registro_rapido_in_out')
    
    # --- NUEVA LÓGICA PARA REGISTRAR EMPLEADO RÁPIDO ---
    empleado_form = EmpleadoRapidoForm() # Inicializamos el form
    if request.method == 'POST' and 'registrar_empleado' in request.POST:
        empleado_form = EmpleadoRapidoForm(request.POST)
        if empleado_form.is_valid():
            try:
                empresa_id = empleado_form.cleaned_data.get('empresa_id')
                empresa_nombre = empleado_form.cleaned_data.get('empresa_nombre')
                
                # Buscamos o creamos la empresa
                if empresa_id:
                    empresa = Empresa.objects.get(pk=empresa_id)
                else:
                    # get_or_create para evitar duplicados si se escribe el nombre exacto
                    empresa, created = Empresa.objects.get_or_create(
                        nombreE=empresa_nombre,
                        defaults={
                            # Rellenamos campos obligatorios con valores por defecto si los hay
                            'abreviacion': empresa_nombre[:20], 
                            'direccion': 'N/A',
                            'departamento': 'N/A',
                            'telefono': 'N/A',
                            'ruc': '00000000000',
                        }
                    )
                
                # Creamos el nuevo empleado
                nuevo_empleado = Empleado.objects.create(
                    empresa=empresa,
                    nomEmpleado=empleado_form.cleaned_data.get('nomEmpleado'),
                    dni=empleado_form.cleaned_data.get('dni'),
                    puesto=empleado_form.cleaned_data.get('puesto')
                )
                
                messages.success(request, f"Empleado '{nuevo_empleado.nomEmpleado}' creado y asignado a la empresa '{empresa.nombreE}'.")
                
                # Fijamos al nuevo empleado como el receptor activo en la sesión
                request.session['receptor_prestamo_id'] = nuevo_empleado.pk
                request.session['receptor_prestamo_nombre'] = nuevo_empleado.nomEmpleado

            except Exception as e:
                messages.error(request, f"Error al crear el empleado: {e}")
            
            return redirect('cenerisapp:registro_rapido_in_out')

    # --- VISTA GET (Mostrar la página) ---
    empleados_receptores = Empleado.objects.all().order_by('nomEmpleado')
    receptor_id_activo = request.session.get('receptor_prestamo_id')
    turno_activo = request.session.get('turno_activo')
    receptor_nombre_activo = request.session.get('receptor_prestamo_nombre')
    area_activa_id = request.session.get('area_trabajo_id')
    punto_activo_id = request.session.get('punto_exacto_id')

    query = request.GET.get('q', '') # Capturamos el parámetro de búsqueda 'q'
    
    # Queryset base
    historial_completo = Registro.objects.select_related(
        'id_dispositivo', 'trabajador_receptor'
    )
    
    if query:
        # Filtramos por el número de serie del dispositivo relacionado
        historial_completo = historial_completo.filter(id_dispositivo__num_serie__icontains=query)

    # --- 2. ORDENAMIENTO INTELIGENTE ---
    # Ordena por 'fecDevol' ascendente, poniendo los NULL (no devueltos) primero.
    # Luego, como segundo criterio, ordena por fecha de registro descendente.
    historial_completo = historial_completo.order_by(F('fecDevol').asc(nulls_first=True), '-fecRegistro')
    
    # --- 3. LÓGICA DE PAGINACIÓN ---
    paginator = Paginator(historial_completo, 15) # 15 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    hoy = timezone.now().date()
    
    # 1. Obtenemos todos los registros de SALIDA que ocurrieron hoy.
    salidas_hoy_qs = Registro.objects.filter(fecRegistro__date=hoy)
    
    # 2. Agrupamos estos registros por el nombre del dispositivo para obtener el TOTAL de salidas.
    #    .values() agrupa, .annotate() cuenta.
    salidas_hoy_por_modelo = salidas_hoy_qs.values('id_dispositivo__nomDisp') \
        .annotate(total_salidas=Count('id_dispositivo__nomDisp')) \
        .order_by('id_dispositivo__nomDisp')

    # 3. Obtenemos los registros de SALIDA de hoy que AÚN NO HAN SIDO DEVUELTOS.
    pendientes_hoy_qs = salidas_hoy_qs.filter(fecDevol__isnull=True)
    
    # 4. Agrupamos estos para obtener el TOTAL de pendientes.
    pendientes_hoy_por_modelo = pendientes_hoy_qs.values('id_dispositivo__nomDisp') \
        .annotate(total_pendientes=Count('id_dispositivo__nomDisp')) \
        .order_by('id_dispositivo__nomDisp')
        
    # 5. Combinamos los dos resultados en una sola estructura de datos para la plantilla.
    #    Usamos un diccionario para facilitar la combinación.
    kpis_por_modelo = {
        item['id_dispositivo__nomDisp']: {'salidas': item['total_salidas'], 'pendientes': 0}
        for item in salidas_hoy_por_modelo
    }
    
    for item in pendientes_hoy_por_modelo:
        if item['id_dispositivo__nomDisp'] in kpis_por_modelo:
            kpis_por_modelo[item['id_dispositivo__nomDisp']]['pendientes'] = item['total_pendientes']

    # Mostramos los dispositivos actualmente prestados a esta persona
    prestamos_activos = []
    if receptor_id_activo:
        prestamos_activos = Registro.objects.filter(
            trabajador_receptor_id=receptor_id_activo,
            fecDevol__isnull=True
        ).select_related('id_dispositivo').order_by('-fecRegistro')
    
    todas_las_areas = AreaTrabajo.objects.all().order_by('nombreA')
    
    context = {
        'titulo': 'Registro Rápido IN/OUT (Modo Lote)',
        'turno_choices': Registro._meta.get_field('turno').choices,
        'turno_activo': turno_activo,
        'todas_las_areas': todas_las_areas,
        'area_activa_id': int(area_activa_id) if area_activa_id else None,
        'punto_activo_id': int(punto_activo_id) if punto_activo_id else None,
        'empleados_receptores': empleados_receptores,
        'receptor_id_activo': receptor_id_activo,
        'receptor_nombre_activo': receptor_nombre_activo,
        'prestamos_activos': prestamos_activos,
        'page_obj': page_obj, # Reemplaza a 'ultimos_movimientos'
        'query': query, # Para que el buscador recuerde el término buscado

        'kpis_por_modelo': kpis_por_modelo,
        'fecha_hoy': hoy,
        'empleado_form': empleado_form,
    }
    return render(request, 'registros/registro_rapido.html', context)


@login_required
def flujo(request): 
    if request.method == 'POST':
        form = RegistroSalidaForm(request.POST)
        
        if form.is_valid():
            # ¡La magia ocurre aquí!
            # El form.cleaned_data ya está validado, y la instancia del modelo ya
            # tiene id_dispositivo_id o id_componente_id asignados.
            registro = form.save(commit=False)
            
            # --- LÓGICA SIMPLIFICADA ---
            if registro.id_dispositivo:
                dispositivo_prestado = registro.id_dispositivo
                if registro.trabajador_receptor and hasattr(registro.trabajador_receptor, 'empresa') and registro.trabajador_receptor.empresa:
                    dispositivo_prestado.id_empresa = registro.trabajador_receptor.empresa
                    dispositivo_prestado.save()
                    registro.save()
                    messages.success(request, f"Salida registrada para el dispositivo '{dispositivo_prestado.nomDisp}'.")
                    return redirect('cenerisapp:lista_registros')
                else:
                    messages.error(request, "El trabajador seleccionado no tiene una empresa asignada.")

            elif registro.id_componente:
                componente_prestado = registro.id_componente
                if hasattr(componente_prestado, 'otrocomponente'):
                    componente_prestado.otrocomponente.estComp = 'Prestado'
                    componente_prestado.otrocomponente.save()
                elif hasattr(componente_prestado, 'sensor'):
                    componente_prestado.sensor.estComp = 'Prestado'
                    componente_prestado.sensor.save()
                
                registro.save()
                messages.success(request, f"Salida registrada y stock actualizado para el componente '{componente_prestado.nomComp}'.")
                return redirect('cenerisapp:lista_registros')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else: 
        form = RegistroSalidaForm()
 
    context = {
        'form': form,
        'titulo': 'Registro de Prestamo de Dispositivos'
    }
    return render(request, 'flujo/flujo.html', context)


@login_required
def lista_registros(request):
    registros_qs = Registro.objects.select_related('trabajador_receptor', 'operador_responsable', 'id_dispositivo').order_by('-fecRegistro')
   
    
    registros_procesados = []
    for registro in registros_qs:
        duracion_en_horas = None 
        if registro.durPrestamo:
            
            
            total_segundos = registro.durPrestamo.total_seconds()
            duracion_en_horas = total_segundos / 3600
       
        
        registro.duracion_horas = duracion_en_horas
        registros_procesados.append(registro)
 
    context = {
        'registros': registros_procesados, 
        'titulo': 'Historial de Prestamo de Dispositivos'
    }
    return render(request, 'flujo/lista_registros.html', context)


@require_POST
def marcar_operativo(request, tipo_item, item_id):
    """
    Cambia el estado de un ítem específico a 'Operativo'.
    Recibe el tipo de ítem y su ID desde la URL.
    """
    try:
        if tipo_item == 'dispositivo':
            # Usamos el nombre de la clave primaria explícita: id_dispositivo
            item = get_object_or_404(Dispositivo, id_dispositivo=item_id)
            item.estadoD = 'Operativo'
            item.save()
            messages.success(request, f'El dispositivo "{item}" ha sido marcado como Operativo.')

        elif tipo_item == 'sensor':
            # Usamos el nombre de la clave primaria explícita: id_componente
            item = get_object_or_404(Sensor, id_componente=item_id)
            item.estComp = 'Operativo'
            item.save()
            messages.success(request, f'El sensor "{item}" ha sido marcado como Operativo.')

        # Cambiamos 'parte' por 'otrocomponente' para que coincida con el modelo
        elif tipo_item == 'otrocomponente':
            # Usamos el nombre de la clave primaria explícita: id_componente
            item = get_object_or_404(OtroComponente, id_componente=item_id)
            item.estComp = 'Operativo'
            item.save()
            messages.success(request, f'El componente "{item}" ha sido marcado como Operativo.')

        else:
            messages.error(request, 'Tipo de ítem no válido.')

    except Exception as e:
        messages.error(request, f'Ocurrió un error al actualizar el ítem: {e}')

    return redirect('cenerisapp:vista_inoperativos')


@login_required
def registrar_devolucion(request, registro_id):
    
    if request.method == 'POST':
        try:

            registro = Registro.objects.get(pk=registro_id, fecDevol__isnull=True)
            
            
            registro.fecDevol = timezone.now()
            
            
            duracion = registro.fecDevol - registro.fecRegistro
            registro.durPrestamo = duracion

            if registro.id_componente:
                componente_devuelto = registro.id_componente
                # Lo devolvemos al stock marcándolo como 'Operativo'
                # (Aquí podrías añadir un formulario para que el usuario confirme
                # si el componente volvió en buen estado o inoperativo)
                componente_devuelto.estComp = 'Operativo'
                componente_devuelto.save()
            
            # (Aquí podrías añadir lógica para el dispositivo, como cambiar su 'id_empresa' a NULL)
            elif registro.id_dispositivo:
                dispositivo_devuelto = registro.id_dispositivo
                dispositivo_devuelto.id_empresa = None # Vuelve a ser propiedad interna
                dispositivo_devuelto.save()

            registro.save()
            
            
            horas_prestamo = duracion.total_seconds() / 3600
            messages.success(request, f'Devolución registrada. Duración: {horas_prestamo:.2f} horas.')

        except Registro.DoesNotExist:
            messages.error(request, 'El registro no es válido o ya ha sido devuelto.')

    
    return redirect('cenerisapp:lista_registros')


@login_required
def crear_reporte(request):
    if request.method == 'POST':
        form = ReporteForm(request.POST)
        if form.is_valid():
            reporte = form.save(commit=False)
            
            reporte.fecReport = date.today()
            if hasattr(request.user, 'empleado'):
                reporte.id_trabajador = request.user.empleado
            
            nuevo_estado_seleccionado = form.cleaned_data.get('nuevo_estado')
            
            # La lógica de actualización del estado se mantiene igual
            if reporte.id_dispositivo:
                reporte.id_dispositivo.estadoD = nuevo_estado_seleccionado
                
                # --- ¡CAMBIO CLAVE AQUÍ! ---
                # Le decimos a Django que solo guarde el campo 'estadoD'.
                reporte.id_dispositivo.save(update_fields=['estadoD']) 
                
                item_afectado = reporte.id_dispositivo
                
            elif reporte.id_otro_componente:
                reporte.id_otro_componente.estComp = nuevo_estado_seleccionado
                
                # --- ¡CAMBIO CLAVE AQUÍ! ---
                reporte.id_otro_componente.save(update_fields=['estComp'])
                
                item_afectado = reporte.id_otro_componente
            
            reporte.save()
            
            messages.success(request, f"Reporte guardado y estado de '{item_afectado}' actualizado a '{nuevo_estado_seleccionado}'.")
            return redirect('cenerisapp:lista_reportes')
        # Si el form no es válido, Django automáticamente pasará el form con los errores
        # a la plantilla, y ahora sí se mostrarán debajo del campo correcto.
        else: 
            print("========================================")
            print("El formulario no es válido. Errores:")
            print(form.errors)
            print("========================================")

            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = ReporteForm()

    context = {'form': form, 'titulo': 'Registrar Reporte de Daño o Pérdida'}
    return render(request, 'reportes/crear_reporte.html', context)


@login_required
def lista_reportes(request):
    
    # --- 1. CAPTURAR VALORES DE FILTRO ---
    dispositivo_q = request.GET.get('dispositivo', '')
    trabajador_q = request.GET.get('trabajador', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # --- 2. CONSTRUIR QUERYSET BASE Y FILTRAR ---
    reportes_qs = Reporte.objects.select_related(
        'id_dispositivo', 'id_otro_componente', 'id_trabajador'
    ).all()
    
    if dispositivo_q:
        reportes_qs = reportes_qs.filter(
            Q(id_dispositivo__nomDisp__icontains=dispositivo_q) |
            Q(id_dispositivo__num_serie__icontains=dispositivo_q) |
            Q(id_otro_componente__nomComp__icontains=dispositivo_q) |
            Q(id_otro_componente__nSerieActual__icontains=dispositivo_q)
        )

    if trabajador_q:
        reportes_qs = reportes_qs.filter(id_trabajador__nomEmpleado__icontains=trabajador_q)
        
    if fecha_desde:
        reportes_qs = reportes_qs.filter(fecReport__gte=fecha_desde)
    if fecha_hasta:
        reportes_qs = reportes_qs.filter(fecReport__lte=fecha_hasta)
        
    # Ordenar al final
    reportes_qs = reportes_qs.order_by('-fecReport')

    # --- 3. APLICAR PAGINACIÓN ---
    paginator = Paginator(reportes_qs, 10) # 10 reportes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # --- 4. CONTEXTO ---
    context = {
        'page_obj': page_obj,
        'titulo': 'Reportes de Daño o Pérdida',
        'filtros_aplicados': {
            'dispositivo': dispositivo_q,
            'trabajador': trabajador_q,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    return render(request, 'reportes/lista_reportes.html', context)


@login_required
def editar_reporte(request, reporte_id):
    
    reporte = get_object_or_404(Reporte, pk=reporte_id)

    if request.method == 'POST':
        
        
        form = ReporteForm(request.POST, instance=reporte)
        
        if form.is_valid():
            form.save() # Guarda los cambios en el objeto 'reporte'
            messages.success(request, f"Reporte #{reporte.id_reporte} actualizado exitosamente.")
            return redirect('cenerisapp:lista_reportes') # Redirigir a la lista de reportes
        else:
            
            messages.error(request, "Por favor, corrige los errores a continuación.")

    else: # Petición GET
        
        
        form = ReporteForm(instance=reporte)

    context = {
        'form': form,
        'reporte': reporte, # Pasamos el objeto para usarlo en el título, etc.
        'titulo': f'Editar Reporte #{reporte.id_reporte}'
    }
    return render(request, 'reportes/editar_reporte.html', context)
