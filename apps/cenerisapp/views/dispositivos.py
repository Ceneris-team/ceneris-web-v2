"""Vistas de gestion de dispositivos y sus observaciones/fotos.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import json

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from cenerisapp.forms import (
    BaseSensorParaDispositivoFormSet,
    DispositivoForm,
    FotoDispositivoForm,
    ParteFormSet,
    SensorParaDispositivoForm,
)
from cenerisapp.models import Dispositivo, FotoDispositivo, ObservacionDispositivo, PuntoExacto


def buscar_puntos_exactos_api(request):
    area_id = request.GET.get('area_id')
    if not area_id:
        return JsonResponse([], safe=False)
    
    puntos = PuntoExacto.objects.filter(area_trabajo_id=area_id).values('id', 'nombre_punto')
    return JsonResponse(list(puntos), safe=False)


@login_required
def get_observaciones_json(request, dispositivo_id):
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    observaciones = dispositivo.observaciones.all().values(
        'comentario', 
        'fecha_creacion', 
        'autor__username' # O 'autor__first_name' si lo prefieres
    )
    # Convertimos el QuerySet a una lista de diccionarios para enviarlo como JSON
    return JsonResponse(list(observaciones), safe=False)


# --- VISTA 2: PARA GUARDAR UN NUEVO COMENTARIO ---
@login_required
@require_POST # Esta vista solo debe aceptar peticiones POST
def add_observacion_json(request, dispositivo_id):
    try:
        dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
        data = json.loads(request.body)
        nuevo_comentario = data.get('comentario', '').strip()

        if not nuevo_comentario:
            return JsonResponse({'status': 'error', 'message': 'El comentario no puede estar vacío.'}, status=400)

        # Creamos y guardamos la nueva observación
        obs = ObservacionDispositivo.objects.create(
            dispositivo=dispositivo,
            autor=request.user,
            comentario=nuevo_comentario
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Observación guardada.',
            'comentario': obs.comentario,
            'autor': obs.autor.username,
            'fecha': obs.fecha_creacion.strftime('%d/%m/%Y %H:%M')
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def inventario_dispositivo(request):
    
    opciones_tipos = Dispositivo.objects.values_list('tipoDisp', flat=True).distinct().order_by('tipoDisp')
    opciones_estados = Dispositivo.objects.values_list('estadoD', flat=True).distinct().order_by('estadoD')
    opciones_areas = Dispositivo.objects.exclude(area_general__isnull=True).exclude(area_general__exact='').values_list('area_general', flat=True).distinct().order_by('area_general')
 
    # 2. Capturar los valores de los filtros desde la URL (request.GET)
    modelo_filtro = request.GET.get('modelo', '')
    serie_filtro = request.GET.get('serie', '')
    tag_filtro = request.GET.get('tag', '')
    tipo_filtro = request.GET.get('tipo', '')
    estado_filtro = request.GET.get('estado', '')
    area_filtro = request.GET.get('area', '')
 
    # 3. Construir el queryset base
    dispositivos = Dispositivo.objects.all().prefetch_related('sensor_set').order_by('nomDisp')
 
    # 4. Aplicar los filtros si existen
    if modelo_filtro:
        dispositivos = dispositivos.filter(nomDisp=modelo_filtro)
    if serie_filtro:
        dispositivos = dispositivos.filter(num_serie__icontains=serie_filtro)
    if tag_filtro:
        dispositivos = dispositivos.filter(tag__icontains=tag_filtro)
    if tipo_filtro:
        dispositivos = dispositivos.filter(tipoDisp=tipo_filtro)
    if estado_filtro:
        dispositivos = dispositivos.filter(estadoD=estado_filtro)
    if area_filtro:
        dispositivos = dispositivos.filter(area_general=area_filtro)

    paginator = Paginator(dispositivos, 15) # 15 modificaciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
 
    # 5. Preparar el contexto para la plantilla
    context = {
        'page_obj': page_obj,
        'titulo': 'Gestiona los Dispositivos Fijos y Portátiles',
        'opciones_tipos': opciones_tipos,
        'opciones_estados': opciones_estados,
        'opciones_areas': opciones_areas,
        'filtros_aplicados': {
            'modelo': modelo_filtro,
            'serie': serie_filtro,
            'tag': tag_filtro,
            'tipo': tipo_filtro,
            'estado': estado_filtro,
            'area': area_filtro,
        }
    }
 
    return render(request, 'dispositivos/lista_dispositivo.html', context)


def eliminar_dispositivo(request, id_dispositivo):
    dispositivo = Dispositivo.objects.get(id_dispositivo=id_dispositivo)
    dispositivo.delete()
    return redirect('cenerisapp:lista_inventario')


def editar_dispositivo(request, id_dispositivo):
    dispositivo = Dispositivo.objects.get(id_dispositivo=id_dispositivo)
    if request.method == 'POST':
        dispositivo.nomDisp = request.POST.get('nomDisp')
        dispositivo.num_serie = request.POST.get('num_serie')
        dispositivo.tag = request.POST.get('tag')
        dispositivo.tipoDisp = request.POST.get('tipoDisp')
        dispositivo.estadoD = request.POST.get('estadoD')
        dispositivo.fabDisp = request.POST.get('fabDisp')
        dispositivo.fecIngreso = request.POST.get('fecIngreso')
        dispositivo.fecVencimientoGarantia = request.POST.get('fecVencimientoGarantia')
        dispositivo.save()
        return redirect('cenerisapp:lista_inventario')
    context = {
        'dispositivo': dispositivo,
        'titulo': 'Editar Dispositivo'
    }
    return render(request, 'dispositivos/editar_dispositivo.html', context)


def get_puntos_por_area_api(request):
    area_id = request.GET.get('area_id')
    puntos = PuntoExacto.objects.filter(area_trabajo_id=area_id).values('id', 'nombre_punto')
    return JsonResponse(list(puntos), safe=False)


@login_required
def crear_dispositivo(request):
    if request.method == 'POST':
        form = DispositivoForm(request.POST)
        if form.is_valid():
            
            dispositivo = form.save(commit=False)
            
            dispositivo.fecIngreso = date.today()  # Fecha del día de hoy
            dispositivo.estadoD = 'Operativo'      # Estado por defecto
            
            dispositivo.save()
            
            cantidad = form.cleaned_data.get('cantidad_sensores') or 0
            messages.success(request, f"Dispositivo '{dispositivo.nomDisp}' creado exitosamente.")
            
            if cantidad > 0:
                return redirect('cenerisapp:asignar_sensores_a_dispositivo', dispositivo_id=dispositivo.id_dispositivo, cantidad=cantidad)
            else:
                return redirect('cenerisapp:lista_dispositivos')
    else:
        form = DispositivoForm()
 
    context = {
        'form': form,
        'titulo': 'Crear Nuevo Dispositivo'
    }
    return render(request, 'dispositivos/crear_dispositivo.html', context)


@login_required
def asignar_sensores_a_dispositivo(request, dispositivo_id, cantidad):
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
   
    SensorFormSet = formset_factory(
        SensorParaDispositivoForm,
        formset=BaseSensorParaDispositivoFormSet, # Mantenemos la validación
        extra=cantidad # Solo usamos 'extra'
    )
 
    if request.method == 'POST':
        formset = SensorFormSet(request.POST)
        if formset.is_valid():
            try: # --- INICIO DEL BLOQUE TRY ---
                for form in formset:
                    if form.has_changed():
                        
                        sensor = form.save(commit=False)
                        sensor.dispositivo_instalado = dispositivo
            
                        sensor.save()
               
                messages.success(request, f"Se asignaron {len(formset)} sensores al dispositivo.")
                return redirect('cenerisapp:lista_dispositivos')

            except ValidationError as e: # --- ATRAPAMOS EL ERROR DEL MODELO ---
                
                if '__all__' in e.message_dict:
                    for error_message in e.message_dict['__all__']:
                        messages.error(request, error_message)
                
               
    else: # Petición GET
        formset = SensorFormSet()
 
    context = {
        'formset': formset,
        'dispositivo': dispositivo,
        'cantidad': cantidad
    }
    return render(request, 'dispositivos/asignar_sensores.html', context)


@login_required
def asignar_partes_a_dispositivo(request, dispositivo_id):
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    
    
    formset_prefix = 'partes' 

    if request.method == 'POST':
        
        formset = ParteFormSet(request.POST, instance=dispositivo, prefix=formset_prefix)
        
        if formset.is_valid():
            formset.save()
            messages.success(request, f"Se han actualizado las partes para el dispositivo '{dispositivo.nomDisp}'.")
            return redirect('cenerisapp:lista_dispositivos')
        else:
            # Imprimimos los errores en la consola para depuración
            print("Errores del FormSet:", formset.errors)
            messages.error(request, "No se pudieron guardar los cambios. Por favor, revisa los errores en el formulario.")
    else:
        
        formset = ParteFormSet(instance=dispositivo, prefix=formset_prefix)

    context = {
        'dispositivo': dispositivo,
        'formset': formset,
        'titulo': f'Asignar/Editar Partes de {dispositivo.nomDisp}'
    }
    return render(request, 'dispositivos/asignar_partes.html', context)


@login_required
def gestionar_fotos_dispositivo(request, dispositivo_id):
    
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    # Traemos las modificaciones para el desplegable
    modificaciones_del_dispositivo = dispositivo.modificacion_set.order_by('-fecInstalacionMod')

    if request.method == 'POST':
        form = FotoDispositivoForm(request.POST, request.FILES, modificaciones_queryset=modificaciones_del_dispositivo)
        
        if form.is_valid():
            foto = form.save(commit=False)
            foto.dispositivo = dispositivo

            modificacion_asociada = form.cleaned_data.get('modificacion')
            
            if modificacion_asociada:
                # =========================================================
                # LÓGICA AUTOMÁTICA MEJORADA (SENSORES Y PARTES)
                # =========================================================
                foto.contexto = 'CARDEX' # Siempre es Cardex si hay modificación
                
                # CASO 1: Es un cambio de SENSOR (Componente entrante es Sensor)
                if modificacion_asociada.componente_entrante and hasattr(modificacion_asociada.componente_entrante, 'sensor'):
                    foto.tipo_foto = modificacion_asociada.componente_entrante.sensor.tipGas
                
                # CASO 2: Es un cambio de SENSOR (Salió un sensor, aunque no haya entrado nada)
                elif modificacion_asociada.sensor_saliente:
                    foto.tipo_foto = modificacion_asociada.sensor_saliente.tipGas

                # CASO 3: Es un cambio de PARTE / KIT (Entró un componente genérico)
                # Aquí capturamos el nombre: "Carcasa", "Batería", etc.
                elif modificacion_asociada.componente_entrante:
                    foto.tipo_foto = modificacion_asociada.componente_entrante.nomComp
                
                # CASO 4: Es un retiro de PARTE (Sin reemplazo)
                elif modificacion_asociada.parte_saliente:
                    foto.tipo_foto = modificacion_asociada.parte_saliente.nomPart
                
                else:
                    # Fallback por seguridad
                    foto.tipo_foto = 'MANTENIMIENTO'

            # =========================================================
            # LÓGICA PARA FOTOS GENERALES (Sin modificación asociada)
            # =========================================================
            else:
                tipo_foto_nuevo = form.cleaned_data.get('tipo_foto')
                contexto_nuevo = form.cleaned_data.get('contexto')
                
                # Si el usuario sube una nueva foto "General" del mismo tipo (ej. EVIDENCIA),
                # borramos la anterior para no acumular basura.
                foto_existente = FotoDispositivo.objects.filter(
                    dispositivo=dispositivo, 
                    tipo_foto=tipo_foto_nuevo,
                    contexto=contexto_nuevo,
                    modificacion__isnull=True
                ).first()

                if foto_existente:
                    foto_existente.delete()
                    messages.info(request, f"Se ha reemplazado la imagen general anterior para '{tipo_foto_nuevo}' en el contexto '{contexto_nuevo}'.")
            
            # Guardamos la foto finalmente
            foto.save()
            messages.success(request, f"Imagen cargada exitosamente como '{foto.tipo_foto}'.")
            return redirect('cenerisapp:gestionar_fotos_dispositivo', dispositivo_id=dispositivo.id_dispositivo)
        else:
            messages.error(request, "Error al cargar la imagen. Por favor, revisa el formulario.")
            
    else: # GET
        form = FotoDispositivoForm(modificaciones_queryset=modificaciones_del_dispositivo)

    # Listar fotos para la galería
    fotos_list = dispositivo.fotos.all().order_by('-fecha_carga')
    
    paginator = Paginator(fotos_list, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Lista de sugerencias para el frontend
    tipos_validos = [s.tipGas for s in dispositivo.sensor_set.all() if s.tipGas] + ["EVIDENCIA"]
    
    context = {
        'form': form,
        'dispositivo': dispositivo,
        'fotos': page_obj,
        'tipos_validos_para_fotos': tipos_validos,
        'titulo': f"Gestionar Fotos para {dispositivo.nomDisp}"
    }
    return render(request, 'dispositivos/gestionar_fotos.html', context)


@login_required
def marcar_cardex_revisado(request, dispositivo_id):
    if request.method == 'POST':
        dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
        dispositivo.cardex_revisado = True
        dispositivo.save()
        messages.success(request, f"CARDEX para {dispositivo.nomDisp} marcado como revisado.")
    return redirect('cenerisapp:lista_dispositivos')
