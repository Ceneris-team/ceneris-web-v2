# recursoshumanos/motor_reglas.py
"""Motor de reglas de validación de marcación (HT-02 / CAV-12).

Núcleo puro y sin dependencias de los modelos de la app: recibe un
``ContextoMarcacion`` con datos ya resueltos (horario, marcas reales,
tolerancia y si el día es feriado) y devuelve un ``ResultadoEvaluacion`` con
el resultado de asistencia, la tardanza y las etiquetas de la marca.

Se evalúa **feriado + horario + tolerancia en una sola pasada**: quien llama
recolecta los datos una vez (ver ``services.recalcular_asistencia_diaria``) y
este módulo solo decide, en memoria, sin volver a tocar la base de datos. Por
eso puede probarse de forma unitaria sin BD (ver ``tests/test_motor_reglas``).

El orden de prioridad de las reglas está documentado en
``docs/motor_reglas_marcacion.md`` (CAV-168) y refleja el implementado en
``evaluar_marcacion``.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.db import models


class EstadoMarca(models.TextChoices):
    """Etiqueta/clasificación del resultado de una marcación (CAV-167).

    Es independiente de ``TareoDiario.estado`` (tipo de jornada C/O/P/J/D) y de
    ``TareoDiario.resultado`` (F/A/J): describe *cómo* fue la marca del día.
    """
    NORMAL = 'NORMAL', 'Normal'
    TARDANZA = 'TARDANZA', 'Tardanza'
    FERIADO = 'FERIADO', 'Feriado'
    FUERA_DE_HORARIO = 'FUERA_HORARIO', 'Fuera de horario'
    FALTA = 'FALTA', 'Falta'
    JUSTIFICADO = 'JUSTIFICADO', 'Justificado'
    DIA_LIBRE = 'DIA_LIBRE', 'Día libre'
    SIN_HORARIO = 'SIN_HORARIO', 'Sin horario'


# Códigos de ``TareoDiario.estado`` con significado propio para el motor.
ESTADO_DIA_LIBRE = 'D'
ESTADO_JORNADA_HORAS = 'J'
RESULTADO_JUSTIFICADO = 'J'
RESULTADO_ASISTIO = 'A'
RESULTADO_FALTA = 'F'


@dataclass(frozen=True)
class ContextoMarcacion:
    """Entradas ya resueltas para evaluar el día (todo en hora local).

    No contiene objetos del ORM a propósito: son tipos primitivos para que el
    motor sea puro y testeable.
    """
    fecha: date
    estado_jornada: str                 # 'C','O','P','J','D'
    resultado_previo: str               # 'F','A','J' (lo que ya tenía el tareo)
    hora_entrada_programada: time | None
    hora_salida_programada: time | None
    hora_entrada_real: time | None
    hora_salida_real: time | None
    minutos_tolerancia: int
    es_feriado: bool
    tiene_marcas: bool
    # Datos del feriado ya resueltos por el servicio (CAV-13), solo para el
    # detalle legible; el motor no consulta la tabla de feriados.
    nombre_feriado: str | None = None
    ambito_feriado: str | None = None


@dataclass(frozen=True)
class ResultadoEvaluacion:
    """Salida del motor: resultado de asistencia + tardanza + etiquetas."""
    resultado: str                      # 'F','A','J'
    etiqueta: str                       # etiqueta principal (EstadoMarca)
    etiquetas: tuple[str, ...]          # todas las etiquetas aplicables
    horas_tardanza: float
    minutos_tardanza: int
    detalle: str = ''                   # motivo legible de la clasificación


def _normalizar_resultado(valor: str) -> str:
    return (valor or '').upper()


def _detalle_feriado(ctx: ContextoMarcacion, base: str) -> str:
    """Agrega al motivo base el nombre y ámbito del feriado, si se conocen."""
    if not ctx.nombre_feriado:
        return base
    ambito = f' ({ctx.ambito_feriado})' if ctx.ambito_feriado else ''
    return f'{base}: {ctx.nombre_feriado}{ambito}'


def _minutos_tardanza(
    hora_real: time | None,
    hora_programada: time | None,
    minutos_tolerancia: int,
) -> int:
    """Minutos de tardanza tras aplicar la tolerancia.

    Réplica de la fórmula histórica de ``recalcular_asistencia_diaria``: se
    compara la entrada real contra la programada y se descuenta la tolerancia
    configurada. En el límite exacto (real == programada + tolerancia) NO hay
    tardanza. Devuelve 0 si falta algún dato.
    """
    if hora_real is None or hora_programada is None:
        return 0

    base = date.today()
    dt_real = datetime.combine(base, hora_real)
    dt_prog = datetime.combine(base, hora_programada)

    diff_min = (dt_real - dt_prog).total_seconds() / 60 - minutos_tolerancia
    return int(diff_min) if diff_min > 0 else 0


def _fuera_de_horario(ctx: ContextoMarcacion) -> list[str]:
    """Detecta marcas fuera del rango del turno, aplicando la tolerancia.

    Devuelve una lista de motivos (vacía si todo está dentro del rango):
      - 'Entrada anticipada' si la entrada real < entrada_programada - tolerancia.
      - 'Salida posterior'   si la salida real  > salida_programada + tolerancia.
      - 'Salida anticipada'  si la salida real  < salida_programada - tolerancia.
    """
    motivos: list[str] = []
    base = date.today()
    tol = timedelta(minutes=ctx.minutos_tolerancia)

    if ctx.hora_entrada_real and ctx.hora_entrada_programada:
        limite_entrada = (datetime.combine(base, ctx.hora_entrada_programada) - tol).time()
        if ctx.hora_entrada_real < limite_entrada:
            motivos.append('Entrada anticipada')

    if ctx.hora_salida_real and ctx.hora_salida_programada:
        limite_salida_max = (datetime.combine(base, ctx.hora_salida_programada) + tol).time()
        if ctx.hora_salida_real > limite_salida_max:
            motivos.append('Salida posterior')

        limite_salida_min = (datetime.combine(base, ctx.hora_salida_programada) - tol).time()
        if ctx.hora_salida_real < limite_salida_min:
            motivos.append('Salida anticipada')

    return motivos


def evaluar_marcacion(ctx: ContextoMarcacion) -> ResultadoEvaluacion:
    """Evalúa la marcación de un día en una sola pasada.

    Orden de prioridad (ver docs/motor_reglas_marcacion.md):
      1. Justificado (resultado_previo 'J') manda sobre todo.
      2. Día libre (estado 'D').
      3. Sin marcas -> Feriado (si aplica) o Falta.
      4. Con marcas en feriado -> Asistió + etiqueta FERIADO (sin tardanza).
      5. Con marcas, día normal -> Asistió; Sin horario / Tardanza /
         Fuera de horario / Normal.
    """
    resultado_previo = _normalizar_resultado(ctx.resultado_previo)

    # 1. La justificación la aprueba RRHH o llega del ERP: no la pisa una marca.
    if resultado_previo == RESULTADO_JUSTIFICADO:
        return ResultadoEvaluacion(
            resultado=RESULTADO_JUSTIFICADO,
            etiqueta=EstadoMarca.JUSTIFICADO,
            etiquetas=(EstadoMarca.JUSTIFICADO,),
            horas_tardanza=0.0,
            minutos_tardanza=0,
            detalle='Justificación aprobada por RRHH o ERP',
        )

    # 2. Día libre programado: no se evalúa tardanza aunque haya marcas sueltas.
    if ctx.estado_jornada == ESTADO_DIA_LIBRE:
        resultado = RESULTADO_ASISTIO if ctx.tiene_marcas else resultado_previo or RESULTADO_FALTA
        return ResultadoEvaluacion(
            resultado=resultado,
            etiqueta=EstadoMarca.DIA_LIBRE,
            etiquetas=(EstadoMarca.DIA_LIBRE,),
            horas_tardanza=0.0,
            minutos_tardanza=0,
            detalle='Día programado como libre',
        )

    # 3. Sin marcas reales: feriado no penaliza; en día normal es Falta.
    if not ctx.tiene_marcas:
        if ctx.es_feriado:
            return ResultadoEvaluacion(
                resultado=resultado_previo or RESULTADO_FALTA,
                etiqueta=EstadoMarca.FERIADO,
                etiquetas=(EstadoMarca.FERIADO,),
                horas_tardanza=0.0,
                minutos_tardanza=0,
                detalle=_detalle_feriado(ctx, 'Día feriado sin marcación'),
            )
        return ResultadoEvaluacion(
            resultado=RESULTADO_FALTA,
            etiqueta=EstadoMarca.FALTA,
            etiquetas=(EstadoMarca.FALTA,),
            horas_tardanza=0.0,
            minutos_tardanza=0,
            detalle='Sin marcación registrada',
        )

    # Hay marcas reales -> el trabajador asistió.
    # 4. Trabajó en feriado: se etiqueta FERIADO y no se calcula tardanza.
    if ctx.es_feriado:
        return ResultadoEvaluacion(
            resultado=RESULTADO_ASISTIO,
            etiqueta=EstadoMarca.FERIADO,
            etiquetas=(EstadoMarca.FERIADO,),
            horas_tardanza=0.0,
            minutos_tardanza=0,
            detalle=_detalle_feriado(ctx, 'Asistencia en día feriado'),
        )

    # 5. Día normal con marcas.
    etiquetas: list[str] = []
    detalles: list[str] = []

    # Sin horario programado no se puede juzgar tardanza ni rango.
    if ctx.hora_entrada_programada is None:
        return ResultadoEvaluacion(
            resultado=RESULTADO_ASISTIO,
            etiqueta=EstadoMarca.SIN_HORARIO,
            etiquetas=(EstadoMarca.SIN_HORARIO,),
            horas_tardanza=0.0,
            minutos_tardanza=0,
            detalle='Sin horario de entrada programado',
        )

    minutos_tardanza = _minutos_tardanza(
        ctx.hora_entrada_real, ctx.hora_entrada_programada, ctx.minutos_tolerancia
    )
    if minutos_tardanza > 0:
        etiquetas.append(EstadoMarca.TARDANZA)
        detalles.append(
            f'Tardanza de {minutos_tardanza} min '
            f'(tolerancia: {ctx.minutos_tolerancia} min)'
        )

    motivos_fuera = _fuera_de_horario(ctx)
    if motivos_fuera:
        etiquetas.append(EstadoMarca.FUERA_DE_HORARIO)
        detalles.extend(motivos_fuera)

    if not etiquetas:
        etiquetas.append(EstadoMarca.NORMAL)
        detalles.append('Marca dentro de horario y tolerancia')

    return ResultadoEvaluacion(
        resultado=RESULTADO_ASISTIO,
        etiqueta=etiquetas[0],
        etiquetas=tuple(etiquetas),
        horas_tardanza=round(minutos_tardanza / 60, 2),
        minutos_tardanza=minutos_tardanza,
        detalle='; '.join(detalles),
    )
