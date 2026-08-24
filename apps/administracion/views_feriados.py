# administracion/views_feriados.py
"""Gestión de Feriados (HU-01 CAV-10).

Vistas de la página de feriados y su API JSON (listado, alta, edición y
borrado), consumidas por el calendario interactivo y la tabla CRUD del
template. Adaptado de la funcionalidad de v1 al modelo v2 (4 campos:
fecha, nombre, tipo, ambito).
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FeriadoForm
from .models import Feriado
from .services.feriados import MSG_TAREO_CERRADO, tiene_tareos_cerrados

MESES_ES_FERIADOS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


def _feriado_to_dict(feriado):
    """Serializa un Feriado para la tabla y el calendario (JSON)."""
    return {
        'id': feriado.id,
        'nombre': feriado.nombre,
        'fecha': feriado.fecha.isoformat(),
        'tipo': feriado.tipo,
        'tipo_display': feriado.get_tipo_display(),
        'ambito': feriado.ambito,
        'ambito_display': feriado.get_ambito_display(),
        'sede': feriado.sede_id or '',
        'sede_display': feriado.sede.nombre if feriado.sede_id else '',
        'empresa': feriado.empresa_id or '',
        'empresa_display': feriado.empresa.nombre if feriado.empresa_id else '',
    }


def _primer_error(form):
    """Devuelve el primer mensaje de error del form (para la respuesta JSON)."""
    for campo, errores in form.errors.items():
        if errores:
            return errores[0]
    return 'No se pudo guardar el feriado.'


@login_required
def gestion_feriados(request):
    """Vista principal del módulo de Gestión de Feriados."""
    anio_actual = timezone.now().year

    # El rango de años se deriva de los datos reales para no ocultar años
    # ya cargados, ampliado a futuro.
    anios_registrados = [f.year for f in Feriado.objects.dates('fecha', 'year')]
    anio_min = min(anios_registrados + [anio_actual])
    anio_max = max(anios_registrados + [anio_actual + 5])
    anios_disponibles = list(range(anio_min, anio_max + 1))

    # Import local: evita cualquier problema de orden de carga entre apps
    # (recursoshumanos.services ya importa administracion de forma diferida).
    from recursoshumanos.models import Empresa, Sede

    context = {
        'anio_actual': anio_actual,
        'anios_disponibles': anios_disponibles,
        'meses': list(enumerate(MESES_ES_FERIADOS, start=1)),
        'tipos_feriado': Feriado.Tipo.choices,
        'ambitos_feriado': Feriado.Ambito.choices,
        'sedes': Sede.objects.filter(activo=True).order_by('nombre'),
        'empresas': Empresa.objects.order_by('nombre'),
        'current_view': 'gestion_feriados',
    }
    return render(request, 'administracion/feriados/gestion_feriados.html', context)


@login_required
def feriados_api_list(request):
    """GET feriados/api/?anio=YYYY&mes=MM&tipo=X&q=texto -> listado JSON."""
    anio = request.GET.get('anio')
    mes = request.GET.get('mes')
    tipo = request.GET.get('tipo')
    busqueda = request.GET.get('q', '').strip()

    feriados_qs = Feriado.objects.all()

    if anio:
        try:
            feriados_qs = feriados_qs.filter(fecha__year=int(anio))
        except ValueError:
            pass

    if mes:
        try:
            feriados_qs = feriados_qs.filter(fecha__month=int(mes))
        except ValueError:
            pass

    # Un tipo desconocido se ignora (no filtra) en vez de romper el listado,
    # igual que anio y mes.
    if tipo in Feriado.Tipo.values:
        feriados_qs = feriados_qs.filter(tipo=tipo)

    if busqueda:
        feriados_qs = feriados_qs.filter(Q(nombre__icontains=busqueda))

    feriados = [_feriado_to_dict(f) for f in feriados_qs.order_by('fecha')]
    return JsonResponse({'status': 'ok', 'feriados': feriados})


@login_required
@require_POST
def feriado_api_crear(request):
    """POST feriados/api/crear/ -> registra un feriado nuevo (CAV-54)."""
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    form = FeriadoForm(data)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'message': _primer_error(form)}, status=400)

    feriado = form.save()
    messages.success(request, f'Feriado "{feriado.nombre}" registrado correctamente.')
    return JsonResponse({'status': 'ok', 'feriado': _feriado_to_dict(feriado)})


@login_required
@require_POST
def feriado_api_editar(request, pk):
    """POST feriados/api/<id>/editar/ -> edita un feriado existente (CAV-57)."""
    feriado = get_object_or_404(Feriado, pk=pk)

    # Se guarda antes de instanciar el form: el ModelForm escribe los datos
    # nuevos sobre `feriado` al validar, y despues de eso ya no se puede saber
    # cual era la fecha original.
    fecha_original = feriado.fecha

    # Regla de negocio HU-02: si la fecha actual ya tiene tareos cerrados, el
    # feriado esta congelado y no se toca.
    if tiene_tareos_cerrados(fecha_original):
        return JsonResponse({'status': 'error', 'message': MSG_TAREO_CERRADO}, status=403)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    form = FeriadoForm(data, instance=feriado)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'message': _primer_error(form)}, status=400)

    # Tampoco se puede mover un feriado hacia un dia que ya fue tareado: eso
    # afectaria la asistencia consolidada de la fecha destino.
    fecha_destino = form.cleaned_data['fecha']
    if fecha_destino != fecha_original and tiene_tareos_cerrados(fecha_destino):
        return JsonResponse({'status': 'error', 'message': MSG_TAREO_CERRADO}, status=403)

    feriado = form.save()
    messages.success(request, f'Feriado "{feriado.nombre}" actualizado correctamente.')
    return JsonResponse({'status': 'ok', 'feriado': _feriado_to_dict(feriado)})


@login_required
@require_POST
def feriado_api_eliminar(request, pk):
    """POST feriados/api/<id>/eliminar/ -> elimina un feriado (CAV-57)."""
    feriado = get_object_or_404(Feriado, pk=pk)

    # Regla de negocio HU-02: no se borra un feriado que ya afecta tareos.
    if tiene_tareos_cerrados(feriado.fecha):
        return JsonResponse({'status': 'error', 'message': MSG_TAREO_CERRADO}, status=403)

    feriado.delete()
    messages.success(request, 'Feriado eliminado correctamente.')
    return JsonResponse({'status': 'ok'})
