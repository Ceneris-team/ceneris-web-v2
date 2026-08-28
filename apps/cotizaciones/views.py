from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import CotizacionForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from administracion.decorators import group_required
from .models import Empresa, Contacto, Cotizaciones
from django.contrib.auth.decorators import user_passes_test # Para restringir el acceso
from django.db.models import Count
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404 # Útil para obtener un objeto o mostrar un error 404
from .models import ProcesoCotizacion
from .forms import AgendarCitaForm, RegistrarEncuentroForm, CrearCotizacionForm
from django.contrib.auth.models import User
from .forms import CotizacionPrincipalForm, DetalleCotizacionFormSet
from django.db.models import Q # Para consultas complejas
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import json
from .forms import EmpresaForm
import datetime
import calendar
from decimal import Decimal
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth

# Create your views here.


@login_required
@group_required('Cotizaciones')
def editar_cotizacion(request, pk):
    cotizacion = get_object_or_404(Cotizaciones, pk=pk)
    
    if request.method == 'POST':

        form = CotizacionForm(request.POST,instance=cotizacion)
        if form.is_valid():
            cleaned_data = form.cleaned_data

            empresa, _ = Empresa.objects.get_or_create(
                ruc=cleaned_data['ruc'],
                defaults={'nombre': cleaned_data['nombre_empresa'],'ubicacion': cleaned_data['ubicacion']}
            )

            contacto, _ = Contacto.objects.get_or_create(
                correo=cleaned_data['correo'],
                defaults={'empresa': empresa, 'nombre': cleaned_data['nombre_contacto'], 'telefono': cleaned_data['telefono']}
            )

            # Actualizamos la instancia de cotización
            cotizacion_a_guardar = form.save(commit=False) # No guardar en DB todavía
            cotizacion_a_guardar.empresa = empresa
            cotizacion_a_guardar.contacto = contacto
            cotizacion_a_guardar.save() # Ahora sí, guardar todo

            return redirect(reverse('cotizaciones:lista_cotizaciones'))
    else:
        # Si es GET, creamos el formulario y lo pre-poblamos con los datos de la instancia
        # Creamos un diccionario con los datos iniciales
        initial_data = {
            'nombre_empresa': cotizacion.empresa.nombre,
            'ruc': cotizacion.empresa.ruc,
            'ubicacion': cotizacion.empresa.ubicacion,
            'nombre_contacto': cotizacion.contacto.nombre,
            'correo': cotizacion.contacto.correo,
            'telefono': cotizacion.contacto.telefono,
        }
        form = CotizacionForm(instance=cotizacion, initial=initial_data)

    return render(request, 'procesos/editar_cotizacion.html', {'form': form})

@login_required
@group_required('Cotizaciones')
def dashboard_cotizaciones(request):
    # Aquí iría la lógica para recopilar datos estadísticos
    # Por ahora, simplemente renderizamos una plantilla vacía
    return render(request, 'cotizaciones/dashboard_cotizaciones.html')

@login_required
@group_required('Cotizaciones')
@login_required
def lista_procesos(request):
    procesos = ProcesoCotizacion.objects.all().order_by('-creado_el')
    return render(request, 'procesos/lista_procesos.html', {'procesos': procesos})

