"""Vistas de certificados de calibracion y sus anexos.

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import os
import uuid

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F, Q
from django.forms import formset_factory, inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from cenerisapp.forms import (
    AnexoCertificadoForm,
    CertificadoForm,
    PatronesFormSet,
    ResultadosFormSet,
)
from cenerisapp.models import (
    AnexoCertificado,
    Certificado,
    Componente,
    DatosPDF,
    Dispositivo,
    PatronesCalibracion,
    Programa,
    Resultados,
    Sensor,
)

from ..services.pdf import generar_pdf_respuesta


@require_POST
@login_required
def upload_anexo_temporal(request):
    if 'imagen' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No se encontró ningún archivo.'}, status=400)
    
    imagen = request.FILES['imagen']
    
    try:
        # Guardamos el archivo en una ubicación temporal en S3
        filename = default_storage.save(f"temp_anexos/{uuid.uuid4()}_{imagen.name}", imagen)
        
        # Devolvemos el path que S3 nos dio
        return JsonResponse({'status': 'success', 'path': filename})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def agregar_anexos_certificado(request):
    certificado = None
    formset = None
    
    # --- BÚSQUEDA DEL CERTIFICADO (vía GET) ---
    query = request.GET.get('q', '').strip()
    if query:
        try:
            # Buscamos el certificado por su número exacto
            certificado = Certificado.objects.prefetch_related('anexos').get(nro_certificado__iexact=query)
        except Certificado.DoesNotExist:
            messages.error(request, f"No se encontró ningún certificado con el número '{query}'.")
        except Certificado.MultipleObjectsReturned:
            messages.error(request, f"Se encontraron múltiples certificados con el número '{query}'. Verifique los datos.")

    # --- DEFINICIÓN DEL FORMSET ---
    # Lo definimos aquí para usarlo tanto en GET como en POST
    AnexoFormSet = inlineformset_factory(
        Certificado,
        AnexoCertificado,
        form=AnexoCertificadoForm,
        extra=3, # Empezamos con 3 campos de archivo
        can_delete=True # Permitimos borrar anexos existentes
    )
    
    # --- MANEJO DEL FORMULARIO (POST) ---
    if request.method == 'POST':
        # Re-buscamos el certificado usando el ID enviado en el POST para seguridad
        certificado_id = request.POST.get('certificado_id')
        if not certificado_id:
            messages.error(request, "No se especificó un certificado para guardar los anexos.")
            return redirect('cenerisapp:agregar_anexos_certificado')
        
        certificado = get_object_or_404(Certificado, pk=certificado_id)
        
        # Inicializamos el formset con los datos POST, los archivos y la instancia del certificado
        formset = AnexoFormSet(request.POST, request.FILES, instance=certificado, prefix='anexos')

        if formset.is_valid():
            formset.save()
            messages.success(request, f"Anexos para el certificado '{certificado.nro_certificado}' guardados correctamente.")
            # Redirigimos a la misma página con el certificado ya cargado
            return redirect(f"{reverse('cenerisapp:agregar_anexos_certificado')}?q={certificado.nro_certificado}")
        else:
            messages.error(request, "Por favor, corrige los errores en los archivos.")
            # Los errores se mostrarán en la plantilla
            
    # --- VISTA GET (O SI EL POST FALLA) ---
    # Si encontramos un certificado, inicializamos el formset con esa instancia
    if certificado and not formset: # 'not formset' para no sobreescribir si el POST falló
        formset = AnexoFormSet(instance=certificado, prefix='anexos')

    context = {
        'titulo': 'Agregar Anexos a Certificado Existente',
        'query': query,
        'certificado': certificado,
        'formset': formset, # Puede ser None si no se ha buscado, o un formset instanciado
    }
    return render(request, 'certificado/agregar_anexos.html', context)


@login_required
def configurar_lote_certificacion(request):


    if request.method == 'POST':
        form = CertificadoForm(request.POST)
        patrones_formset = PatronesFormSet(request.POST, prefix='patrones')
        resultados_formset = ResultadosFormSet(request.POST, prefix='resultados')

        form.fields['estadoFinal'].required = False
        form.fields['nro_certificado'].required = False
        if 'dispositivo' in form.fields:
            form.fields['dispositivo'].required = False

        if form.is_valid():
            
            # --- NUEVA LÓGICA DE LIMPIEZA Y SERIALIZACIÓN ---
            
            # 1. Limpiamos el formulario principal
            main_data = form.cleaned_data
            main_data.pop('estadoFinal', None)
            main_data.pop('nro_certificado', None)
            
            # Convertimos las fechas a string
            for key, value in main_data.items():
                if isinstance(value, date):
                    main_data[key] = value.isoformat()
            
            # 2. Limpiamos los formsets de manera explícita
            patrones_data_list = []
            for patron_form_data in patrones_formset.cleaned_data:
                # Nos aseguramos de saltar formularios vacíos o marcados para borrar
                if patron_form_data and not patron_form_data.get('DELETE'):
                    # Creamos un nuevo diccionario solo con los datos que queremos
                    clean_data = {
                        'patronUtil': patron_form_data.get('patronUtil'),
                        'n_p': patron_form_data.get('n_p'),
                        'n_lote': patron_form_data.get('n_lote'),
                        'n_certificado': patron_form_data.get('n_certificado'),
                        # Convertimos la fecha si existe
                        'fechaExpiracion': patron_form_data.get('fechaExpiracion').isoformat() if patron_form_data.get('fechaExpiracion') else None,
                    }
                    patrones_data_list.append(clean_data)

            resultados_data_list = []
            for resultado_form_data in resultados_formset.cleaned_data:
                if resultado_form_data and not resultado_form_data.get('DELETE'):
                    clean_data = {
                        'gas': resultado_form_data.get('gas'),
                        'lecturaPatron': resultado_form_data.get('lecturaPatron'),
                        'lecturaEquipo': resultado_form_data.get('lecturaEquipo'),
                        'prob_error': resultado_form_data.get('prob_error'),
                    }
                    resultados_data_list.append(clean_data)
            
            

            # 3. Construimos el diccionario final para la sesión
            lote_data = {
                'main': main_data,
                'patrones': patrones_data_list,
                'resultados': resultados_data_list,
            }
            
            request.session['lote_certificado_data'] = lote_data
            
            messages.success(request, "Paso 1 completado. Ahora seleccione los dispositivos para certificar.")
            
            # --- ¡CAMBIO CRUCIAL AQUÍ! ---
            # Redirigimos al Paso 2: la selección de dispositivos.
            return redirect('cenerisapp:seleccionar_dispositivos_lote') 

        else:
            messages.error(request, "Por favor, corrige los errores en el formulario para guardar los datos del lote.")

    else: # GET
        form = CertificadoForm()
        patrones_formset = PatronesFormSet(prefix='patrones')
        resultados_formset = ResultadosFormSet(prefix='resultados')

    context = {
        'form': form,
        'patrones_formset': patrones_formset,
        'resultados_formset': resultados_formset,
        'titulo': 'Configurar Datos para Lote de Certificación Diario',
        'modo_configuracion_lote': True,
    }
    return render(request, 'certificado/certificado_form.html', context)


@login_required
def limpiar_lote_certificacion(request):
    """
    Elimina los datos del lote de certificación de la sesión actual.
    """
    if 'lote_certificado_data' in request.session:
        del request.session['lote_certificado_data']
        messages.info(request, "Los datos del lote de certificación han sido limpiados.")
    return redirect(request.META.get('HTTP_REFERER', 'cenerisapp:lista_dispositivos'))


@login_required
def certificado_form(request, dispositivo_id=None, componente_id=None):
    dispositivo = None
    componente = None
    # Determinar si se está certificando un dispositivo completo o un componente específico
    if componente_id:
        componente = get_object_or_404(Componente, pk=componente_id)
        # Si es un componente, buscar su dispositivo asociado
        # Asumiendo que Sensor tiene un ForeignKey a Dispositivo y Componente es padre de Sensor
        if hasattr(componente, 'sensor') and componente.sensor.dispositivo_instalado:
            dispositivo = componente.sensor.dispositivo_instalado
        # Si tienes otros tipos de componentes que puedan estar en un dispositivo, añade lógica aquí
        
        if not dispositivo:
            messages.error(request, "Error: El componente seleccionado no está instalado en ningún dispositivo o el dispositivo no fue encontrado.")
            return redirect('cenerisapp:alguna_pagina_de_error_o_lista_de_componentes') # Ajusta tu URL de redirección
            
    elif dispositivo_id:
        dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
        # Para portátiles, el certificado se asocia al dispositivo completo, no a un componente individual en este contexto
        
    else:
        messages.error(request, "Error: No se proporcionó ID de dispositivo ni de componente.")
        return redirect('cenerisapp:alguna_pagina_de_error_o_lista_de_dispositivos') # Ajusta tu URL de redirección

    # Asegurarse de que tenemos un dispositivo para continuar
    if not dispositivo:
        messages.error(request, "Error: No se pudo determinar el dispositivo asociado para la certificación.")
        return redirect('cenerisapp:alguna_pagina_de_error_o_lista_general')

    empresa_asociada = dispositivo.id_empresa

    # Calcular el estado inicial previo
    estado_inicial_previo = "Primera Calibración"
    if componente: # Si estamos certificando un componente específico
        ultimo_certificado = Certificado.objects.filter(componente=componente).order_by('-fechCertificado', '-pk').first()
    else: # Si estamos certificando un dispositivo completo (portátil)
        ultimo_certificado = Certificado.objects.filter(dispositivo=dispositivo, componente__isnull=True).order_by('-fechCertificado', '-pk').first()

    if ultimo_certificado and ultimo_certificado.estadoFinal:
        estado_inicial_previo = ultimo_certificado.estadoFinal

    lote_data = request.session.get('lote_certificado_data', None)
    lote_activo = lote_data is not None


    if request.method == 'POST':
        form = CertificadoForm(request.POST)
        patrones_formset = PatronesFormSet(request.POST, prefix='patrones')
        resultados_formset = ResultadosFormSet(request.POST, prefix='resultados')

        if form.is_valid():
            lote_data = request.session.get('lote_certificado_data', None)
            
            # La validación condicional de los formsets
            are_formsets_valid = (not lote_data and 
                                  patrones_formset.is_valid() and 
                                  resultados_formset.is_valid())
            if lote_data or are_formsets_valid:
                certificado = form.save(commit=False)
                
                # Fusión de datos del lote
                if lote_data:
                    datos_main = lote_data.get('main', {})
                    certificado.temp = datos_main.get('temp')
                    certificado.presion = datos_main.get('presion')
                    certificado.humedadRelativa = datos_main.get('humedadRelativa')
                    certificado.proxFecha = datos_main.get('proxFecha')
                    certificado.rango_medicion = datos_main.get('rango_medicion')
                
                # Asignación de datos del dispositivo
                certificado.dispositivo = dispositivo
                if componente:
                    certificado.componente = componente 
                else:
                    certificado.componente = None 
                
                certificado.estado_inicial = estado_inicial_previo
                if empresa_asociada:
                    certificado.id_empresa = empresa_asociada
                else:
                    messages.error(request, "Error: El dispositivo no tiene una empresa asignada.")
                    return redirect('cenerisapp:lista_dispositivos')

                # Guardamos el certificado principal
                certificado.save()


                DatosPDF.objects.update_or_create(
                    certificado=certificado,
                    defaults={
                        'num_paginas_pdf': form.cleaned_data.get('num_paginas_pdf', 1),
                        'codigo_pdf': form.cleaned_data.get('codigo_pdf', ''),
                        'version_pdf': form.cleaned_data.get('version_pdf', ''),
                    }
                )
                
                # Procesamiento de formsets
                if lote_data:
                    # Modo Lote: Creamos objetos desde la sesión
                    for patron_data in lote_data.get('patrones', []):
                        if patron_data:
                            # --- CORRECCIÓN AQUÍ ---
                            # El campo en PatronesCalibracion se llama 'certificado'
                            PatronesCalibracion.objects.create(certificado=certificado, **patron_data)
                    
                    for resultado_data in lote_data.get('resultados', []):
                        if resultado_data:
                            # --- CORRECCIÓN AQUÍ ---
                            # El campo en Resultados se llama 'id_certificado'
                            Resultados.objects.create(id_certificado=certificado, **resultado_data)
                else:
                    # Modo Normal: Guardamos desde el POST
                    patrones_formset.instance = certificado
                    patrones_formset.save()
                    
                    resultados_formset.instance = certificado
                    resultados_formset.save()
                
                messages.success(request, f"Certificado N°{certificado.nro_certificado} creado exitosamente.")
                
                # Redirección a la lista de certificados
                if dispositivo:
                    return redirect('cenerisapp:lista_certificados_dispositivo', dispositivo_id=dispositivo.id_dispositivo)
                else:
                    return redirect('cenerisapp:lista_dispositivos')
            else:
                messages.error(request, "Por favor, corrige los errores en el formulario.")
                print("--- ERRORES DEL FORMULARIO PRINCIPAL ---")
                print(form.errors.as_json())
                print("\n--- ERRORES DEL FORMSET DE ANEXOS ---")
                print(formset.errors)
                print("Non-form errors:", formset.non_form_errors())

    else:
        
        if lote_activo:
            # Usamos los datos de la sesión como valores iniciales
            form = CertificadoForm(initial=lote_data.get('main'))
            patrones_formset = PatronesFormSet(prefix='patrones', initial=lote_data.get('patrones'))
            resultados_formset = ResultadosFormSet(prefix='resultados', initial=lote_data.get('resultados'))
        else:
            # Si no hay datos de lote, el formulario se carga vacío
            form = CertificadoForm()
            patrones_formset = PatronesFormSet(prefix='patrones')
            resultados_formset = ResultadosFormSet(prefix='resultados')
    
    context = {
        'form': form,
        'patrones_formset': patrones_formset,
        'resultados_formset': resultados_formset,
        'dispositivo': dispositivo,
        'componente': componente, # Puede ser None para portátiles
        'empresa': empresa_asociada,
        'titulo': f'Registrar Nuevo Certificado para: {dispositivo.nomDisp}' + (f' - {componente.nomComp}' if componente else ''),
        'estado_inicial_para_mostrar': estado_inicial_previo,
        'lote_activo': lote_activo,
    }
    return render(request, 'certificado/certificado_form.html', context)


@login_required
def seleccionar_dispositivos_lote(request):
    lote_data = request.session.get('lote_certificado_data')
    if not lote_data:
        messages.warning(request, "Primero debe configurar los datos del lote.")
        return redirect('configurar_lote_certificacion')

    AnexoFormSet = formset_factory(AnexoCertificadoForm, extra=1)
    if request.method == 'POST':
        seleccionados_str = request.POST.get('todos_los_seleccionados', '')
        dispositivos_ids = seleccionados_str.split(',') if seleccionados_str else []
        # Obtenemos la lista de IDs de los dispositivos SELECCIONADOS
        # dispositivos_ids = request.POST.getlist('dispositivos_seleccionados')
        anexos_paths_str = request.POST.get('anexos_paths', '')
        anexos_paths = anexos_paths_str.split(',') if anexos_paths_str else []
        
        programa_id = request.POST.get('programa')
        
        if not dispositivos_ids:
            messages.error(request, "No ha seleccionado ningún dispositivo.")
            return redirect('cenerisapp:seleccionar_dispositivos_lote')

        programa = get_object_or_404(Programa, pk=programa_id) if programa_id else None
            
        certificados_creados = []
        errores = []
        
        for dispositivo_id in dispositivos_ids:
            try:
                with transaction.atomic():
                        dispositivo = Dispositivo.objects.get(pk=dispositivo_id)
                            
                        # --- ¡NUEVA LÓGICA PARA DATOS INDIVIDUALES! ---
                        # Construimos el 'name' del input para este dispositivo
                        nro_certificado_name = f'nro_certificado_D{dispositivo_id}'
                        estado_final_name = f'estado_final_D{dispositivo_id}'
                        version_name = f'version_D{dispositivo_id}'
                            
                        # Leemos los valores del POST
                        nro_certificado_individual = request.POST.get(nro_certificado_name, '').strip()
                        estado_final_individual = request.POST.get(estado_final_name, 'Operativo') # 'Calibrado' por defecto
                        version_individual = request.POST.get(version_name, '01')

                        # Validación: el número de certificado es obligatorio
                        if not nro_certificado_individual:
                            errores.append(f"Falta el N° de Certificado para el dispositivo '{dispositivo.nomDisp}'.")
                            continue # Saltamos este dispositivo y continuamos con el siguiente

                        # Validación de duplicados
                        if Certificado.objects.filter(nro_certificado=nro_certificado_individual).exists():
                            errores.append(f"El N° de Certificado '{nro_certificado_individual}' ya existe en la base de datos.")
                            continue

                        # --- CÓDIGO COMPLETO PARA CREAR EL CERTIFICADO ---
                        certificado = Certificado(
                            dispositivo=dispositivo,
                            id_empresa=dispositivo.id_empresa,
                            id_programa=programa,
                                
                            # Datos comunes del lote (desde la sesión)
                            temp=lote_data['main'].get('temp'),
                            presion=lote_data['main'].get('presion'),
                            humedadRelativa=lote_data['main'].get('humedadRelativa'),
                            proxFecha=lote_data['main'].get('proxFecha'),
                            rango_medicion=lote_data['main'].get('rango_medicion'),
                                
                            # Datos individuales (leídos del POST)
                            nro_certificado=nro_certificado_individual,
                            estadoFinal=estado_final_individual,
                                
                            # Asumimos que el estado inicial se puede determinar o viene del lote
                            # Para este ejemplo, lo tomaremos del último certificado si existe.
                            estado_inicial=Certificado.objects.filter(dispositivo=dispositivo).order_by('-fechCertificado').first().estadoFinal if Certificado.objects.filter(dispositivo=dispositivo).exists() else "Primera Calibración",
                        )
                            
                        certificado.save()

                        from django.core.files import File
                        for path in anexos_paths:
                            if default_storage.exists(path):
                                with default_storage.open(path) as f:
                                    AnexoCertificado.objects.create(
                                        certificado=certificado,
                                        imagen=File(f, name=os.path.basename(path))
                                    )

                        DatosPDF.objects.create(
                            certificado=certificado,
                            version_pdf=version_individual # <-- Asignamos la versión individual
                        )

                        # Creamos sus Patrones y Resultados desde el lote
                        for patron_data in lote_data.get('patrones', []):
                            if patron_data: PatronesCalibracion.objects.create(certificado=certificado, **patron_data)
                        for resultado_data in lote_data.get('resultados', []):
                            if resultado_data: Resultados.objects.create(id_certificado=certificado, **resultado_data)
                            
                        certificados_creados.append(certificado.nro_certificado)
            
            except Exception as e:
                errores.append(f"Error inesperado con dispositivo ID {dispositivo_id}: {e}")
                print(f"--- TRACEBACK PARA ERROR EN DISPOSITIVO ID {dispositivo_id} ---")
                import traceback
                traceback.print_exc()
                print("---------------------------------------------------------")
        
        for path in anexos_paths:
            if default_storage.exists(path):
                default_storage.delete(path)
        
        if certificados_creados:
            messages.success(request, f"Se crearon exitosamente {len(certificados_creados)} certificados: {', '.join(certificados_creados)}.")
        if errores:
            messages.error(request, f"Ocurrieron errores: {'; '.join(errores)}")
        
        # Limpiamos la sesión del lote después de usarla
        request.session.pop('lote_certificado_data', None)
        return redirect('cenerisapp:lista_dispositivos')

    # Si la petición es GET, mostramos la lista de dispositivos
    else:
        query = request.GET.get('q', '')
        # Mostramos todos los dispositivos portátiles elegibles
        dispositivos_elegibles = Dispositivo.objects.filter(tipoDisp='Portatil')
        
        if query:
            # Filtramos por nombre del dispositivo O por número de serie
            dispositivos_elegibles = dispositivos_elegibles.filter(
                Q(nomDisp__icontains=query) |
                Q(num_serie__icontains=query)
            )
        programas_disponibles = Programa.objects.filter(totalEjecutado__lt=F('totalPrograma'))

        anexos_formset = AnexoFormSet(prefix='anexos')

        context = {
            'titulo': 'Paso 2: Seleccionar Dispositivos para el Lote',
            'dispositivos': dispositivos_elegibles,
            'lote_data': lote_data,
            'query': query, # Pasamos la query para que el buscador la recuerde
            'programas': programas_disponibles,
            'anexos_formset': anexos_formset,
        }
        return render(request, 'certificado/seleccionar_dispositivos_lote.html', context)


@login_required
def descargar_certificado(request, certificado_id):
    print("=============================================")
    print(f"INICIANDO DESCARGA DE PDF PARA CERTIFICADO ID: {certificado_id}")
    print("=============================================")
    certificado = get_object_or_404(Certificado, pk=certificado_id)
    
    # Pass the 'request' object as the first argument to the function
    return generar_pdf_respuesta(request, certificado)


@login_required
def lista_certificados_dispositivo(request, dispositivo_id): # <-- AÑADE el argumento aquí
    
    dispositivo = get_object_or_404(Dispositivo, pk=dispositivo_id)
    
    certificados = Certificado.objects.filter(dispositivo=dispositivo).order_by('-fechCertificado')
    sensores_del_dispositivo = Sensor.objects.filter(dispositivo_instalado=dispositivo)
    context = {
        'dispositivo': dispositivo,
        'certificados': certificados,
        'titulo': f'Certificados para {dispositivo.nomDisp}',
        'sensores_del_dispositivo': sensores_del_dispositivo,
    }
    return render(request, 'certificado/lista_certificados_dispositivos.html', context)


def lista_certificados(request):
    certificados = Certificado.objects.all()
    return render(request, 'certificado/lista_certificados.html', {'certificados': certificados})
