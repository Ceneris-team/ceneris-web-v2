# administracion/views.py

from django.shortcuts import render, redirect
from django.forms import formset_factory
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import UpdateView, DeleteView, ListView, CreateView
from django.urls import reverse_lazy, reverse
from .models import Requerimiento, RegistroConsumo
from .forms import RequerimientoForm, RegistroConsumoForm # <-- Añade el nuevo form
from .forms import RequerimientoForm
from .decorators import group_required
from .models import Requerimiento, RegistroConsumo # <-- Asegúrate de importar RegistroConsumo
import datetime
from dateutil.relativedelta import relativedelta
import datetime
import calendar
import json
from .models import Agente 
from decimal import Decimal
from django.db.models import Sum, F, Value, Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce


@login_required
@group_required('Administracion')
def gestionar_requerimientos(request):
    RequerimientoFormSet = formset_factory(RequerimientoForm, extra=1, can_delete=True)

    if request.method == 'POST':
        fecha_inicio_str = request.POST.get('fecha_inicio')
        fecha_fin_str = request.POST.get('fecha_fin')
        formset = RequerimientoFormSet(request.POST)

        if not fecha_inicio_str or not fecha_fin_str:
            messages.error(request, 'Debe especificar la fecha de inicio y fin del período.')
            return render(request, 'administracion/requerimiento_form_tabla.html', {'formset': formset})

        if formset.is_valid():
            requerimientos_para_crear = []
            fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

            diff = relativedelta(fecha_fin, fecha_inicio)
            meses_totales = diff.years * 12 + diff.months
            if meses_totales <= 0:
                meses_totales = 1

            for form in formset:
                if not form.has_changed() or form.cleaned_data.get('DELETE'):
                    continue
                
                cantidad_total = form.cleaned_data.get('cantidad_total')
                meta_calculada = 0
                
                if meses_totales > 0 and cantidad_total:
                    # --- INICIO DEL CAMBIO ---
                    # Usamos round() sin segundo argumento para redondear al entero más cercano.
                    meta_calculada = round(cantidad_total / meses_totales, 2)
                    # --- FIN DEL CAMBIO ---

                requerimiento = Requerimiento(
                    tipo_monitoreo=form.cleaned_data.get('tipo_monitoreo'),
                    agente=form.cleaned_data.get('agente'),
                    cantidad_total=cantidad_total,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    meta_mensual=meta_calculada
                )
                requerimientos_para_crear.append(requerimiento)
            
            if requerimientos_para_crear:
                Requerimiento.objects.bulk_create(requerimientos_para_crear)
                messages.success(request, f'Se han guardado {len(requerimientos_para_crear)} requerimiento(s) correctamente.')
            else:
                messages.info(request, 'No se ingresó ningún requerimiento nuevo para guardar.')

            return redirect('administracion:crear_requerimiento')
        else:
            messages.error(request, 'Por favor, corrige los errores en la tabla.')
    else:
        formset = RequerimientoFormSet()

    context = {
        'formset': formset,
        'titulo': 'Ingresar Nuevos Requerimientos',
        'current_view': 'crear_requerimiento',
    }
    return render(request, 'administracion/requerimiento_form_tabla.html', context)