@login_required
@group_required('Cotizaciones')
@login_required
def agendar_cita(request):
    if request.method == 'POST':
        form = AgendarCitaForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data

            # 1. Busca o crea la Empresa usando el RUC como identificador único
            empresa, created_empresa = Empresa.objects.get_or_create(
                ruc=cleaned_data['ruc'],
                defaults={
                    'nombre': cleaned_data['nombre_empresa'],
                    'ubicacion': cleaned_data['ubicacion']
                }
            )

            # 2. Busca o crea el Contacto usando el correo como identificador único
            contacto, created_contacto = Contacto.objects.get_or_create(
                correo=cleaned_data['correo'],
                defaults={
                    'empresa': empresa,
                    'nombre': cleaned_data['nombre_contacto'],
                    'telefono': cleaned_data['telefono']
                }
            )

            # 3. Crea el Proceso de Cotización y lo enlaza
            proceso = ProcesoCotizacion.objects.create(
                empresa=empresa,
                contacto=contacto,
                fecha_citacion=cleaned_data['fecha_citacion'],
                usuario_agenda=request.user  # Asigna al usuario actual
            )
            
            messages.success(request, f"Proceso para '{empresa.nombre}' iniciado correctamente.")
            return redirect('cotizaciones:lista_procesos')
    else:
        form = AgendarCitaForm()
        
    return render(request, 'procesos/agendar_cita.html', {'form': form})

@login_required
@group_required('Cotizaciones')
@login_required
def detalle_proceso(request, pk):
    proceso = get_object_or_404(ProcesoCotizacion, pk=pk)
    
    # Lógica para el formulario de registrar encuentro
    if 'registrar_encuentro' in request.POST:
        encuentro_form = RegistrarEncuentroForm(request.POST, instance=proceso)
        if encuentro_form.is_valid():
            encuentro = encuentro_form.save(commit=False)
            encuentro.usuario_encuentro = request.user # Asigna al usuario actual
            encuentro.save()
            return redirect('cotizaciones:detalle_proceso', pk=proceso.pk)
    else:
        encuentro_form = RegistrarEncuentroForm(instance=proceso)

    return render(request, 'procesos/detalle_proceso.html', {
        'proceso': proceso,
        'encuentro_form': encuentro_form,
    })

@login_required
@group_required('Cotizaciones')
@login_required
def crear_cotizacion(request, proceso_pk):
    proceso = get_object_or_404(ProcesoCotizacion, pk=proceso_pk)
    
    if request.method == 'POST':
        form = CotizacionPrincipalForm(request.POST)
        formset = DetalleCotizacionFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # 1. Guarda la cotización principal pero sin enviar a la BD aún
            cotizacion = form.save(commit=False)
            cotizacion.usuario_creador = request.user
            cotizacion.save() # Ahora la guardamos para que tenga un ID

            # 2. Asocia el formset con la cotización recién creada
            formset.instance = cotizacion
            formset.save() # Guarda todos los ítems de detalle

            # 3. Llama al método para calcular y guardar los totales
            cotizacion.calcular_totales()

            # 4. Vincula la cotización final con el proceso
            proceso.cotizacion_final = cotizacion
            proceso.save()
            
            messages.success(request, f"Cotización #{cotizacion.id} creada exitosamente.")
            return redirect('cotizaciones:detalle_proceso', pk=proceso.pk)
    else:
        form = CotizacionPrincipalForm()
        formset = DetalleCotizacionFormSet()
        
    return render(request, 'cotizaciones/crear_cotizacion.html', {
        'form': form,
        'formset': formset,
        'proceso': proceso
    })

@login_required
def lista_empresas(request):
    """
    Muestra una lista de todas las empresas y los comerciales que han iniciado
    procesos con ellas.
    """
    # 1. Obtenemos todas las empresas, ordenadas por nombre.
    # Usamos prefetch_related para cargar eficientemente los procesos y los usuarios asociados
    # en un número mínimo de consultas a la base de datos.
    empresas_qs = Empresa.objects.prefetch_related(
        'procesocotizacion_set__usuario_agenda'
    ).order_by('nombre')

    # 2. Procesamos los datos para que sean fáciles de usar en la plantilla.
    # Aunque podríamos hacer esto en la plantilla, es más limpio y mantenible hacerlo aquí.
    empresas_con_vendedores = []
    for empresa in empresas_qs:
        # Usamos un set para asegurarnos de que cada vendedor aparezca solo una vez por empresa.
        vendedores = set()
        for proceso in empresa.procesocotizacion_set.all():
            if proceso.usuario_agenda:
                vendedores.add(proceso.usuario_agenda.username)
        
        empresas_con_vendedores.append({
            'empresa': empresa,
            'vendedores': sorted(list(vendedores)) # Lo convertimos a una lista ordenada para la plantilla
        })

    context = {
        'empresas_data': empresas_con_vendedores
    }

    return render(request, 'empresas/lista_empresas.html', context)

