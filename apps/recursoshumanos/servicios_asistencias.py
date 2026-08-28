# servicios_reloj.py
import datetime
from contextlib import contextmanager
from collections import defaultdict

import pymysql
from django.conf import settings
from django.db import connections
from django.utils import timezone
from .models import Trabajador, Asistencia, TareoDiario, Justificacion # <-- Agregamos Justificacion

# ==========================================================
# CONFIGURACIÓN DE TABLAS EXTERNAS (Ajusta los nombres reales aquí)
# ==========================================================
EMP_TABLES = ['p01empall', 'p02empall', 'p03empall', 'p04empall','p05empall','p21empall', 'p22empall']
MARCAS_TABLES = ['p01marcas', 'p02marcas', 'p03marcas', 'p04marcas', 'p05marcas', 'p21marcas', 'p22marcas']
JUST_TABLES = ['p01ausen', 'p02ausen', 'p03ausen', 'p04ausen', 'p05ausen', 'p21ausen', 'p22ausen'] # <-- TABLAS DE JUSTIFICACIONES


@contextmanager
def _cursor_biometrico():
    """Conexión a la BD externa con depuración extrema para ver dónde falla."""
    import time
    
    print("\n" + "="*50)
    print("  [DEBUG BIOMÉTRICO] INICIANDO PROCESO ")
    print("="*50)
    
    db_conf = settings.DATABASES.get('db_biometrico', {})
    host_reloj = db_conf.get('HOST') or 'localhost'
    puerto_reloj = int(db_conf.get('PORT') or 3306)
    usuario_reloj = db_conf.get('USER') or 'No definido'
    
    print(f"[DEBUG] 1. Leyendo variables de entorno (settings.py)...")
    print(f"    -> HOST a atacar : {host_reloj}")
    print(f"    -> PUERTO        : {puerto_reloj}")
    print(f"    -> USUARIO MySQL : {usuario_reloj}")
    
    print("\n[DEBUG] 2. Tocando la puerta del router/firewall...")
    print("    (Si el log se queda congelado aquí, el puerto sigue cerrado por TI)")
    
    inicio_tiempo = time.time()
    
    try:
        # Usamos PyMySQL directo con un Timeout de 10 segundos
        conn = pymysql.connect(
            host=host_reloj,
            user=usuario_reloj,
            password=db_conf.get('PASSWORD') or '',
            database=db_conf.get('NAME') or '',
            port=puerto_reloj,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor,
            connect_timeout=10 # ¡Clave! Si en 10 segs no contestan, aborta.
        )
        tiempo_total = round(time.time() - inicio_tiempo, 2)
        
        print(f"\n[DEBUG] 3. ¡ÉXITO! ")
        print(f"    -> El router dejó pasar a Render.")
        print(f"    -> MySQL aceptó al usuario '{usuario_reloj}'.")
        print(f"    -> Tiempo de conexión: {tiempo_total} segundos.")
        
        try:
            with conn.cursor() as cursor:
                yield cursor
        finally:
            conn.close()
            print("\n[DEBUG] 4. Conexión cerrada correctamente tras extraer datos.")
            print("="*50 + "\n")

    except pymysql.err.OperationalError as exc:
        tiempo_total = round(time.time() - inicio_tiempo, 2)
        print(f"\n[DEBUG] [ERROR] FALLO DE OPERACIÓN tras {tiempo_total} segundos.")
        
        mensaje_error = str(exc).lower()
        if 'timed out' in mensaje_error:
            print("    -> DIAGNÓSTICO: TIEMPO AGOTADO (Timeout).")
            print("    -> CAUSA: La IP de Render llegó al router, pero este no la redirigió al servidor local o el Firewall la bloqueó.")
        elif 'access denied' in mensaje_error:
            print("    -> DIAGNÓSTICO: ACCESO DENEGADO.")
            print("    -> CAUSA: El router dejó pasar a Render, pero la contraseña de MySQL es incorrecta o el usuario no tiene permisos '%' remotos.")
        else:
            print(f"    -> DIAGNÓSTICO DESCONOCIDO: {exc}")
        print("="*50 + "\n")
        raise
        
    except Exception as exc:
        print(f"\n[DEBUG] [ERROR] ERROR INESPERADO: {exc}")
        print("="*50 + "\n")
        raise