@login_required
# Permitimos el acceso a varios grupos para consulta
@group_required('Administracion', 'RecursosHumanos', 'Calidad')
def lista_requerimientos(request):
    requerimientos = Requerimiento.objects.all().order_by('-creado_en')

    # Lectura de filtros desde query string
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()

    if q:
        # `agente` es una ForeignKey a `Agente`. Para filtrar por texto
        # debemos usar el campo del modelo relacionado (`nombre_agente`).
        requerimientos = requerimientos.filter(agente__nombre_agente__icontains=q)
    if tipo:
        # Filtramos por el valor exacto en tipo_monitoreo (se pasan las claves desde el select)
        requerimientos = requerimientos.filter(tipo_monitoreo=tipo)

    tipos_monitoreo = list(Requerimiento.TIPO_MONITOREO_CHOICES)
    # Obtener lista de agentes registrados (Agente.nombre_agente) para el selector
    try:
        agentes_qs = Agente.objects.filter(activo=True).order_by('nombre_agente')
        agentes_choices = [('', 'Todos')] + [(a.nombre_agente, a.nombre_agente) for a in agentes_qs]
    except Exception:
        agentes_choices = [('', 'Todos')]

    context = {
        'requerimientos': requerimientos,
        'titulo': 'Consulta de Requerimientos',
        'current_view': 'lista_requerimientos',
        'tipos_monitoreo': tipos_monitoreo,
        'current_filters': {'q': q, 'tipo': tipo},
        'agentes_choices': agentes_choices,
    }
    return render(request, 'administracion/lista_requerimientos.html', context)

# --- VISTA AUXILIAR PARA EDITAR (para el botón "Editar") ---
class RequerimientoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Requerimiento
    # Para la edición, usamos un formulario que SÍ incluye las fechas
    fields = ['tipo_monitoreo', 'agente', 'cantidad_total', 'fecha_inicio', 'fecha_fin']
    template_name = 'administracion/requerimiento_form_editar.html'
    success_url = reverse_lazy('administracion:lista_requerimientos')

    def test_func(self):
        # Permitir acceso tanto a 'Gestores de Consumo' como a 'Administracion', o superusers
        user = self.request.user
        return user.is_superuser or user.groups.filter(name__in=['Gestores de Consumo', 'Administracion']).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Requerimiento'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'El requerimiento ha sido actualizado correctamente.')
        return super().form_valid(form)

# --- VISTA AUXILIAR PARA ELIMINAR (para el botón "Eliminar") ---
class RequerimientoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Requerimiento
    template_name = 'administracion/requerimiento_confirm_delete.html'
    success_url = reverse_lazy('administracion:lista_requerimientos')

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name__in=['Gestores de Consumo', 'Administracion']).exists()

    def form_valid(self, form):
        messages.success(self.request, 'El requerimiento ha sido eliminado correctamente.')
        return super().form_valid(form)

@login_required
@group_required('Administracion')
def registrar_avance(request, requerimiento_id):
    requerimiento = Requerimiento.objects.get(pk=requerimiento_id)
    historial = RegistroConsumo.objects.filter(requerimiento=requerimiento).order_by('-fecha_registro')

    today = datetime.date.today()
    consumo_del_mes = historial.filter(
        año=today.year, mes=today.month
    ).aggregate(
        total=Sum('cantidad_consumida')
    )['total'] or 0

    meta_mensual = requerimiento.meta_mensual
    porcentaje_actual = 0
    if meta_mensual and meta_mensual > 0:
        porcentaje_actual = round((consumo_del_mes / meta_mensual) * 100)
    
    # Mapa de meses en español (índice 1-12)
    meses_es = [None, 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    progreso_mes_actual = {
        'consumido': consumo_del_mes,
        'meta': meta_mensual,
        'porcentaje': porcentaje_actual,
        'nombre_mes': meses_es[today.month],
        'año': today.year
    }

    if request.method == 'POST':
        form = RegistroConsumoForm(request.POST)
        if form.is_valid():
            nuevo_registro = form.save(commit=False)
            nuevo_registro.requerimiento = requerimiento
            nuevo_registro.registrado_por = request.user
            nuevo_registro.save()
            messages.success(request, f'Se ha añadido un registro de {nuevo_registro.cantidad_consumida} unidades.')
            return redirect('administracion:registrar_avance', requerimiento_id=requerimiento.id)
    else:
        form = RegistroConsumoForm()
        
    context = {
        'form': form,
        'requerimiento': requerimiento,
        'historial': historial,
        'progreso_mes_actual': progreso_mes_actual,
        'titulo': f'Registrar Avance para "{requerimiento.agente}"',
        'range_101': range(101)  # <-- LA LÍNEA CLAVE QUE FALTABA
    }
    return render(request, 'administracion/registrar_avance.html', context)


class RegistroConsumoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RegistroConsumo
    form_class = RegistroConsumoForm # Usamos el formulario que ya creamos
    template_name = 'administracion/registro_consumo_form.html'

    def test_func(self):
        # Solo los gestores pueden editar
        return self.request.user.groups.filter(name='Administracion').exists() or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Registro de Consumo'
        return context

    def get_success_url(self):
        # Redirigimos de vuelta a la página de avance del requerimiento padre
        registro = self.get_object()
        messages.success(self.request, 'El registro ha sido actualizado correctamente.')
        return reverse_lazy('administracion:registrar_avance', kwargs={'requerimiento_id': registro.requerimiento.id})

# --- NUEVA VISTA PARA ELIMINAR UN REGISTRO DE CONSUMO ---
class RegistroConsumoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = RegistroConsumo
    template_name = 'administracion/registro_consumo_confirm_delete.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Administracion').exists() or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Confirmar Eliminación de Registro'
        return context

    def get_success_url(self):
        # Redirigimos de vuelta a la página de avance
        registro = self.get_object()
        messages.success(self.request, 'El registro ha sido eliminado correctamente.')
        return reverse_lazy('administracion:registrar_avance', kwargs={'requerimiento_id': registro.requerimiento.id})

