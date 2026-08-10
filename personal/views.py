from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Value, Q
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import Personal, AreaTrabajo
from .forms import PersonalForm, AreaTrabajoForm


@login_required 
def lista_personal(request):
    # --- MODELOS IMPORTADOS LOCALMENTE ---
    # Esto ayuda a prevenir errores de importación circular en proyectos grandes.
    from proyectos.models import Proyecto, TareaP

    # --- INICIALIZACIÓN DE VARIABLES ---
    personal_list = None
    tareas_del_proyecto = None
    areas_trabajo = []
    cargos = []
    area_filtrada = request.GET.get('area')
    cargo_filtrado = request.GET.get('cargo')
    query_nombre = request.GET.get('q_nombre', '')
    
    proyectos = Proyecto.objects.all()
    proyecto_seleccionado_id = request.GET.get('proyecto_id')

    # --- DECIDIR MODO DE VISUALIZACIÓN ---
    if proyecto_seleccionado_id:
        # MODO: Vista de Equipo de Proyecto
        tareas_del_proyecto_final = []
        try:
            proyecto_seleccionado = Proyecto.objects.get(pk=proyecto_seleccionado_id)
            tareas_principales = TareaP.objects.filter(
                proyecto=proyecto_seleccionado
            ).prefetch_related('subtareas__personal_asignado') # Usamos prefetch_related para eficiencia

            animation_counter = 0 # Contador global para el delay
            
            for tarea in tareas_principales:
                personas_en_tarea = []
                subtareas_de_la_tarea = tarea.subtareas.all()
                
                for subtarea in subtareas_de_la_tarea:
                    for persona in subtarea.personal_asignado.all():
                        personas_en_tarea.append({
                            'persona': persona,
                            'subtarea': subtarea,
                            'delay': animation_counter * 0.05 # Calculamos el delay aquí
                        })
                        animation_counter += 1
                
                # Agrupamos los datos para la plantilla
                tareas_del_proyecto_final.append({
                    'tarea': tarea,
                    'asignaciones': personas_en_tarea
                })

        except Proyecto.DoesNotExist:
            proyecto_seleccionado_id = None
        
        # Actualizamos la variable que pasamos al contexto
        tareas_del_proyecto = tareas_del_proyecto_final 
    else:
        # MODO: Vista de Todo el Personal
        personal_list = Personal.objects.select_related('area_trabajo').all()
        
        areas_trabajo = AreaTrabajo.objects.all()
        cargos = Personal.objects.values_list('cargo', flat=True).distinct()

        if query_nombre:
            personal_list = personal_list.filter(
                Q(nombre__icontains=query_nombre) | Q(apellido__icontains=query_nombre)
            )

        if area_filtrada:
            personal_list = personal_list.filter(area_trabajo__id=area_filtrada)
        if cargo_filtrado:
            personal_list = personal_list.filter(cargo=cargo_filtrado)
            
    # El formulario para el modal siempre se necesita
    form = PersonalForm()
    
    context = {
        'personal_list': personal_list,
        'form': form,
        'proyectos': proyectos,
        'proyecto_seleccionado_id': proyecto_seleccionado_id,
        'tareas_del_proyecto': tareas_del_proyecto,
        'areas_trabajo': areas_trabajo,
        'cargos': cargos,
        'filtros_aplicados': {'area': area_filtrada, 'cargo': cargo_filtrado, 'q_nombre': query_nombre,}
    }
    
    return render(request, 'lista_personal.html', context)

@login_required 
@transaction.atomic     
def crear_personal(request):
    redirect_url = 'personal:lista_personal'

    if request.method == 'POST':
        form = PersonalForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Nuevo miembro del personal añadido correctamente.")
            return redirect(redirect_url)
        else:
            # Si el formulario NO es válido
            # La mejor práctica es recargar la página y que un JS muestre el modal con los errores.
            for field, errors in form.errors.items():
                # Obtenemos el label del campo para un mensaje más amigable
                label = form.fields.get(field).label if form.fields.get(field) else field.replace('_', ' ').title()
                for error in errors:
                    messages.error(request, f"{label}: {error}")
            # Guardamos los datos incorrectos en la sesión para rellenar el formulario
            request.session['invalid_personal_form_data'] = request.POST

    return redirect(redirect_url)

def search_personal(request):
    term = request.GET.get('term', '').strip()
    if not term:
        return JsonResponse({'results': []})
    
    personal_qs = Personal.objects.filter(
        Q(nombre__icontains=term) | Q(apellido__icontains=term)
    )[:10]

    results = [{"id": p.id, "text": f"{p.nombre} {p.apellido}"} for p in personal_qs]
    return JsonResponse({'results': results})


@require_POST
def api_unassign_personal(request, subtarea_id, personal_id):
    from proyectos.models import SubTarea
    subtarea = get_object_or_404(SubTarea, pk=subtarea_id)
    persona = get_object_or_404(Personal, pk=personal_id)
    subtarea.personal_asignado.remove(persona)
    return JsonResponse({'status': 'success', 'message': f'{persona.nombre} ha sido desasignado/a.'})

@login_required 
@require_POST
def api_delete_personal(request, pk):
    persona = get_object_or_404(Personal, pk=pk)
    if persona.subtareas_asignadas.exists():
        return JsonResponse({
            'status': 'error',
            'message': f'No se puede eliminar a {persona.nombre} porque está asignado/a a tareas.'
        }, status=400)
        
    try:
        nombre_persona = f"{persona.nombre} {persona.apellido}"
        persona.delete()
        return JsonResponse({'status': 'success', 'message': f'{nombre_persona} ha sido eliminado.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)