@login_required
@require_GET # Esta vista solo debe aceptar peticiones GET
def check_ruc_view(request):
    """
    Endpoint que recibe un RUC y verifica si existe un proceso pendiente.
    Un proceso se considera 'pendiente' si no tiene una cotización final,
    o si la tiene, esta no está 'aprobada' ni 'rechazada'.
    """
    ruc = request.GET.get('ruc', None)
    if not ruc:
        return JsonResponse({'error': 'RUC no proporcionado'}, status=400)

    # Buscamos procesos que NO estén terminados (aprobados/rechazados)
    proceso_existente = ProcesoCotizacion.objects.filter(
        empresa__ruc=ruc
    ).exclude(
        Q(cotizacion_final__estado='aprobada') | Q(cotizacion_final__estado='rechazada')
    ).first()

    if proceso_existente:
        data = {
            'exists': True,
            'agendado_por': proceso_existente.usuario_agenda.username if proceso_existente.usuario_agenda else 'un usuario desconocido',
            'proceso_pk': proceso_existente.pk
        }
    else:
        data = {'exists': False}
        
    return JsonResponse(data)


@login_required
def reasignar_proceso_view(request, proceso_pk):
    """
    Reasigna el 'usuario_agenda' de un proceso existente al usuario actual
    y lo redirige a la página de detalle.
    """
    proceso = get_object_or_404(ProcesoCotizacion, pk=proceso_pk)
    
    usuario_anterior = proceso.usuario_agenda.username if proceso.usuario_agenda else 'Nadie'
    
    # Actualizamos el usuario
    proceso.usuario_agenda = request.user
    proceso.save()
    
    messages.info(request, f"El proceso #{proceso.pk} ha sido reasignado de '{usuario_anterior}' a ti.")
    
    # Redirigimos al detalle del proceso para que el nuevo usuario continúe el flujo
    return redirect('cotizaciones:detalle_proceso', pk=proceso.pk)