@login_required
@group_required('Administracion', 'Recursos Humanos', 'Calidad')
def reporte_avance_mensual(request):
    # --- INICIO DE LA LÓGICA DE FILTROS INTELIGENTES ---

    # 1. Capturar todos los parámetros de los filtros desde la URL
    selected_year = int(request.GET.get('year', datetime.date.today().year))
    search_query = request.GET.get('q', '')
    tipo_monitoreo_filter = request.GET.get('tipo', '')

    # 2. CORRECCIÓN DEL ERROR: Filtrar requerimientos activos en el año seleccionado
    #    Un requerimiento está activo si:
    #    - Su fecha de inicio es menor o igual al final del año Y
    #    - Su fecha de fin es mayor o igual al inicio del año.
    requerimientos = Requerimiento.objects.filter(
        fecha_inicio__year__lte=selected_year,
        fecha_fin__year__gte=selected_year
    )

    # 3. Aplicar los filtros adicionales si existen
    if search_query:
        # `agente` es una FK -> buscar por el campo `nombre_agente` del modelo relacionado
        requerimientos = requerimientos.filter(agente__nombre_agente__icontains=search_query)
    
    if tipo_monitoreo_filter:
        requerimientos = requerimientos.filter(tipo_monitoreo=tipo_monitoreo_filter)

    # --- INICIO DE LA CORRECCIÓN: CONSULTA ACUMULATIVA ---

    # 1. Obtener la suma total de consumo por requerimiento y por mes en una sola consulta.
    consumos_mensuales = RegistroConsumo.objects.filter(
        año=selected_year,
        requerimiento__in=requerimientos
    ).values(
        'requerimiento_id', 'mes'
    ).annotate(
        total_consumido=Sum('cantidad_consumida')
    ).order_by('requerimiento_id', 'mes')

    # 2. Agrupar los consumos en un diccionario para un acceso rápido y eficiente.
    #    La clave será (requerimiento_id, mes) y el valor será la SUMA total consumida.
    consumos_dict = {}
    for consumo in consumos_mensuales:
        consumos_dict[(consumo['requerimiento_id'], consumo['mes'])] = consumo['total_consumido']

    # --- FIN DE LA CORRECCIÓN ---

    report_data = []
    for req in requerimientos:
        meses_data = []
        for mes_num in range(1, 13):
            consumido = consumos_dict.get((req.id, mes_num), 0)
            meta = req.meta_mensual
            porcentaje = 0
            
            if meta and meta > 0:
                porcentaje = round((consumido / meta) * 100)

            meses_data.append({
                'nombre': calendar.month_name[mes_num], # Usamos el nombre completo del mes
                'consumido': consumido,
                'porcentaje': porcentaje,
            })
        
        report_data.append({
            'requerimiento': req,
            'meses': meses_data
        })

    available_years = range(2023, datetime.date.today().year + 2)
    # Pasamos las opciones de Tipo de Monitoreo al contexto para el selector
    tipos_monitoreo = Requerimiento.TIPO_MONITOREO_CHOICES
    # Obtener lista de agentes registrados (Agente.nombre_agente) para el selector
    try:
        agentes_qs = Agente.objects.filter(activo=True).order_by('nombre_agente')
        agentes_choices = [('', 'Todos')] + [(a.nombre_agente, a.nombre_agente) for a in agentes_qs]
    except Exception:
        agentes_choices = [('', 'Todos')]

    context = {
        'report_data': report_data,
        'selected_year': selected_year,
        'available_years': available_years,
        'tipos_monitoreo': tipos_monitoreo,
        'agentes_choices': agentes_choices,
        'current_filters': { # Pasamos los filtros actuales para mantenerlos en los inputs
            'q': search_query,
            'tipo': tipo_monitoreo_filter
        },
        'titulo': f'Reporte de Avance Mensual - Año {selected_year}',
        'current_view': 'reporte_mensual',
    }
    return render(request, 'administracion/reporte_avance_mensual.html', context)

