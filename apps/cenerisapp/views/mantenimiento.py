"""Vistas de mantenimiento de dispositivos.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from cenerisapp.forms import MantenimientoForm
from cenerisapp.models import Dispositivo


@login_required
def crear_mantenimiento(request, dispositivo_id):
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    
    
    partes_del_dispositivo = list(dispositivo.partes.all().values_list('nomPart', flat=True))
    sensores_del_dispositivo = [f"Sensor {s.tipGas}" for s in dispositivo.sensor_set.all()]
    checklist_items = sorted(partes_del_dispositivo + sensores_del_dispositivo)

    if request.method == 'POST':
        
        form = MantenimientoForm(request.POST)
        
        if form.is_valid():
            mantenimiento = form.save(commit=False)
            mantenimiento.dispositivo = dispositivo
            
            
            checklist_data = {}
            for item in checklist_items:
                estado = request.POST.get(f'checklist_estado_{item}')
                comentario = request.POST.get(f'checklist_comentario_{item}')
                if estado:
                    checklist_data[item] = {'estado': estado, 'comentario': comentario}
            mantenimiento.checklist_partes = checklist_data
            
            mantenimiento.save() # Guardamos el registro de mantenimiento

            
            fec_ino = form.cleaned_data.get('actualizar_fec_inoperativo')
            fec_irr = form.cleaned_data.get('actualizar_fec_irreparable')
            if dispositivo.tipoDisp == 'Portatil' and (fec_ino or fec_irr):
                if fec_ino:
                    dispositivo.fec_inoperativo = fec_ino
                    dispositivo.estadoD = 'Inoperativo'
                if fec_irr:
                    dispositivo.fec_irreparable = fec_irr
                dispositivo.save()
            
            messages.success(request, "Registro de mantenimiento guardado.")
            return redirect('cenerisapp:lista_dispositivos') # O a una lista de mantenimientos
            
    else: # GET
        form = MantenimientoForm()
        
    context = {
        'form': form,
        'dispositivo': dispositivo,
        'checklist_items': checklist_items, # Le pasamos la lista de items
        'titulo': f'Nuevo Mantenimiento para {dispositivo.nomDisp}'
    }
    return render(request, 'mantenimiento/crear_mantenimiento.html', context)
