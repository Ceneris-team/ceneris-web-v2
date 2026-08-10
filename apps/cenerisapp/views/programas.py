"""Vistas de programas de certificacion.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from cenerisapp.forms import ProgramaCreateForm, ProgramaUpdateForm
from cenerisapp.models import Certificado, Programa


@login_required
def lista_programas(request):
    
    # --- 1. PREPARAR DATOS PARA LA NAVEGACIÓN Y FILTROS ---
    anos_disponibles = Programa.objects.values_list('ano', flat=True).distinct().order_by('-ano')
    meses_disponibles = Programa.MES_CHOICES
    tipos_disponibles = Programa.TIPO_DISPOSITIVO_CHOICES
    
    # --- 2. CAPTURAR EL AÑO Y FILTROS SELECCIONADOS ---
    today = date.today()
    ano_seleccionado = int(request.GET.get('year', today.year))
    
    mes_filtro = request.GET.get('mes')
    tipo_filtro = request.GET.get('tipo')
    
    # --- 3. CONSTRUIR QUERYSET BASE Y APLICAR FILTROS ---
    # La base siempre se filtra por el año seleccionado
    programas_qs = Programa.objects.filter(ano=ano_seleccionado)
    
    if mes_filtro:
        programas_qs = programas_qs.filter(mes=mes_filtro)
    if tipo_filtro:
        programas_qs = programas_qs.filter(tipo_dispositivo=tipo_filtro)
    
    # Anotamos el conteo de certificados (esto es crucial y se mantiene)
    programas_con_conteo = programas_qs.annotate(
        num_certificados=Count('certificado')
    )

    # Actualizamos el totalEjecutado en memoria para la plantilla
    for programa in programas_con_conteo:
        programa.totalEjecutado = programa.num_certificados
    
    # --- 4. PREPARAR CONTEXTO ---
    context = {
        'programas': programas_con_conteo, 
        'titulo': f'Programas de Calibración - Año {ano_seleccionado}',
        
        # Para la navegación por año
        'anos_disponibles': anos_disponibles,
        'ano_seleccionado': ano_seleccionado,
        
        # Para los desplegables de filtros
        'meses_disponibles': meses_disponibles,
        'tipos_disponibles': tipos_disponibles,
        'filtros_aplicados': {
            'mes': int(mes_filtro) if mes_filtro else None,
            'tipo': tipo_filtro,
        }
    }
    return render(request, 'programas/lista_programas.html', context)


@login_required
def crear_programa(request):
    if request.method == 'POST':
        form = ProgramaCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Nuevo programa creado exitosamente.")
            return redirect('cenerisapp:lista_programas')
    else:
        form = ProgramaCreateForm()
    
    context = {'form': form, 'titulo': 'Crear Nuevo Programa'}
    return render(request, 'programas/crear_programa.html', context)


@login_required
def ver_certificados_programa(request, programa_id):
    # 1. Obtenemos el objeto del programa específico. Si no existe, devuelve un error 404.
    programa = get_object_or_404(Programa, pk=programa_id)

    # 2. Hacemos la consulta clave: Filtramos todos los Certificados
    #    cuyo campo 'id_programa' coincida con el programa que obtuvimos.
    #    Usamos 'select_related' para optimizar la consulta y evitar
    #    golpes extra a la BD al acceder al dispositivo en la plantilla.
    certificados_del_programa = Certificado.objects.filter(
        id_programa=programa
    ).select_related('dispositivo').order_by('-fechCertificado')

    # 3. Preparamos el contexto para pasarlo a la plantilla.
    context = {
        'programa': programa,
        'certificados': certificados_del_programa,
        'titulo': f"Certificados para el Programa: {programa.get_mes_display()} {programa.ano}"
    }
    
    # 4. Renderizamos la nueva plantilla que crearemos en el siguiente paso.
    return render(request, 'programas/certificados_por_programa.html', context)


@login_required
def editar_programa(request, programa_id):
    programa = get_object_or_404(Programa, pk=programa_id)
    
    if request.method == 'POST':
        form = ProgramaUpdateForm(request.POST, instance=programa)
        if form.is_valid():
            form.save()
            messages.success(request, f"Progreso del programa #{programa.id_programa} actualizado.")
            return redirect('cenerisapp:lista_programas')
    else:
        form = ProgramaUpdateForm(instance=programa)

    context = {
        'form': form,
        'programa': programa,
        'titulo': f'Actualizar Progreso del Programa #{programa.id_programa}'
    }
    return render(request, 'programas/editar_programa.html', context)
