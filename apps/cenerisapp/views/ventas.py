"""Vistas de ventas de componentes.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from cenerisapp.forms import VentaForm
from cenerisapp.models import Componente, Ventas


@login_required
def crear_venta(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        if form.is_valid():
            componente_id = form.cleaned_data.get('id_componente')
            componente_obj = get_object_or_404(Componente, pk=componente_id)
            
            
            venta = form.save(commit=False)
            venta.id_componente = componente_obj
            venta.save()
            
            
            
            nombre_componente_vendido = componente_obj.nomComp # Guardamos el nombre para el mensaje
            componente_obj.delete()
            
            messages.success(request, f"Venta registrada y componente '{nombre_componente_vendido}' descontado del stock.")
            return redirect('cenerisapp:lista_ventas')
    else:
        form = VentaForm()

    context = {
        'form': form,
        'titulo': 'Registrar Nueva Venta'
    }
    return render(request, 'ventas/crear_venta.html', context)


@login_required
def completar_venta(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Ventas, pk=venta_id)
        
        venta.estado = 'Completado' # O el estado que prefieras
        venta.save()
        messages.success(request, f"La venta #{venta.id_ventas} ha sido marcada como completada.")
    return redirect('cenerisapp:lista_ventas')


@login_required
def lista_ventas(request):
    ventas = Ventas.objects.select_related('id_componente').all().order_by('-fecVenta')
    context = {
        'ventas': ventas,
        'titulo': 'Historial de Ventas'
    }
    return render(request, 'ventas/lista_ventas.html', context)