@login_required # Podrías cambiarlo a @group_required si quieres
def dashboard_cotizaciones(request):
    # --- Lógica de Filtro por Año ---
    selected_year = int(request.GET.get('year', datetime.date.today().year))

    # --- Filtros base por año ---
    procesos_del_año = ProcesoCotizacion.objects.filter(creado_el__year=selected_year)
    cotizaciones_del_año = Cotizaciones.objects.filter(fecha_creacion__year=selected_year)

    # --- 1. CÁLCULO DE TARJETAS DE KPIs ---
    
    # KPI 1: Total de procesos iniciados
    kpi_total_procesos = procesos_del_año.count()

    # Cotizaciones aprobadas y totales para cálculos
    cotizaciones_aprobadas = cotizaciones_del_año.filter(estado='aprobada')
    total_generadas = cotizaciones_del_año.count()
    total_aprobadas_count = cotizaciones_aprobadas.count()

    # KPI 2: Tasa de Conversión
    kpi_tasa_conversion = round((total_aprobadas_count / total_generadas) * 100) if total_generadas > 0 else 0
    
    # KPI 3: Valor Total Aprobado
    kpi_valor_aprobado = cotizaciones_aprobadas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    # KPI 4: Cotizaciones Aprobadas (conteo)
    kpi_cotizaciones_aprobadas = total_aprobadas_count

    # KPI 5: Top Comercial
    top_comercial_data = cotizaciones_aprobadas.values('usuario_creador__username').annotate(
        total_valor=Sum('total')
    ).order_by('-total_valor').first()
    kpi_top_comercial = top_comercial_data['usuario_creador__username'] if top_comercial_data else "N/A"

    # KPI 6: Ticket Promedio
    kpi_ticket_promedio = cotizaciones_aprobadas.aggregate(avg=Avg('total'))['avg'] or Decimal('0.00')

    # --- 2. PREPARACIÓN DE DATOS PARA GRÁFICOS ---

    # Gráfico 1: Valor Aprobado por Mes (Líneas)
    ventas_mensuales = cotizaciones_aprobadas.annotate(
        month=TruncMonth('fecha_creacion')
    ).values('month').annotate(
        total_valor=Sum('total')
    ).order_by('month')
    
    ventas_dict = {item['month'].month: item['total_valor'] for item in ventas_mensuales}
    line_chart_data = {
        'labels': [calendar.month_abbr[i] for i in range(1, 13)],
        'data': [ventas_dict.get(i, 0) for i in range(1, 13)]
    }

    # Gráfico 2: Top 5 Comerciales por Valor (Barras Horizontales)
    top_5_comerciales = cotizaciones_aprobadas.values('usuario_creador__username').annotate(
        total_valor=Sum('total')
    ).order_by('-total_valor')[:5]
    bar_chart_data = {
        'labels': [item['usuario_creador__username'] for item in top_5_comerciales],
        'data': [item['total_valor'] for item in top_5_comerciales]
    }

    # Gráfico 3: Distribución de Cotizaciones por Estado (Anillo/Dona)
    distribucion_estado = cotizaciones_del_año.values('estado').annotate(
        total=Count('id')
    ).order_by('-total')
    estado_map = dict(Cotizaciones.ESTADO_CHOICES)
    doughnut_chart_data = {
        'labels': [estado_map.get(item['estado'], item['estado']) for item in distribucion_estado],
        'data': [item['total'] for item in distribucion_estado]
    }
    
    # Helper para convertir Decimal a float para JSON
    def _decimal_to_native(obj):
        if isinstance(obj, Decimal): return float(obj)
        if isinstance(obj, dict): return {k: _decimal_to_native(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_decimal_to_native(v) for v in obj]
        return obj

    context = {
        'titulo': f'Dashboard de Ventas - {selected_year}',
        'current_view': 'dashboard_cotizaciones',
        'selected_year': selected_year,
        'available_years': range(2023, datetime.date.today().year + 2),
        
        # KPIs
        'kpi_total_procesos': kpi_total_procesos,
        'kpi_tasa_conversion': kpi_tasa_conversion,
        'kpi_valor_aprobado': kpi_valor_aprobado,
        'kpi_cotizaciones_aprobadas': kpi_cotizaciones_aprobadas,
        'kpi_top_comercial': kpi_top_comercial,
        'kpi_ticket_promedio': kpi_ticket_promedio,

        # Datos para Chart.js
        'line_chart_data': json.dumps(_decimal_to_native(line_chart_data)),
        'bar_chart_data': json.dumps(_decimal_to_native(bar_chart_data)),
        'doughnut_chart_data': json.dumps(_decimal_to_native(doughnut_chart_data)),
    }
    return render(request, 'cotizaciones/dashboard_cotizaciones.html', context)

@login_required
def gestion_empresas(request):
    """
    Página central para que los comerciales registren nuevas empresas y vean
    la lista completa de todas las empresas existentes.
    """
    # Obtenemos TODAS las empresas, sin filtrar por usuario.
    empresas_list = Empresa.objects.order_by('nombre')

    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            # Usamos get_or_create para evitar duplicar empresas por RUC
            ruc = form.cleaned_data['ruc']
            empresa, created = Empresa.objects.get_or_create(
                ruc=ruc,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'ubicacion': form.cleaned_data['ubicacion']
                }
            )

            if created:
                # El historial de 'simple-history' registrará qué usuario hizo esto
                messages.success(request, f"Empresa '{empresa.nombre}' registrada en la base de datos central.")
            else:
                messages.warning(request, f"La empresa con RUC {ruc} ya existía en el sistema.")
            
            # Limpiamos el formulario después de un registro exitoso
            return redirect('cotizaciones:gestion_empresas')
    else:
        form = EmpresaForm()

    context = {
        'form': form,
        'empresas_list': empresas_list,
    }
    return render(request, 'cotizaciones/gestion_empresas.html', context)

