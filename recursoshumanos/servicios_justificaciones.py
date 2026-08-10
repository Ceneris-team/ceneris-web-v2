# servicios_justificaciones.py
import datetime

from django.utils import timezone

from recursoshumanos.models import Justificacion, TareoDiario, Trabajador
from recursoshumanos.servicios_asistencias import (
    EMP_TABLES,
    _cursor_biometrico,
    _tablas_existentes,
)

# Asegúrate de poner aquí todas las tablas de ausencias de tu ERP
AUSEN_TABLES = ['p01ausen', 'p02ausen', 'p03ausen', 'p04ausen', 'p21ausen', 'p22ausen']

def sincronizar_justificaciones_erp(con_detalle=False):
    justificaciones_creadas = 0
    hoy = timezone.localdate()
    
    # Buscamos ausencias que toquen el último mes o el futuro cercano
    fecha_inicio = hoy - timezone.timedelta(days=30)
    fecha_fin = hoy + timezone.timedelta(days=30)
    
    mapa_empleados_por_sucursal = {}
    filas_ausencias = []

    with _cursor_biometrico() as cursor:
        tablas_emp = _tablas_existentes(cursor, EMP_TABLES)
        tablas_ausen = _tablas_existentes(cursor, AUSEN_TABLES)

        # 1. Mapeamos empleados por sucursal (igual que en las marcaciones)
        for tabla in tablas_emp:
            prefijo = tabla[:3].lower()
            if prefijo not in mapa_empleados_por_sucursal:
                mapa_empleados_por_sucursal[prefijo] = {}

            cursor.execute(f"SELECT codigo, idtrab FROM {tabla} WHERE idtrab IS NOT NULL AND idtrab <> ''")
            for codigo_reloj, dni in cursor.fetchall():
                if codigo_reloj and dni:
                    mapa_empleados_por_sucursal[prefijo][str(codigo_reloj).strip()] = str(dni).strip()

        # 2. Extraemos las ausencias usando TUS COLUMNAS EXACTAS
        for tabla in tablas_ausen:
            prefijo = tabla[:3].lower()
            cursor.execute(
                f"""
                SELECT codigo, desde, hasta, tip_aus, comments 
                FROM {tabla}
                WHERE hasta >= %s AND desde <= %s
                """,
                [fecha_inicio, fecha_fin]
            )
            for fila in cursor.fetchall():
                filas_ausencias.append({
                    'codigo': fila[0],
                    'desde': fila[1],
                    'hasta': fila[2],
                    'tipo': fila[3],
                    'comentario': fila[4],
                    'prefijo': prefijo
                })

    # 3. Procesamos y guardamos en la base local
    for ausencia in filas_ausencias:
        codigo_reloj = str(ausencia['codigo'] or '').strip()
        prefijo_origen = ausencia['prefijo']
        
        # Obtenemos fechas asegurándonos que sean objetos date
        desde = ausencia['desde'].date() if isinstance(ausencia['desde'], datetime.datetime) else ausencia['desde']
        hasta = ausencia['hasta'].date() if isinstance(ausencia['hasta'], datetime.datetime) else ausencia['hasta']
        
        # Mapeo de motivos del ERP ('M'=Médico, 'V'=Vacaciones) a tu modelo
        tipo_erp = str(ausencia['tipo'] or '').strip().upper()
        if tipo_erp == 'M':
            motivo_local = 'SALUD'
        elif tipo_erp == 'V':
            motivo_local = 'PERSONAL' # O puedes agregar 'VACACIONES' a las tuplas de tu modelo
        else:
            motivo_local = 'OTRO'
            
        comentario = str(ausencia['comentario'] or f'Ausencia ERP tipo {tipo_erp}').strip()

        # Buscamos al trabajador
        dni_empleado = mapa_empleados_por_sucursal.get(prefijo_origen, {}).get(codigo_reloj)
        if not dni_empleado or not desde or not hasta:
            continue

        try:
            trabajador = Trabajador.objects.get(dni=dni_empleado)
            
            # MAGIA AQUÍ: Iteramos día por día dentro del rango (desde -> hasta)
            delta = hasta - desde
            for i in range(delta.days + 1):
                dia_actual = desde + datetime.timedelta(days=i)
                
                # A. Aseguramos que exista el TareoDiario para ese día
                tareo, _ = TareoDiario.objects.get_or_create(
                    trabajador=trabajador,
                    fecha=dia_actual,
                    defaults={'estado': 'O', 'resultado': 'F'} # Nace como Falta por defecto
                )

                # B. Creamos la justificación APROBADA
                justificacion, creada = Justificacion.objects.get_or_create(
                    tareo=tareo,
                    defaults={
                        'motivo': motivo_local,
                        'descripcion': f'Importado desde ERP: {comentario}',
                        'estado_solicitud': 'APROBADO'
                    }
                )
                
                if creada:
                    justificaciones_creadas += 1

        except Trabajador.DoesNotExist:
            pass

    return justificaciones_creadas