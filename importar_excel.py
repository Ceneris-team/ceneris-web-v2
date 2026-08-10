# importar_excel.py

import pandas as pd
from datetime import datetime, time, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import pytz


# --- 1. CONFIGURACIÓN INICIAL ---
NOMBRE_ARCHIVO_EXCEL = 'reporte_asistencias.xlsx'
# Como todos los meses están en una sola hoja, podemos eliminar la variable de la hoja
SERVICE_ACCOUNT_KEY_PATH = 'secrets/firebase-service-account.json'
COLECCION_TRABAJADORES = 'trabajadores'
COLECCION_ASISTENCIAS = 'asistencias'
HORA_BASE_ENTRADA = time(8, 30, 0) # La hora base: 08:30:00
ANIO_DE_REGISTROS = 2025 # ¡IMPORTANTE! Asumimos el año 2024 para todos los registros.
ZONA_HORARIA_LOCAL = pytz.timezone('America/Lima') # <-- AÑADE ESTA LÍNEA
# Esto es crucial para manejar correctamente las fechas y horas en la zona horaria correcta.

# --- 2. CONEXIÓN A FIREBASE ---
try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Conexión con Firebase exitosa.")
except Exception as e:
    print(f"❌ Error al conectar con Firebase: {e}")
    exit()

# --- 3. LECTURA Y LIMPIEZA DEL EXCEL ---
try:
    df = pd.read_excel(NOMBRE_ARCHIVO_EXCEL)
    print(f"📄 Excel leído. Se encontraron {len(df)} filas en total.")

    # Convertimos todas las columnas de días a texto para manejar 'F' y otros valores
    columnas_dias = [col for col in df.columns if isinstance(col, int) and 1 <= col <= 31]
    for col in columnas_dias:
        df[col] = df[col].astype(str)

except Exception as e:
    print(f"❌ ERROR al leer o procesar el Excel: {e}")
    exit()

# --- 4. TRANSFORMACIÓN Y SUBIDA A FIRESTORE ---
print("🚀 Iniciando procesamiento y subida de datos. Esto puede tardar...")

registros_subidos = 0
trabajadores_procesados = set()

# Iteramos sobre cada fila del Excel
for index, row in df.iterrows():
    try:
        # Extraemos los datos del trabajador de la fila actual
        dni = str(row['Doc.Id.'])
        nombre = str(row['Nombre']).strip()
        mes = int(row['MES'])
        estatus = str(row['ESTATUS']).strip().upper()

        if not dni or not nombre or dni == 'nan':
            print(f"⚠️ Fila {index + 2} saltada: DNI o Nombre vacíos.")
            continue

        # Creamos o actualizamos el perfil del trabajador (solo la primera vez que lo vemos)
        if dni not in trabajadores_procesados:
            trabajador_ref = db.collection(COLECCION_TRABAJADORES).document(dni)
            trabajador_ref.set({
                'nombre': nombre,
                'dni': dni,
                'activo': True if estatus == 'ACTIVO' else False,
            }, merge=True)
            trabajadores_procesados.add(dni)

        # Iteramos sobre las columnas de días (del 1 al 31) para esta fila
        for dia in columnas_dias:
            valor_celda = row[dia]
            
            # Ignoramos faltas y celdas vacías/inválidas
            if pd.isna(valor_celda) or str(valor_celda).upper() in ['F', 'NAN', 'NAT', '00:00']:
                continue

            try:
                # La hora de tardanza puede ser un objeto de tiempo o un string
                hora_tardanza = valor_celda
                
                if isinstance(hora_tardanza, str):
                    partes = hora_tardanza.split(':')
                    h, m = int(partes[0]), int(partes[1])
                    s = int(partes[2]) if len(partes) > 2 else 0
                    tardanza_delta = timedelta(hours=h, minutes=m, seconds=s)
                elif isinstance(hora_tardanza, time):
                    tardanza_delta = timedelta(hours=hora_tardanza.hour, minutes=hora_tardanza.minute, seconds=hora_tardanza.second)
                else:
                    # Si no es string ni time, lo ignoramos
                    continue

                # Calculamos la hora real de marcación
                fecha_base = datetime(ANIO_DE_REGISTROS, mes, dia, HORA_BASE_ENTRADA.hour, HORA_BASE_ENTRADA.minute)
                timestamp_real_naive = fecha_base + tardanza_delta
                
                # ¡LA CORRECCIÓN CLAVE! Hacemos que la fecha sea "consciente" de su zona horaria
                timestamp_real = ZONA_HORARIA_LOCAL.localize(timestamp_real_naive)
                # Preparamos el documento para subir
                asistencia_data = {
                    'userDni': dni,
                    'userName': nombre,
                    'timestamp': timestamp_real,
                    'status': 'success_imported',
                    'locationName': 'Oficina (Histórico)',
                }
                
                # Subimos la asistencia
                db.collection(COLECCION_ASISTENCIAS).add(asistencia_data)
                registros_subidos += 1
                
            except (ValueError, TypeError) as e_cell:
                # Error específico al procesar una celda de hora
                print(f"⚠️ Fila {index + 2}, Día {dia}: Saltada. Valor de hora no válido ('{valor_celda}'). Error: {e_cell}")
                continue

    except Exception as e_row:
        print(f"❌ ERROR grave procesando la fila {index + 2} (DNI: {dni}): {e_row}")

    if (index + 1) % 50 == 0: # Imprime el progreso cada 50 filas del Excel
        print(f"⏳ Progreso: {index + 1} / {len(df)} filas del Excel procesadas...")

print(f"\n✅ ¡Proceso finalizado!")
print(f"   - Se procesaron {len(trabajadores_procesados)} trabajadores únicos.")
print(f"   - Se subieron {registros_subidos} registros de asistencia a Firestore.")