@login_required
@group_required('Administracion', 'Recursos Humanos', 'Calidad')
def reporte_avance_anual(request):
    # --- INICIO DE LA LÓGICA DE FILTROS INTELIGENTES ---

    # 1. Capturar todos los parámetros de los filtros
    selected_year = int(request.GET.get('year', datetime.date.today().year))
    search_query = request.GET.get('q', '')
    tipo_monitoreo_filter = request.GET.get('tipo', '')

    # 2. Filtrar requerimientos activos en el año seleccionado (la misma lógica que antes)
    requerimientos = Requerimiento.objects.filter(
        fecha_inicio__year__lte=selected_year,
        fecha_fin__year__gte=selected_year
    )

    # 3. Aplicar los filtros adicionales
    if search_query:
        # `agente` es una FK -> buscar por el campo `nombre_agente` del modelo relacionado
        requerimientos = requerimientos.filter(agente__nombre_agente__icontains=search_query)
    
    if tipo_monitoreo_filter:
        requerimientos = requerimientos.filter(tipo_monitoreo=tipo_monitoreo_filter)

    # --- FIN DE LA LÓGICA DE FILTROS INTELIGENTES ---

    # Ahora, el resto de la lógica operará sobre los requerimientos ya filtrados
    requerimiento_ids = requerimientos.values_list('id', flat=True)
    consumos_anuales = RegistroConsumo.objects.filter(
        año=selected_year,
        requerimiento_id__in=requerimiento_ids
    ).values(
        'requerimiento_id'
    ).annotate(
        total_consumido=Sum('cantidad_consumida')
    )
    
    consumos_dict = {item['requerimiento_id']: item['total_consumido'] for item in consumos_anuales}

    report_data = []
    # Iteramos sobre la lista de requerimientos ya filtrada
    for req in requerimientos:
        total_consumido = consumos_dict.get(req.id, 0)
        meta_anual = req.cantidad_total
        
        porcentaje = 0
        if meta_anual and meta_anual > 0:
            porcentaje = round((total_consumido / meta_anual) * 100)
            
        restante = meta_anual - total_consumido

        report_data.append({
            'requerimiento': req,
            'total_consumido': total_consumido,
            'meta_anual': meta_anual,
            'restante': restante,
            'porcentaje': porcentaje,
        })
        
    available_years = range(2023, datetime.date.today().year + 2)
    tipos_monitoreo = Requerimiento.TIPO_MONITOREO_CHOICES
    # Obtener lista de agentes registrados (Agente.nombre_agente) para el selector
    try:
        agentes_qs = Agente.objects.filter(activo=True).order_by('nombre_agente')
        agentes_choices = [('', 'Todos')] + [(a.nombre_agente, a.nombre_agente) for a in agentes_qs]
    except Exception:
        agentes_choices = [('', 'Todos')]

    context = {
        'report_data': report_data,
        'selected_year': selected_year,
        'available_years': available_years,
        'tipos_monitoreo': tipos_monitoreo,
        'agentes_choices': agentes_choices,
        'current_filters': {
            'q': search_query,
            'tipo': tipo_monitoreo_filter
        },
        'titulo': f'Reporte de Avance Anual - Año {selected_year}',
        'current_view': 'reporte_anual',
    }
    return render(request, 'administracion/reporte_avance_anual.html', context)

