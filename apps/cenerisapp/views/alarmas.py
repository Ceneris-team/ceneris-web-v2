"""Vistas de alarmas, calibraciones e informes.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from cenerisapp.forms import AlarmaFijoForm, AlarmaPortatilForm, InformeCalibracionForm
from cenerisapp.models import Calibracion, Dispositivo, Sensor


@login_required
def seleccionar_dispositivo_alarma(request):
    """Página 1: El usuario selecciona un dispositivo."""
    dispositivos = Dispositivo.objects.all().order_by('nomDisp')
    context = {
        'dispositivos': dispositivos,
        'titulo': 'Seleccionar Dispositivo para Configurar Alarma'
    }
    return render(request, 'alarmas/seleccionar_dispositivo.html', context)


@login_required
def get_dispositivo_tipo(request, dispositivo_id):
    """Una mini-API para que JS sepa qué tipo de dispositivo es."""
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    return JsonResponse({'tipo': dispositivo.tipoDisp})


@login_required
def configurar_alarma(request, dispositivo_id):
    """Página 2: Muestra el formulario correcto y procesa los datos."""
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    
    if dispositivo.tipoDisp.upper() == 'FIJO':
        
        if request.method == 'POST':
            form = AlarmaFijoForm(request.POST)
            if form.is_valid():
                alarma = form.save(commit=False)
                alarma.id_dispositivo = dispositivo
                alarma.save()
                messages.success(request, f"Alarma configurada para el dispositivo fijo '{dispositivo.nomDisp}'.")
                return redirect('cenerisapp:seleccionar_dispositivo_alarma')
        else:
            form = AlarmaFijoForm()
        
        template_name = 'alarmas/configurar_alarma_fijo.html'

    elif dispositivo.tipoDisp.upper() == 'PORTATIL':
        
        if request.method == 'POST':
            
            form = AlarmaPortatilForm(request.POST, instance=dispositivo)
            if form.is_valid():
                form.save()
                messages.success(request, f"Alarma actualizada para el dispositivo portátil '{dispositivo.nomDisp}'.")
                return redirect('cenerisapp:seleccionar_dispositivo_alarma')
        else:
            form = AlarmaPortatilForm(instance=dispositivo)
        
        template_name = 'alarmas/configurar_alarma_portatil.html'

    else:
        messages.error(request, "Tipo de dispositivo desconocido.")
        return redirect('cenerisapp:seleccionar_dispositivo_alarma')

    context = {
        'form': form,
        'dispositivo': dispositivo
    }
    return render(request, template_name, context)


@login_required
def gestion_calibraciones(request): # Le cambiamos el nombre para que sea más claro
    
    
    dispositivos = Dispositivo.objects.prefetch_related('calibracion_set').all().order_by('nomDisp')
    
    

    context = {
        'dispositivos': dispositivos,
        'titulo': 'Gestión de Calibraciones'
    }
    return render(request, 'calibraciones/gestion_calibraciones.html', context)


@login_required
def registrar_calibracion_ahora(request, dispositivo_id):
    
    if request.method == 'POST':
        dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
        
        
        
        calibracion, created = Calibracion.objects.get_or_create(id_dispositivo=dispositivo)
        
        
        calibracion.estado = 'Calibrado'
        calibracion.fecCalibracionC = timezone.now().date() # Usamos la fecha actual
        
        
        if dispositivo.tipoDisp == 'Portatil':
            calibracion.prox_fecha = calibracion.fecCalibracionC + timedelta(days=1)
        elif dispositivo.tipoDisp == 'Fijo':
            calibracion.prox_fecha = calibracion.fecCalibracionC + timedelta(days=30)
        
        calibracion.save()
        
        messages.success(request, f"El dispositivo '{dispositivo.nomDisp}' ha sido calibrado.")
        
    
    return redirect('cenerisapp:gestion_calibraciones')


@login_required
def seleccionar_sensor_para_informe(request, dispositivo_id):
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    # Obtenemos todos los sensores instalados en este dispositivo
    sensores_del_dispositivo = dispositivo.sensor_set.all()
    
    context = {
        'dispositivo': dispositivo,
        'sensores_del_dispositivo': sensores_del_dispositivo,
        'titulo': f'Seleccionar Sensor para Informe en {dispositivo.nomDisp}'
    }
    return render(request, 'informes/seleccionar_sensor.html', context)


@login_required
def crear_informe_calibracion(request, sensor_id):
    # Buscamos el sensor específico, y a través de él, su dispositivo
    sensor = get_object_or_404(Sensor.objects.select_related('dispositivo_instalado'), pk=sensor_id)
    dispositivo = sensor.dispositivo_instalado

    if request.method == 'POST':
        form = InformeCalibracionForm(request.POST)
        if form.is_valid():
            informe = form.save(commit=False)
            informe.sensor = sensor # <-- Asignamos el sensor
            informe.save()
            messages.success(request, f"Informe guardado para el sensor '{sensor.nomComp}'.")
            
            # Redirigimos a la página de detalles del dispositivo padre
            return redirect('cenerisapp:detalle_dispositivo', pk=dispositivo.pk) 
    else:
        form = InformeCalibracionForm()

    context = {
        'form': form,
        'sensor': sensor,
        'dispositivo': dispositivo, # Pasamos ambos para mostrar info en el título
        'titulo': f'Nuevo Informe para Sensor {sensor.nomComp} (en {dispositivo.nomDisp})'
    }
    return render(request, 'informes/crear_informe.html', context)