def _tablas_existentes(cursor, tablas_esperadas):
    cursor.execute('SHOW TABLES')
    disponibles = {fila[0].lower(): fila[0] for fila in cursor.fetchall()}
    return [disponibles[t.lower()] for t in tablas_esperadas if t.lower() in disponibles]


def _parse_hora(valor_hora):
    if isinstance(valor_hora, datetime.time):
        return valor_hora
    texto = ''.join(ch for ch in str(valor_hora or '') if ch.isdigit())
    if not texto:
        return None
    texto = texto.zfill(4)[-4:]
    hh, mm = int(texto[:2]), int(texto[2:4])
    if hh > 23 or mm > 59:
        return None
    return datetime.time(hh, mm)


def _combinar_fecha_hora(fecha_valor, hora_valor):
    if isinstance(fecha_valor, datetime.datetime):
        fecha = fecha_valor.date()
    else:
        fecha = fecha_valor
    hora = _parse_hora(hora_valor)
    if fecha is None or hora is None:
        return None
    dt = datetime.datetime.combine(fecha, hora)
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def sincronizar_biometrico_fragmentado(con_detalle=False, desde=None, hasta=None):
    nuevos_registros = 0
    hoy = timezone.localdate()
    fecha_inicio = datetime.date.fromisoformat(desde) if desde else hoy.replace(day=1)
    fecha_fin = datetime.date.fromisoformat(hasta) if hasta else hoy
    
    mapa_empleados_por_sucursal = {}
    filas_marcaciones_crudas = []
    justificaciones_crudas = []
    
    detalle = {
        'rango_fechas': {'inicio': fecha_inicio, 'fin': fecha_fin},
        'empleados_tablas': {},
        'marcas_tablas': {},
        'marcas_total_leidas': 0,
        'justificaciones': {
            'tablas': {},
            'total_leidas': 0,
            'evaluadas': 0,
            'sin_mapeo_dni': 0,
            'trabajador_no_encontrado': 0,
            'tareos_creados': 0,
            'tareos_marcados_j': 0,
            'registros_locales_creados': 0,
            'registros_locales_actualizados': 0,
            'errores_inesperados': 0,
        },
        'marcas_evaluadas': 0,
        'marcas_validas_para_busqueda': 0,
        'descartes': {
            'sin_mapeo_dni': 0,
            'fecha_hora_invalida': 0,
            'trabajador_no_encontrado': 0,
            'trabajador_sin_usuario': 0,
            'asistencia_duplicada': 0,
            'errores_inesperados': 0,
        },
        'tareo': {
            'creados': 0,
            'actualizados': 0,
            'justificados': 0,
        },
        'muestras': {
            'codigos_sin_dni': [],
            'dnis_sin_trabajador': [],
            'trabajadores_sin_usuario': [],
            'errores': [],
            'just_codigos_sin_dni': [],
            'just_dnis_sin_trabajador': [],
            'just_errores': [],
        },
    }

    with _cursor_biometrico() as cursor:
        tablas_emp = _tablas_existentes(cursor, EMP_TABLES)
        tablas_marcas = _tablas_existentes(cursor, MARCAS_TABLES)
        tablas_just = _tablas_existentes(cursor, JUST_TABLES)

        # 1. MAPEAR EMPLEADOS POR SUCURSAL
        for tabla in tablas_emp:
            prefijo = tabla[:3].lower()
            if prefijo not in mapa_empleados_por_sucursal:
                mapa_empleados_por_sucursal[prefijo] = {}

            cursor.execute(f"SELECT codigo, idtrab FROM {tabla} WHERE idtrab IS NOT NULL AND idtrab <> ''")
            filas_emp = cursor.fetchall()
            mapeados = 0
            for codigo_reloj, dni in filas_emp:
                codigo_reloj, dni = str(codigo_reloj or '').strip(), str(dni or '').strip()
                if codigo_reloj and dni:
                    mapa_empleados_por_sucursal[prefijo][codigo_reloj] = dni
                    mapeados += 1
            detalle['empleados_tablas'][tabla] = {'filas_leidas': len(filas_emp), 'filas_mapeadas': mapeados}

        # 2. EXTRAER MARCACIONES
        for tabla in tablas_marcas:
            prefijo = tabla[:3].lower()
            cursor.execute(
                f"SELECT codigo, fecha, hora, punmar FROM {tabla} WHERE fecha >= %s AND fecha <= %s ORDER BY fecha ASC, hora ASC",
                [fecha_inicio, fecha_fin],
            )
            filas_tabla = cursor.fetchall()
            detalle['marcas_tablas'][tabla] = {'filas_leidas': len(filas_tabla)}
            detalle['marcas_total_leidas'] += len(filas_tabla)
            for fila in filas_tabla:
                filas_marcaciones_crudas.append((fila[0], fila[1], fila[2], fila[3], prefijo))

        # 3. EXTRAER JUSTIFICACIONES (mismo criterio que servicios_justificaciones)
        for tabla in tablas_just:
            prefijo = tabla[:3].lower()
            try:
                cursor.execute(
                    f"""
                    SELECT codigo, desde, hasta, tip_aus, comments
                    FROM {tabla}
                    WHERE hasta >= %s AND desde <= %s
                    """,
                    [fecha_inicio, fecha_fin]
                )
                filas_just_tabla = cursor.fetchall()
                detalle['justificaciones']['tablas'][tabla] = {
                    'filas_leidas': len(filas_just_tabla),
                    'error': None,
                }
                detalle['justificaciones']['total_leidas'] += len(filas_just_tabla)
                for fila in filas_just_tabla:
                    justificaciones_crudas.append({
                        'codigo': fila[0],
                        'desde': fila[1],
                        'hasta': fila[2],
                        'tipo': fila[3],
                        'comentario': fila[4],
                        'prefijo': prefijo,
                    })
            except Exception as exc:
                detalle['justificaciones']['tablas'][tabla] = {
                    'filas_leidas': 0,
                    'error': str(exc),
                }

    # ==========================================================
    # --- FILTRADO DE MARCACIONES (Entradas y Salidas reales)
    # ==========================================================
    marcas_por_dia = defaultdict(list)
    for fila in filas_marcaciones_crudas:
        codigo_reloj, fecha, prefijo_origen = fila[0], fila[1], fila[4]
        fecha_sola = fecha.date() if isinstance(fecha, datetime.datetime) else fecha
        clave = (prefijo_origen, codigo_reloj, fecha_sola)
        marcas_por_dia[clave].append(fila)

    filas_marcaciones = []
    for clave, marcas_del_dia in marcas_por_dia.items():
        # Ordenamos por la hora ya interpretada (no por texto): como cadena,
        # "930" > "1030" y la primera/última marca del día saldría invertida.
        marcas_del_dia.sort(key=lambda x: _parse_hora(x[2]) or datetime.time.min)
        if len(marcas_del_dia) > 0:
            primera_marca = list(marcas_del_dia[0])
            primera_marca[3] = 'ENTRADA'
            filas_marcaciones.append(primera_marca)
        if len(marcas_del_dia) > 1:
            ultima_marca = list(marcas_del_dia[-1])
            ultima_marca[3] = 'SALIDA'
            filas_marcaciones.append(ultima_marca)

    # ==========================================================
    # --- GUARDAR MARCACIONES Y TAREOS
    # ==========================================================
    for fila_marc in filas_marcaciones:
        detalle['marcas_evaluadas'] += 1
        codigo_reloj = str(fila_marc[0] or '').strip()
        fecha_hora = _combinar_fecha_hora(fila_marc[1], fila_marc[2])
        tipo_bd = str(fila_marc[3] or '').strip()
        prefijo_origen = fila_marc[4]
        
        tipo_marcacion = 'Entrada' if tipo_bd in {'0', '1', '01', 'E', 'ENTRADA'} else 'Salida'
        dni_empleado = mapa_empleados_por_sucursal.get(prefijo_origen, {}).get(codigo_reloj)

        # =====================================================
        # [ALERTA] INICIO DEL CHIVATO (RASTREADOR DE DNI)
        # =====================================================
        if dni_empleado == '75150962':
            print("\n" + "!"*40)
            print(f"[ALERTA] RASTREANDO A: 75150962")
            print(f" -> Fecha y Hora que llega del reloj: {fecha_hora}")
            print(f" -> Tipo: {tipo_marcacion}")
            print(f" -> Código Reloj: {codigo_reloj} (Sucursal {prefijo_origen})")
            print("!"*40 + "\n")
        # =====================================================
        # [ALERTA] FIN DEL CHIVATO
        # =====================================================
        
        if not dni_empleado:
            detalle['descartes']['sin_mapeo_dni'] += 1
            if len(detalle['muestras']['codigos_sin_dni']) < 8:
                detalle['muestras']['codigos_sin_dni'].append(codigo_reloj)
            continue

        if fecha_hora is None:
            detalle['descartes']['fecha_hora_invalida'] += 1
            continue

        detalle['marcas_validas_para_busqueda'] += 1

        try:
            trabajador = Trabajador.objects.get(dni=dni_empleado)
            if not trabajador.user_id:
                detalle['descartes']['trabajador_sin_usuario'] += 1
                if len(detalle['muestras']['trabajadores_sin_usuario']) < 8:
                    detalle['muestras']['trabajadores_sin_usuario'].append(dni_empleado)
                continue
            
            asistencia, creada = Asistencia.objects.get_or_create(
                usuario=trabajador.user,
                timestamp=fecha_hora,
                defaults={
                    'tipo_marcacion': tipo_marcacion, 
                    'nombre_ubicacion': f'Biométrico {prefijo_origen.upper()}',
                    'origen': 'BIOMETRICO'  # Esta es la línea clave agregada
                }
            )

            if creada:
                nuevos_registros += 1
                fecha_sola = fecha_hora.date()
                hora_sola = fecha_hora.time()
                
                tareo, tareo_creado = TareoDiario.objects.get_or_create(
                    trabajador=trabajador,
                    fecha=fecha_sola,
                    defaults={'estado': 'O', 'resultado': 'F'}
                )
                if tareo_creado:
                    detalle['tareo']['creados'] += 1
                else:
                    detalle['tareo']['actualizados'] += 1

                if tipo_marcacion == 'Entrada':
                    # La entrada real debe ser siempre la MAS TEMPRANA vista
                    # hasta ahora, sin importar el origen (app o biometrico).
                    # Antes esto se sobrescribia sin comparar: si la app ya
                    # habia registrado una entrada temprana real (ej. 05:38)
                    # y despues llegaba la marca del biometrico (ej. 08:30,
                    # que ademas nunca trae segundos), esta ultima pisaba a
                    # la correcta con una hora mas tardia y menos precisa.
                    if tareo.hora_entrada_real is None or hora_sola < tareo.hora_entrada_real:
                        tareo.hora_entrada_real = hora_sola

                        # Recalculamos la tardanza solo cuando la entrada real
                        # cambia de verdad, usando el horario real asignado
                        # (Campo=9:00, Personalizado=variable, Sabado=9:00) y,
                        # si no hay horario asignado, el mismo valor por
                        # defecto que usa el resto del sistema (8:30 entre
                        # semana, 9:00 los sabados).
                        if tareo.hora_entrada:
                            hora_ref = tareo.hora_entrada
                        elif fecha_sola.weekday() == 5:
                            hora_ref = datetime.time(9, 0)
                        else:
                            hora_ref = datetime.time(8, 30)

                        if hora_sola > hora_ref:
                            segundos_tarde = (
                                (hora_sola.hour * 3600 + hora_sola.minute * 60 + hora_sola.second)
                                - (hora_ref.hour * 3600 + hora_ref.minute * 60 + hora_ref.second)
                            )
                            tareo.horas_tardanza = round(segundos_tarde / 3600, 2)
                        else:
                            tareo.horas_tardanza = 0.0
                    tareo.resultado = 'A'
                else:
                    # La salida real debe ser siempre la MAS TARDIA vista
                    # hasta ahora, por la misma razon (no dejar que una marca
                    # posterior del biometrico pise una salida real mas
                    # tardia ya registrada por la app, o viceversa).
                    if tareo.hora_salida_real is None or hora_sola > tareo.hora_salida_real:
                        tareo.hora_salida_real = hora_sola
                tareo.save()
            else:
                detalle['descartes']['asistencia_duplicada'] += 1

        except Trabajador.DoesNotExist:
            detalle['descartes']['trabajador_no_encontrado'] += 1
            if len(detalle['muestras']['dnis_sin_trabajador']) < 8:
                detalle['muestras']['dnis_sin_trabajador'].append(dni_empleado)
        except Exception as exc:
            detalle['descartes']['errores_inesperados'] += 1
            if len(detalle['muestras']['errores']) < 8:
                detalle['muestras']['errores'].append(str(exc))

    # ==========================================================
    # --- PROCESAR Y APLICAR JUSTIFICACIONES
    # ==========================================================
    for fila_just in justificaciones_crudas:
        detalle['justificaciones']['evaluadas'] += 1
        codigo_reloj = str(fila_just['codigo'] or '').strip()
        prefijo_origen = fila_just['prefijo']

        desde = fila_just['desde'].date() if isinstance(fila_just['desde'], datetime.datetime) else fila_just['desde']
        hasta = fila_just['hasta'].date() if isinstance(fila_just['hasta'], datetime.datetime) else fila_just['hasta']

        tipo_erp = str(fila_just['tipo'] or '').strip().upper()
        if tipo_erp == 'M':
            motivo_local = 'SALUD'
        elif tipo_erp == 'V':
            motivo_local = 'PERSONAL'
        else:
            motivo_local = 'OTRO'

        comentario = str(fila_just['comentario'] or f'Ausencia ERP tipo {tipo_erp}').strip()
        dni_empleado = mapa_empleados_por_sucursal.get(prefijo_origen, {}).get(codigo_reloj)
        
        if not dni_empleado or not desde or not hasta:
            detalle['justificaciones']['sin_mapeo_dni'] += 1
            if len(detalle['muestras']['just_codigos_sin_dni']) < 8:
                detalle['muestras']['just_codigos_sin_dni'].append(codigo_reloj)
            continue

        try:
            trabajador = Trabajador.objects.get(dni=dni_empleado)

            # Aplicamos solo los dias de ausencia que caen dentro del rango consultado.
            inicio_aplicable = max(desde, fecha_inicio)
            fin_aplicable = min(hasta, fecha_fin)
            if inicio_aplicable > fin_aplicable:
                continue

            delta = fin_aplicable - inicio_aplicable
            for i in range(delta.days + 1):
                dia_actual = inicio_aplicable + datetime.timedelta(days=i)

                tareo, tareo_creado = TareoDiario.objects.get_or_create(
                    trabajador=trabajador,
                    fecha=dia_actual,
                    defaults={'estado': 'O', 'resultado': 'F'}
                )
                if tareo_creado:
                    detalle['justificaciones']['tareos_creados'] += 1

                if tareo.resultado != 'J':
                    tareo.resultado = 'J'
                    tareo.save()
                    detalle['tareo']['justificados'] += 1
                    detalle['justificaciones']['tareos_marcados_j'] += 1

                _, just_creada = Justificacion.objects.update_or_create(
                    tareo=tareo,
                    defaults={
                        'motivo': motivo_local,
                        'descripcion': f'Importado desde ERP: {comentario}',
                        'estado_solicitud': 'APROBADO'
                    }
                )
                if just_creada:
                    detalle['justificaciones']['registros_locales_creados'] += 1
                else:
                    detalle['justificaciones']['registros_locales_actualizados'] += 1
        except Trabajador.DoesNotExist:
            detalle['justificaciones']['trabajador_no_encontrado'] += 1
            if len(detalle['muestras']['just_dnis_sin_trabajador']) < 8:
                detalle['muestras']['just_dnis_sin_trabajador'].append(dni_empleado)
            continue
        except Exception as exc:
            detalle['justificaciones']['errores_inesperados'] += 1
            if len(detalle['muestras']['just_errores']) < 8:
                detalle['muestras']['just_errores'].append(str(exc))
            continue

    # ==========================================================
    total_mapeados = sum(len(sucursal) for sucursal in mapa_empleados_por_sucursal.values())
    if con_detalle:
        detalle['empleados_mapeados_total'] = total_mapeados
        detalle['marcaciones_procesadas_total'] = len(filas_marcaciones)
        detalle['marcaciones_nuevas'] = nuevos_registros
        return nuevos_registros, detalle

    return nuevos_registros