"""Vistas de datos maestros: empresas, areas y empleados.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from cenerisapp.forms import (
    AreaTrabajoForm,
    CorreoFormSet,
    EmpleadoForm,
    PuntoExactoFormSet,
    TelefonoFormSet,
)
from cenerisapp.models import AreaTrabajo, Empleado, Empresa


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'¡Cuenta creada para {username}! Ahora puedes iniciar sesión.')
            return redirect('cenerisapp:login') 
    else:
        form = UserCreationForm()
    return render(request, 'registration/registro.html', {'form': form})


@login_required
def buscar_empresas_api(request):
    query = request.GET.get('term', '')
    empresas = Empresa.objects.filter(nombreE__icontains=query)[:10]
    resultados = [
        {'id': empresa.pk, 'label': empresa.nombreE, 'value': empresa.nombreE}
        for empresa in empresas
    ]
    return JsonResponse(resultados, safe=False)


@login_required
def get_empleado_info(request, empleado_id):
    try:
        
        empleado = Empleado.objects.select_related('areaTrabajo').get(pk=empleado_id)
        data = {
            'nombre': empleado.nomEmpleado,
            'puesto': empleado.puesto,
            'area_trabajo': empleado.areaTrabajo.nombreA if empleado.areaTrabajo else 'No asignada'
        }
        return JsonResponse(data)
    except Empleado.DoesNotExist:
        return JsonResponse({'error': 'Empleado no encontrado'}, status=404)


@login_required
def tecnicos_indice(request):
    titulo = "Datos Técnicos"
    return render(request, 'tecnicos/indice.html', {'titulo': titulo})


@login_required
def lista_empresas(request):
    empresas = Empresa.objects.all().order_by('nombreE')
    context = {
        'empresas': empresas,
        'titulo': 'Lista de Todas las Empresas'
    }
    return render(request, 'tecnicos/lista_empresas.html', context)


@login_required
def lista_areas(request):
    areas = AreaTrabajo.objects.all().order_by('nombreA')
    context = {
        'areas': areas,
        'titulo': 'Lista de Todas las Áreas de Trabajo' 
    }
    return render(request, 'tecnicos/lista_areas.html', context)


@login_required
def lista_empleados(request):
    empleados = Empleado.objects.select_related('areaTrabajo', 'supervisor').all().order_by('nomEmpleado')
    context = {
        'empleados': empleados,
        'titulo': 'Lista de Todos los Empleados'
    }
    return render(request, 'tecnicos/lista_empleados.html', context)


@login_required
def crear_empleado(request):
    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        
        
        correo_formset = CorreoFormSet(request.POST, prefix='correo')
        telefono_formset = TelefonoFormSet(request.POST, prefix='telefono')

        if form.is_valid() and correo_formset.is_valid() and telefono_formset.is_valid():
            
            empleado = form.save()
            
            correos = correo_formset.save(commit=False)
            for correo in correos:
                correo.empleado = empleado
                correo.save()
            
            telefonos = telefono_formset.save(commit=False)
            for telefono in telefonos:
                telefono.empleado = empleado
                telefono.save()

            messages.success(request, f"Empleado '{empleado.nomEmpleado}' creado exitosamente.")
            return redirect('cenerisapp:lista_empleados')
    else:
        form = EmpleadoForm()
        correo_formset = CorreoFormSet(prefix='correo')
        telefono_formset = TelefonoFormSet(prefix='telefono')

    context = {
        'form': form,
        'correo_formset': correo_formset,
        'telefono_formset': telefono_formset,
        'titulo': 'Registrar Nuevo Empleado'
    }
    return render(request, 'tecnicos/crear_empleado.html', context)


@login_required
def crear_empresa(request):
    if request.method == 'POST':
        abreviacion = request.POST.get('abreviacion')
        nombreE = request.POST.get('nombreE')
        direccion = request.POST.get('direccion')
        departamento = request.POST.get('departamento')
        telefono = request.POST.get('telefono')
        ruc = request.POST.get('ruc')
        Empresa.objects.create(
            abreviacion=abreviacion,
            nombreE=nombreE,
            direccion=direccion,
            departamento=departamento,
            telefono=telefono,
            ruc=ruc
        )
        return redirect('cenerisapp:lista_empresas')
    return render(request, 'tecnicos/crear_empresa.html')


@login_required
def editar_empresa(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
    if request.method == 'POST':
        empresa.abreviacion = request.POST.get('abreviacion')
        empresa.nombreE = request.POST.get('nombreE')
        empresa.direccion = request.POST.get('direccion')
        empresa.departamento = request.POST.get('departamento')
        empresa.telefono = request.POST.get('telefono')
        empresa.ruc = request.POST.get('ruc')
        empresa.save()
        return redirect('cenerisapp:lista_empresas')
    return render(request, 'tecnicos/editar_empresa.html', {'empresa': empresa})


@login_required
def eliminar_empresa(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
    empresa.delete()
    return redirect('cenerisapp:lista_empresas')


@login_required
def crear_area(request):
    if request.method == 'POST':
        # Instanciamos el formulario principal y el formset con los datos del POST
        form = AreaTrabajoForm(request.POST)
        formset = PuntoExactoFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Primero, guardamos el objeto principal (AreaTrabajo)
            area_trabajo = form.save()
            
            # Asociamos el formset con la instancia del área recién creada
            puntos_exactos = formset.save(commit=False)
            for punto in puntos_exactos:
                punto.area_trabajo = area_trabajo
                punto.save()

            messages.success(request, f"Área de Trabajo '{area_trabajo.nombreA}' y sus puntos exactos han sido creados.")
            return redirect('cenerisapp:lista_areas') # Asume que tienes una URL con este nombre
    else:
        # Petición GET: mostramos los formularios vacíos
        form = AreaTrabajoForm()
        formset = PuntoExactoFormSet()

    context = {
        'form': form,
        'formset': formset,
        'titulo': 'Crear Nueva Área de Trabajo'
    }
    return render(request, 'tecnicos/crear_area.html', context)


# --- VISTA DE EDICIÓN ---
@login_required
def editar_area(request, area_id):
    area_trabajo = get_object_or_404(AreaTrabajo, pk=area_id)
    
    if request.method == 'POST':
        # Pasamos la 'instance' a ambos para indicar que estamos editando
        form = AreaTrabajoForm(request.POST, instance=area_trabajo)
        formset = PuntoExactoFormSet(request.POST, instance=area_trabajo)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save() # Con 'instance', Django maneja la creación, actualización y borrado
            
            messages.success(request, f"Área de Trabajo '{area_trabajo.nombreA}' actualizada.")
            return redirect('cenerisapp:lista_areas')
    else:
        # Petición GET: mostramos los formularios pre-llenados
        form = AreaTrabajoForm(instance=area_trabajo)
        formset = PuntoExactoFormSet(instance=area_trabajo)

    context = {
        'form': form,
        'formset': formset,
        'area': area_trabajo,
        'titulo': f'Editar Área de Trabajo: {area_trabajo.nombreA}'
    }
    return render(request, 'tecnicos/editar_area.html', context)


@login_required
def eliminar_area(request, area_id):
    area = get_object_or_404(AreaTrabajo, pk=area_id)
    area.delete()
    return redirect('cenerisapp:lista_areas')
