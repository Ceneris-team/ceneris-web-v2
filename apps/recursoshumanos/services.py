from datetime import datetime, date, time, timedelta
from django.db import transaction
from django.utils import timezone # <--- ESTO ES VITAL
from .models import (
    TareoDiario,
    Asistencia,
    SolicitudHorasExtra,
    ConfiguracionTolerancia,
    ToleranciaAuditoria,
)


TOLERANCIA_TARDANZA_MINUTOS = 15


# ==============================================================================
# HU-06 (CAV-15): CONFIGURACIÓN DE TOLERANCIA DE HORARIO
# ==============================================================================

def listar_tolerancias(sede_id=None):
    """Lista las configuraciones de tolerancia, opcionalmente filtradas por sede."""
    qs = ConfiguracionTolerancia.objects.select_related('sede').all()
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return qs


@transaction.atomic
def actualizar_tolerancia(configuracion_id, minutos_nuevos, usuario):
    """
    Actualiza los minutos de tolerancia de una configuración existente y deja
    registro en ToleranciaAuditoria en la misma transacción, para que nunca
    quede un cambio de minutos sin su historial correspondiente.
    """
    configuracion = ConfiguracionTolerancia.objects.select_for_update().get(pk=configuracion_id)
    minutos_anteriores = configuracion.minutos_tolerancia

    if minutos_anteriores != minutos_nuevos:
        configuracion.minutos_tolerancia = minutos_nuevos
        configuracion.save(update_fields=['minutos_tolerancia', 'actualizado_en'])

        ToleranciaAuditoria.objects.create(
            configuracion=configuracion,
            sede_nombre=configuracion.sede.nombre,
            tipo_horario=configuracion.tipo_horario,
            minutos_anteriores=minutos_anteriores,
            minutos_nuevos=minutos_nuevos,
            usuario=usuario,
        )

    return configuracion


@transaction.atomic
def crear_o_actualizar_tolerancia(sede_id, tipo_horario, minutos_tolerancia, usuario):
    """
    Crea la configuración de tolerancia para (sede, tipo_horario) si no existe,
    o actualiza sus minutos (con auditoría) si ya existía.
    """
    configuracion, creada = ConfiguracionTolerancia.objects.get_or_create(
        sede_id=sede_id,
        tipo_horario=tipo_horario,
        defaults={'minutos_tolerancia': minutos_tolerancia},
    )

    if creada:
        ToleranciaAuditoria.objects.create(
            configuracion=configuracion,
            sede_nombre=configuracion.sede.nombre,
            tipo_horario=configuracion.tipo_horario,
            minutos_anteriores=0,
            minutos_nuevos=minutos_tolerancia,
            usuario=usuario,
        )
        return configuracion

    return actualizar_tolerancia(configuracion.pk, minutos_tolerancia, usuario)


def obtener_minutos_tolerancia(sede, tipo_horario, default=TOLERANCIA_TARDANZA_MINUTOS):
    """
    Consulta la tolerancia vigente directamente en BD (sin caché ni valores en
    memoria), de forma que un cambio guardado desde la pantalla administrativa
    (CAV-72) se refleje de inmediato en el cálculo de asistencia, sin
    necesidad de reiniciar el servidor.
    """
    if not sede or not tipo_horario:
        return default

    minutos = ConfiguracionTolerancia.objects.filter(
        sede=sede, tipo_horario=tipo_horario, activo=True
    ).values_list('minutos_tolerancia', flat=True).first()

    return minutos if minutos is not None else default

def _a_time(valor):
    """Normaliza un TimeField que a veces llega como datetime/date a `time`.

    Protección histórica contra mezclas datetime vs time; una `date` pura no
    tiene hora útil, así que se descarta (None)."""
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, date):
        return None
    return valor