@login_required
def gestion_empresas(request):
    """
    Página central para registrar nuevas empresas y ver/buscar en la lista completa.
    """
    # Lógica de Búsqueda
    query = request.GET.get('q', '')
    if query:
        # Busca por nombre de empresa O por RUC
        empresas_list = Empresa.objects.filter(
            Q(nombre__icontains=query) | Q(ruc__icontains=query)
        ).order_by('nombre')
    else:
        empresas_list = Empresa.objects.order_by('nombre')

    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            ruc = form.cleaned_data['ruc']
            empresa, created = Empresa.objects.get_or_create(
                ruc=ruc,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'ubicacion': form.cleaned_data['ubicacion']
                }
            )
            if created:
                messages.success(request, f"Empresa '{empresa.nombre}' registrada exitosamente.")
            else:
                messages.warning(request, f"La empresa con RUC {ruc} ya existía.")
            return redirect('cotizaciones:gestion_empresas')
    else:
        form = EmpresaForm()

    context = {
        'form': form,
        'empresas_list': empresas_list,
        'search_query': query, # Para mantener el término de búsqueda en el input
    }
    return render(request, 'cotizaciones/gestion_empresas.html', context)

@login_required
def registrar_empresa(request):
    """
    Maneja el formulario multi-paso para registrar una nueva empresa.
    """
    if request.method == 'POST':
        # Nota: Aquí he simplificado la lógica. El formulario multi-paso
        # en realidad no necesita lógica especial en la vista si todos los
        # campos pertenecen al mismo modelo. Se envían todos al final.
        form = EmpresaForm(request.POST)
        if form.is_valid():
            ruc = form.cleaned_data['ruc']
            # Usamos 'get_or_create' para evitar duplicados por RUC
            empresa, created = Empresa.objects.get_or_create(
                ruc=ruc,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'ubicacion': form.cleaned_data['ubicacion']
                }
            )
            
            if created:
                messages.success(request, f"Empresa '{empresa.nombre}' registrada exitosamente.")
            else:
                messages.warning(request, f"La empresa con RUC {ruc} ya existía en el sistema.")
            
            # Después de registrar, lo llevamos a la lista para que vea el resultado.
            return redirect('cotizaciones:lista_empresas_central')
    else:
        form = EmpresaForm()

    context = {
        'form': form,
        'form_title': 'Registrar Nueva Empresa', # Título para la plantilla
    }
    return render(request, 'empresas/registrar_empresa.html', context)

@login_required
def lista_empresas_central(request):
    """
    Muestra la lista completa de empresas con una función de búsqueda.
    Este es el punto de entrada principal para la gestión de empresas.
    """
    query = request.GET.get('q', '')
    if query:
        empresas_list = Empresa.objects.filter(
            Q(nombre__icontains=query) | Q(ruc__icontains=query)
        ).order_by('nombre')
    else:
        empresas_list = Empresa.objects.all().order_by('nombre')

    context = {
        'empresas_list': empresas_list,
        'search_query': query,
    }
    return render(request, 'empresas/lista_empresas_central.html', context)

@login_required
def centro_gestion_empresas(request):
    """
    Muestra el centro de gestión con tarjetas de navegación para
    registrar una nueva empresa o ver la lista existente.
    """
    # Esta vista no necesita pasar datos complejos, solo renderizar la plantilla.
    return render(request, 'empresas/centro_gestion_empresas.html')