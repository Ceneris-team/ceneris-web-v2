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

def recalcular_asistencia_diaria(tareo: TareoDiario):
    """
    Algoritmo robusto para calcular asistencia, tolerancias y pagos.
    CORREGIDO: Convierte UTC a Hora Local antes de guardar.
    """
    # 1. OBTENER MARCAS DEL DÍA
    marcas = Asistencia.objects.filter(
        usuario=tareo.trabajador.user, 
        timestamp__date=tareo.fecha
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

    # Un día justificado (J) no debe volverse "Asistió" por una marcación
    # suelta: la justificación la aprueba RRHH o llega del ERP, y manda sobre
    # cualquier marca (ej. alguien de licencia que igual marcó ese día).
    if (tareo.resultado or '').upper() != 'J':
        tareo.resultado = 'A'

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

    # 5. CÁLCULO DE TARDANZA (EN HORAS DECIMALES)
    tareo.horas_tardanza = 0.00
    
    h_programada = tareo.hora_entrada
    
    # Validación de tipos (Protección contra errores datetime vs time)
    if isinstance(h_programada, datetime):
        h_programada = h_programada.time()
    elif isinstance(h_programada, date):
        h_programada = None

    if tareo.estado != 'J' and h_programada is not None:
        try:
            # Usamos la hora real ya convertida (Local)
            dt_prog = datetime.combine(date.today(), h_programada)
            dt_real = datetime.combine(date.today(), tareo.hora_entrada_real)

            diff_min = (dt_real - dt_prog).total_seconds() / 60

            # CAV-154: la tolerancia se consulta en vivo (ConfiguracionTolerancia)
            # según la Sede del trabajador y el horario/turno del día, en vez de
            # usar una constante fija, para que los cambios de HU-06 apliquen
            # de inmediato.
            minutos_tolerancia = obtener_minutos_tolerancia(tareo.trabajador.sede, tareo.estado)
            diff_min -= minutos_tolerancia

            if diff_min > 0:
                # Convertimos minutos a horas decimales
                tareo.horas_tardanza = round(diff_min / 60, 2)

        except Exception as e:
            print(f"⚠️ Error calculando tardanza: {e}")

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