def recalcular_asistencia_diaria(tareo: TareoDiario):
    """
    Algoritmo robusto para calcular asistencia, tolerancias y pagos.
    CORREGIDO: Convierte UTC a Hora Local antes de guardar.

    CAV-166: la clasificación de la marca (resultado, tardanza y etiqueta) se
    delega al motor de reglas puro (`motor_reglas.evaluar_marcacion`), que
    evalúa feriado + horario + tolerancia en una sola pasada. Aquí solo se
    recolectan los datos (una vez) y se persisten; la contabilidad de horas de
    pago (pares/almuerzo/horas extra) se mantiene local.
    """
    # Import local: administracion.services.feriados hace import diferido de
    # este mismo app, así evitamos cualquier ciclo al cargar las apps.
    from administracion.services.feriados import obtener_feriado
    from .motor_reglas import ContextoMarcacion, evaluar_marcacion

    # 1. OBTENER MARCAS DEL DÍA
    # Se acota por RANGO de instante en vez de `timestamp__date=`: bajo USE_TZ
    # ese lookup aplica una conversion de zona horaria sobre la columna, que un
    # indice btree no puede aprovechar, asi que cada recalculo escanea la tabla
    # entera de asistencias. Al volver de faena esta funcion corre una vez por
    # cada dia sincronizado, de modo que el escaneo se multiplica por cientos.
    # El rango es equivalente (ambos delimitan el dia en America/Lima) pero si
    # usa el indice (usuario, timestamp) declarado en el modelo.
    inicio_dia = timezone.make_aware(datetime.combine(tareo.fecha, time.min))
    fin_dia = timezone.make_aware(
        datetime.combine(tareo.fecha + timedelta(days=1), time.min)
    )
    marcas = Asistencia.objects.filter(
        usuario=tareo.trabajador.user,
        timestamp__gte=inicio_dia,
        timestamp__lt=fin_dia,
    ).order_by('timestamp')

    if not marcas.exists():
        return

    # 2. PRIMERA ENTRADA Y ÚLTIMA SALIDA (EN HORA LOCAL)
    # Filtramos por tipo de marcación. Antes se tomaba la marca más temprana
    # del día fuera del tipo que fuera como "entrada" (y la más tardía como
    # "salida"), asi que una Salida marcada por error temprano terminaba
    # registrada como hora de entrada.
    primera_entrada = marcas.filter(tipo_marcacion='Entrada').first()
    ultima_salida = marcas.filter(tipo_marcacion='Salida').last()

    tareo.hora_entrada_real = (
        timezone.localtime(primera_entrada.timestamp).time() if primera_entrada else None
    )
    tareo.hora_salida_real = (
        timezone.localtime(ultima_salida.timestamp).time() if ultima_salida else None
    )

    # 3. CÁLCULO DE MINUTOS TRABAJADOS (PARES)
    # Para restar duraciones NO importa la zona horaria (la diferencia es la misma)
    lista = list(marcas)
    minutos_raw = 0
    pares = 0
    i = 0
    while i < len(lista) - 1:
        if lista[i].tipo_marcacion == 'Entrada' and lista[i+1].tipo_marcacion == 'Salida':
            diff = (lista[i+1].timestamp - lista[i].timestamp).total_seconds() / 60
            minutos_raw += diff
            pares += 1
            i += 2
        else:
            i += 1

    # 4. REGLA DEL ALMUERZO
    tareo.descuento_almuerzo_aplicado = False
    if pares == 1 and minutos_raw > 300:
        minutos_raw = max(0, minutos_raw - 60)
        tareo.descuento_almuerzo_aplicado = True

    # 5. CLASIFICACIÓN POR EL MOTOR DE REGLAS (resultado + tardanza + etiqueta)
    # La tolerancia se consulta en vivo (ConfiguracionTolerancia) según la Sede
    # del trabajador y el horario/turno del día (CAV-154), y el feriado se
    # resuelve contra la tabla oficial (CAV-11), todo en esta única pasada.
    h_programada = _a_time(tareo.hora_entrada)

    # El feriado se resuelve según el scope del trabajador (CAV-13): un feriado
    # regional/de empresa solo aplica a su sede/empresa; el nacional a todos.
    trabajador = tareo.trabajador
    feriado = obtener_feriado(tareo.fecha, sede=trabajador.sede, empresa=trabajador.empresa)

    contexto = ContextoMarcacion(
        fecha=tareo.fecha,
        estado_jornada=tareo.estado,
        resultado_previo=tareo.resultado,
        hora_entrada_programada=h_programada,
        hora_salida_programada=_a_time(tareo.hora_salida),
        hora_entrada_real=tareo.hora_entrada_real,
        hora_salida_real=tareo.hora_salida_real,
        minutos_tolerancia=obtener_minutos_tolerancia(trabajador.sede, tareo.estado),
        es_feriado=feriado is not None,
        nombre_feriado=feriado.nombre if feriado else None,
        ambito_feriado=feriado.get_ambito_display() if feriado else None,
        tiene_marcas=True,
    )
    evaluacion = evaluar_marcacion(contexto)

    tareo.resultado = evaluacion.resultado
    tareo.horas_tardanza = evaluacion.horas_tardanza
    tareo.etiqueta_estado = evaluacion.etiqueta
    tareo.detalle_marca = evaluacion.detalle

    # 6. VALIDAR HORAS EXTRA Y TOPES
    horas_reales = round(minutos_raw / 60, 2)
    horas_objetivo = 0.0

    try:
        if tareo.estado == 'J' and tareo.jornada_horas:
            horas_objetivo = float(tareo.jornada_horas)
        elif h_programada and tareo.hora_salida:
            h_salida_prog = tareo.hora_salida
            
            # Validación tipos salida
            if isinstance(h_salida_prog, datetime): h_salida_prog = h_salida_prog.time()
            elif isinstance(h_salida_prog, date): h_salida_prog = None
            
            if h_salida_prog:
                dt_e = datetime.combine(date.today(), h_programada)
                dt_s = datetime.combine(date.today(), h_salida_prog)
                horas_objetivo = max(0, ((dt_s - dt_e).total_seconds() / 3600) - 1)
    except Exception as e:
         print(f"⚠️ Error calculando objetivo: {e}")

    # Sumar Extras
    solicitud = SolicitudHorasExtra.objects.filter(
        trabajador=tareo.trabajador, fecha_horas_extra=tareo.fecha, estado='APROBADO'
    ).first()
    extras = float(solicitud.cantidad_horas) if solicitud else 0.0

    # Guardar
    tareo.horas_trabajadas_validas = min(horas_reales, horas_objetivo + extras)
    tareo.save()