@login_required
@group_required('Administracion', 'Recursos Humanos', 'Calidad')
def dashboard_estadistico(request):
    """
    Muestra el dashboard estadístico con filtros por año y mes.
    Los KPIs de 'Críticos' y 'Completados' se ajustan al filtro de mes,
    mientras que los gráficos y otros KPIs permanecen anuales.
    """
    
    # --- 1. LÓGICA DE FILTROS (AÑO Y MES) ---
    selected_year = int(request.GET.get('year', datetime.date.today().year))
    # 'anual' es el valor por defecto para la vista general.
    selected_month = request.GET.get('month', 'anual')

    # Diccionario de meses para usar en la vista y la plantilla.
    meses_es = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    
    # Filtro base: Requerimientos activos en el año seleccionado.
    # Usamos select_related para optimizar la obtención del nombre del agente.
    requerimientos_activos = Requerimiento.objects.filter(
        fecha_inicio__year__lte=selected_year,
        fecha_fin__year__gte=selected_year
    )
    # Consulta base de consumos anuales para reutilizar en KPIs y gráficos.
    consumos_del_año = RegistroConsumo.objects.filter(año=selected_year, requerimiento__in=requerimientos_activos)

    # --- 2. CÁLCULO DE TARJETAS DE KPIs (Lógica condicional) ---
    kpi_completados = 0
    kpi_criticos = 0
    
    if selected_month == 'anual':
        # --- LÓGICA PARA LA VISTA ANUAL ---
        consumos_del_año = RegistroConsumo.objects.filter(año=selected_year, requerimiento__in=requerimientos_activos)
        for req in requerimientos_activos:
            consumo_req_anual = consumos_del_año.filter(requerimiento=req).aggregate(total=Sum('cantidad_consumida'))['total'] or 0
            if req.cantidad_total > 0:
                porcentaje_anual = (consumo_req_anual / req.cantidad_total) * 100
                if porcentaje_anual >= 100:
                    kpi_completados += 1
                elif porcentaje_anual < 50: # Umbral de criticidad anual
                    kpi_criticos += 1
    else:
        # --- LÓGICA PARA LA VISTA MENSUAL ---
        selected_month_int = int(selected_month)
        consumos_del_mes = RegistroConsumo.objects.filter(
            año=selected_year, 
            mes=selected_month_int, 
            requerimiento__in=requerimientos_activos
        )
        for req in requerimientos_activos:
            consumo_req_mes = consumos_del_mes.filter(requerimiento=req).aggregate(total=Sum('cantidad_consumida'))['total'] or 0
            # Comparamos el consumo del mes contra la meta mensual.
            if req.meta_mensual > 0:
                porcentaje_mes = (consumo_req_mes / req.meta_mensual) * 100
                if porcentaje_mes >= 100:
                    kpi_completados += 1
                elif porcentaje_mes < 50: # Mismo umbral, pero sobre la base mensual
                    kpi_criticos += 1

    # --- KPIs que SIEMPRE son anuales, independientemente del filtro de mes ---
    kpi_total_requerimientos = requerimientos_activos.count()
    
    # Reutilizamos la consulta de consumos anuales para los siguientes KPIs
    consumos_anuales_totales = RegistroConsumo.objects.filter(año=selected_year, requerimiento__in=requerimientos_activos)
    total_consumido_general = consumos_anuales_totales.aggregate(total=Sum('cantidad_consumida'))['total'] or 0
    meta_anual_general = requerimientos_activos.aggregate(total=Sum('cantidad_total'))['total'] or 0
    
    kpi_progreso_general = round((total_consumido_general / meta_anual_general) * 100) if meta_anual_general > 0 else 0
    
    mes_productivo_data = consumos_anuales_totales.values('mes').annotate(total=Sum('cantidad_consumida')).order_by('-total').first()
    kpi_mes_productivo = meses_es.get(mes_productivo_data['mes']) if mes_productivo_data else "N/A"
    
    kpi_total_consumido_año = total_consumido_general

    # --- 3. PREPARACIÓN DE DATOS PARA GRÁFICOS (Estos siempre muestran datos anuales) ---

    # Gráfico 1: Progreso Anual Acumulado (Líneas)
    meta_mensual_constante = requerimientos_activos.aggregate(total=Sum('meta_mensual'))['total'] or 0
    
    # Obtenemos el consumo real de cada mes en un diccionario para fácil acceso.
    consumo_mensual = consumos_del_año.values('mes').annotate(total=Sum('cantidad_consumida')).order_by('mes')
    consumo_mensual_dict = {item['mes']: item['total'] for item in consumo_mensual}
    
    # Creamos las listas de datos para el gráfico (NO acumulativas).
    meta_mensual_data = []
    consumo_mensual_data = []
    
    for i in range(1, 13):
        # Para la meta, añadimos el mismo valor constante 12 veces.
        meta_mensual_data.append(round(meta_mensual_constante))
        
        # Para el consumo, añadimos el valor de ese mes específico (o 0 si no hubo consumo).
        consumo_mensual_data.append(consumo_mensual_dict.get(i, 0))

    line_chart_data = {
        'labels': [calendar.month_abbr[i] for i in range(1, 13)],
        'meta_data': meta_mensual_data,
        'consumo_data': consumo_mensual_data
    }

    # Gráfico 2: Top 10 Requerimientos con Mayor Carga (Barras Horizontales)
    top_5_carga = requerimientos_activos.order_by('-cantidad_total')[:10]
    # Asegurarnos de convertir los posibles objetos `Agente` a su nombre antes de serializar a JSON.
    def _agente_label(a):
        try:
            # si es FK a Agente
            return a.nombre_agente
        except Exception:
            # si es string u otro tipo
            return str(a)

    bar_chart_data = {
        'labels': [_agente_label(req.agente) for req in top_5_carga],
        'data': [req.cantidad_total for req in top_5_carga]
    }

    # Gráfico 3: Distribución por Tipo de Monitoreo (Anillo/Dona)
    distribucion_tipo = consumos_anuales_totales.values('requerimiento__tipo_monitoreo').annotate(total=Sum('cantidad_consumida')).order_by('-total')
    tipo_map = dict(Requerimiento.TIPO_MONITOREO_CHOICES)
    doughnut_chart_data = {'labels': [tipo_map.get(item['requerimiento__tipo_monitoreo'], item['requerimiento__tipo_monitoreo']) for item in distribucion_tipo], 'data': [item['total'] for item in distribucion_tipo]}

    # --- 4. CONSTRUCCIÓN DEL CONTEXTO FINAL PARA LA PLANTILLA ---
    
    # Helper para convertir Decimals a float para la serialización a JSON
    def _decimal_to_native(obj):
        if isinstance(obj, Decimal): return float(obj)
        if isinstance(obj, dict): return {k: _decimal_to_native(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_decimal_to_native(v) for v in obj]
        return obj

    # Creamos la lista de meses para el selector del formulario
    available_months = [('anual', 'General (Anual)')] + list(meses_es.items())
    
    # Creamos el enlace para la página de críticos, ahora consciente del filtro de mes
    criticos_link = reverse('administracion:lista_requerimientos_criticos') + f'?year={selected_year}&month={selected_month}'

    context = {
        'titulo': f'Dashboard Estadístico - {selected_year}',
        'current_view': 'dashboard_estadistico',
        'selected_year': selected_year,
        'available_years': range(2023, datetime.date.today().year + 2),
        'selected_month': selected_month,
        'available_months': available_months,
        
        # KPIs (los valores de completados/críticos son ahora dinámicos)
        'kpi_total_requerimientos': kpi_total_requerimientos,
        'kpi_progreso_general': kpi_progreso_general,
        'kpi_completados': kpi_completados,
        'kpi_criticos': kpi_criticos,
        'kpi_mes_productivo': kpi_mes_productivo,
        'kpi_total_consumido_año': kpi_total_consumido_año,
        'kpi_criticos_link': criticos_link,

        # Datos para Chart.js (serializados a JSON)
        'line_chart_data': json.dumps(_decimal_to_native(line_chart_data)),
        'bar_chart_data': json.dumps(_decimal_to_native(bar_chart_data)),
        'doughnut_chart_data': json.dumps(_decimal_to_native(doughnut_chart_data)),
    }
    return render(request, 'administracion/dashboard_estadistico.html', context)

@login_required
@group_required('Administracion', 'Recursos Humanos', 'Calidad')
def lista_requerimientos_criticos(request):
    selected_year = int(request.GET.get('year', datetime.date.today().year))
    selected_month = request.GET.get('month', 'anual')
    
    requerimientos_activos = Requerimiento.objects.filter(
        fecha_inicio__year__lte=selected_year,
        fecha_fin__year__gte=selected_year
    )
    
    requerimientos_criticos_data = []
    periodo_texto = f"para todo el año {selected_year}"
    
    if selected_month == 'anual':
        # --- LÓGICA ANUAL ---
        consumos_del_año = RegistroConsumo.objects.filter(año=selected_year)
        for req in requerimientos_activos:
            consumo_req = consumos_del_año.filter(requerimiento=req).aggregate(total=Sum('cantidad_consumida'))['total'] or 0
            if req.cantidad_total > 0:
                porcentaje = (consumo_req / req.cantidad_total) * 100
                if porcentaje < 50:
                    requerimientos_criticos_data.append({
                        'requerimiento': req,
                        'consumo_periodo': consumo_req,
                        'meta_periodo': req.cantidad_total,
                        'porcentaje': int(porcentaje),
                        'explicacion': f"su progreso anual ({int(porcentaje)}%) está por debajo del umbral del 50%."
                    })
    else:
        # --- LÓGICA MENSUAL ---
        selected_month_int = int(selected_month)
        mes_nombre = calendar.month_name[selected_month_int].capitalize()
        periodo_texto = f"para el mes de {mes_nombre} {selected_year}"
        
        consumos_del_mes = RegistroConsumo.objects.filter(año=selected_year, mes=selected_month_int)
        for req in requerimientos_activos:
            consumo_req_mes = consumos_del_mes.filter(requerimiento=req).aggregate(total=Sum('cantidad_consumida'))['total'] or 0
            if req.meta_mensual > 0:
                porcentaje_mes = (consumo_req_mes / req.meta_mensual) * 100
                if porcentaje_mes < 50:
                    requerimientos_criticos_data.append({
                        'requerimiento': req,
                        'consumo_periodo': consumo_req_mes,
                        'meta_periodo': req.meta_mensual,
                        'porcentaje': int(porcentaje_mes),
                        'explicacion': f"su progreso para {mes_nombre} ({int(porcentaje_mes)}%) está por debajo del 50% de la meta mensual."
                    })

    back_url = reverse('administracion:dashboard_estadistico') + f'?year={selected_year}&month={selected_month}'

    context = {
        'titulo': f'Requerimientos Críticos',
        'current_view': 'dashboard_estadistico',
        'periodo_texto': periodo_texto,
        'requerimientos_criticos': requerimientos_criticos_data,
        'back_url': back_url
    }
    return render(request, 'administracion/lista_requerimientos_criticos.html', context)

class AgenteListView(ListView):
    model = Agente
    template_name = 'agente/agente_list.html'
    context_object_name = 'agentes'
    paginate_by = 15 # Opcional: para paginar la lista si tienes muchos agentes

class AgenteCreateView(CreateView):
    model = Agente
    fields = ['nombre_agente', 'precio_unitario', 'activo']
    # Usamos una plantilla nueva y limpia para evitar problemas con la plantilla dañada previa
    template_name = 'administracion/agente_form_create.html'
    success_url = reverse_lazy('administracion:lista_agentes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Agente'
        return context

class AgenteUpdateView(UpdateView):
    model = Agente
    fields = ['nombre_agente', 'precio_unitario', 'activo']
    # Reuse the clean form template used for create to avoid template issues
    template_name = 'administracion/agente_form_create.html'
    success_url = reverse_lazy('administracion:lista_agentes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Agente'
        return context

class AgenteDeleteView(DeleteView):
    model = Agente
    template_name = 'agente/agente_confirm_delete.html'
    success_url = reverse_lazy('administracion:lista_agentes')


@login_required
@group_required('Administracion')
def reporte_facturacion(request):
    """Reporte que muestra facturación por registros (consumo * precio unitario).

    Implementación robusta: no requiere que `Requerimiento` tenga una FK a `Agente`.
    En lugar de eso hacemos una Subquery sobre `Agente.nombre_agente` y utilizamos
    Coalesce para asegurar un tipo Decimal consistente en la anotación.
    """
    selected_year = int(request.GET.get('year', datetime.date.today().year))
    selected_month = request.GET.get('month', 'anual')

    # Filtro base para los registros de consumo del año seleccionado
    registros = RegistroConsumo.objects.filter(año=selected_year)
    if selected_month != 'anual':
        registros = registros.filter(mes=int(selected_month))

    # Preparar la subconsulta que obtiene el precio del Agente por nombre
    # Determinamos si Requerimiento.agente es una FK en el modelo actual.
    # Si es FK, podemos leer precio_unitario directamente via join; si no, usamos la subconsulta por nombre.
    field = None
    try:
        field = Requerimiento._meta.get_field('agente')
    except Exception:
        field = None

    registros = registros.select_related('requerimiento')

    if field is not None and getattr(field, 'remote_field', None) is not None:
        # agente es una ForeignKey -> usar relación directa
        registros_facturados = registros.select_related('requerimiento__agente').annotate(
            agente_precio=Coalesce(F('requerimiento__agente__precio_unitario'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=12, decimal_places=2)),
            subtotal=F('cantidad_consumida') * F('agente_precio')
        )
    else:
        # agente es un CharField en el modelo -> buscar Agente por nombre
        agente_precio_sq = Agente.objects.filter(
            nombre_agente=OuterRef('requerimiento__agente')
        ).values('precio_unitario')[:1]

        registros_facturados = registros.annotate(
            agente_precio=Coalesce(Subquery(agente_precio_sq), Value(Decimal('0.00')), output_field=DecimalField(max_digits=12, decimal_places=2)),
            subtotal=F('cantidad_consumida') * F('agente_precio')
        )

    total_facturado = registros_facturados.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')

    # Lista de meses para el selector
    meses_es = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    available_months = [('anual', 'General (Anual)')] + list(meses_es.items())

    context = {
        'titulo': 'Reporte de Facturación',
        'current_view': 'reporte_facturacion',
        'selected_year': selected_year,
        'selected_month': selected_month,
        'available_years': range(2023, datetime.date.today().year + 2),
        'available_months': available_months,
        'registros_facturados': registros_facturados,
        'total_facturado': total_facturado
    }
    return render(request, 'administracion/reporte_facturacion.html', context)