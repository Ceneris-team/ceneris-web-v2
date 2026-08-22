"""Acumulado de horas trabajadas por período.

RRHH necesita saber, para un rango de fechas que ellos mismos eligen, cuántas
horas acumuló cada trabajador. El dato por día ya lo produce
`recalcular_asistencia_diaria` (`TareoDiario.horas_trabajadas_validas`, que es la
hora real topeada al objetivo del día, con el descuento de almuerzo y las horas
extra aprobadas ya incluidas); aquí solo se agrega ese campo por trabajador.

El reporte no juzga si el total es suficiente: cada modalidad de contrato tiene
su propia exigencia y esa decisión la toma RRHH mirando la cifra. Lo único que
se señala es cuándo el total puede estar mal medido (días con entrada pero sin
salida), porque eso sí es un problema del dato, no del trabajador.

Se agrega `horas_trabajadas_validas` y NO las horas crudas de marcación porque
la pregunta del negocio es "¿cuánto se le paga?", y ese campo es justamente lo
pagable. Las horas extra ya están dentro de él, así que no se vuelven a sumar.

Módulo sin dependencias de request: se prueba llamándolo directo.
"""
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import TareoDiario, Trabajador

# Tipos de jornada que no exigen horas: 'D' = Día libre. Un día libre no cuenta
# como día sin marcar ni como día en que tocaba trabajar.
ESTADOS_SIN_JORNADA = {'D', '', '.'}

CERO = Decimal('0.00')


@dataclass(frozen=True)
class ResumenHorasTrabajador:
    """Acumulado de un trabajador en el período consultado."""

    trabajador: Trabajador
    total_horas: Decimal
    dias_con_horas: int
    dias_esperados: int
    dias_incompletos: int
    dias_sin_marca: int

    @property
    def promedio_diario(self):
        """Horas por día sobre los días en que sí tocaba trabajar."""
        if self.dias_esperados <= 0:
            return CERO
        return (self.total_horas / self.dias_esperados).quantize(Decimal('0.01'))

    @property
    def tiene_alerta(self):
        """Días que marcaron entrada pero no salida distorsionan el acumulado
        hacia abajo (sin par Entrada→Salida el día suma 0 h), así que el total
        de esa persona está subestimado hasta que se corrija la marcación."""
        return self.dias_incompletos > 0


def resumen_horas_por_periodo(
    fecha_inicio,
    fecha_fin,
    *,
    empresa_id=None,
    area_id=None,
    sede_id=None,
    proyecto_id=None,
    trabajador_id=None,
    solo_con_alerta=False,
):
    """Devuelve un `ResumenHorasTrabajador` por trabajador con tareo en el rango.

    `fecha_fin` se recorta a hoy: los días futuros ya existen como `TareoDiario`
    programado (nacen con `resultado='F'` y 0 horas), y contarlos ensuciaría el
    conteo de días con jornadas que aún no han ocurrido.

    Solo aparecen trabajadores que tengan al menos un día de tareo en el rango;
    quien no fue programado no tiene nada que sumar.
    """
    hoy = timezone.localdate()
    fecha_tope = min(fecha_fin, hoy)

    if fecha_tope < fecha_inicio:
        return []

    qs = TareoDiario.objects.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_tope)

    if empresa_id:
        qs = qs.filter(trabajador__empresa_id=empresa_id)
    if area_id:
        qs = qs.filter(trabajador__area_id=area_id)
    if sede_id:
        qs = qs.filter(trabajador__sede_id=sede_id)
    if proyecto_id:
        qs = qs.filter(trabajador__proyectos__id=proyecto_id)
    if trabajador_id:
        qs = qs.filter(trabajador_id=trabajador_id)

    # `dias_esperados` excluye los días libres: son los días en que sí tocaba
    # trabajar, para poder leer el total en contexto.
    #
    # `dias_incompletos` = marcó entrada pero nunca salida. Ese día suma 0 h
    # porque el algoritmo de pares no lo puede cerrar, así que se cuenta aparte
    # para que el total no se lea como abandono del puesto.
    filas = (
        qs.values('trabajador_id')
        .annotate(
            total_horas=Sum('horas_trabajadas_validas'),
            dias_con_horas=Count('id', filter=Q(horas_trabajadas_validas__gt=0)),
            dias_esperados=Count('id', filter=~Q(estado__in=ESTADOS_SIN_JORNADA)),
            dias_incompletos=Count(
                'id',
                filter=Q(hora_entrada_real__isnull=False, hora_salida_real__isnull=True),
            ),
            dias_sin_marca=Count(
                'id',
                filter=Q(hora_entrada_real__isnull=True, hora_salida_real__isnull=True)
                & ~Q(estado__in=ESTADOS_SIN_JORNADA),
            ),
        )
        .order_by()
    )

    # `.values()` sobre un queryset con join a proyectos puede repetir filas; el
    # agrupado por trabajador_id ya las colapsa, pero los trabajadores se cargan
    # en una sola consulta aparte para no golpear la BD por cada fila.
    por_id = {fila['trabajador_id']: fila for fila in filas}
    trabajadores = (
        Trabajador.objects.filter(id__in=por_id.keys())
        .select_related('area', 'empresa', 'sede')
        .order_by('apellido_paterno', 'apellido_materno', 'nombres')
    )

    resumenes = []
    for trabajador in trabajadores:
        fila = por_id[trabajador.id]
        resumen = ResumenHorasTrabajador(
            trabajador=trabajador,
            total_horas=Decimal(str(fila['total_horas'] or 0)).quantize(Decimal('0.01')),
            dias_con_horas=fila['dias_con_horas'],
            dias_esperados=fila['dias_esperados'],
            dias_incompletos=fila['dias_incompletos'],
            dias_sin_marca=fila['dias_sin_marca'],
        )
        if solo_con_alerta and not resumen.tiene_alerta:
            continue
        resumenes.append(resumen)

    return resumenes


def totales_generales(resumenes):
    """Fila de totales del período, para las tarjetas de la cabecera."""
    total_horas = sum((r.total_horas for r in resumenes), CERO)
    return {
        'trabajadores': len(resumenes),
        'total_horas': total_horas.quantize(Decimal('0.01')),
        'con_alerta': sum(1 for r in resumenes if r.tiene_alerta),
    }


def detalle_dias_trabajador(trabajador_id, fecha_inicio, fecha_fin):
    """Días del período de un trabajador, para justificar su acumulado.

    Es el desglose que RRHH abre cuando el total no le cuadra: qué día aportó
    cuántas horas y cuál quedó incompleto.
    """
    hoy = timezone.localdate()
    return (
        TareoDiario.objects.filter(
            trabajador_id=trabajador_id,
            fecha__gte=fecha_inicio,
            fecha__lte=min(fecha_fin, hoy),
        )
        .select_related('trabajador')
        .order_by('fecha')
    )
