import psycopg2
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURACIÓN ---

# 1. Inicializa Firebase Admin SDK
# Reemplaza 'ruta/a/tu/firebase-credentials.json' con el nombre de tu archivo de credenciales.
cred = credentials.Certificate('asistenciaceneris-app-firebase-adminsdk-fbsvc-85dac4d12d.json')
firebase_admin.initialize_app(cred)
db_firestore = firestore.client()

# 2. Configura la conexión a PostgreSQL
# Pega aquí la URL de conexión externa que obtuviste de Render.
POSTGRES_URL = "postgresql://ceneris_db_2h87_user:4qXCDyJhefDfecdnYr0ZyzA8ik5X2yrl@dpg-d3l9kel6ubrc73968mk0-a.virginia-postgres.render.com/ceneris_db_2h87"

# 3. Define el nombre de la colección en Firestore donde se guardarán los trabajadores.
COLECCION_TRABAJADORES = "trabajadores" # Puedes cambiar este nombre si lo deseas

# --- FUNCIÓN PRINCIPAL DE MIGRACIÓN ---

def migrar_trabajadores():
    """
    Se conecta a PostgreSQL, lee los datos de los trabajadores,
    y los sube a la colección de Firestore con la estructura deseada.
    """
    conn = None
    try:
        # Conexión a la base de datos PostgreSQL
        print("Conectando a la base de datos PostgreSQL en Render...")
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()

        # ### CAMBIO 1: Consulta SQL actualizada ###
        # Seleccionamos las columnas que existen en tu tabla: dni, nombres, apellido_paterno, apellido_materno.
        # Reemplaza 'recursoshumanos_trabajador' si tu tabla se llama diferente.
        sql_query = "SELECT dni, nombres, apellido_paterno, apellido_materno FROM recursoshumanos_trabajador"
        cur.execute(sql_query)
        
        trabajadores_postgres = cur.fetchall()
        print(f"Se encontraron {len(trabajadores_postgres)} trabajadores para migrar.")

        # Iterar sobre cada trabajador y subirlo a Firestore
        for trabajador in trabajadores_postgres:
            # ### CAMBIO 2: Asignación de variables según la nueva consulta ###
            # El orden debe coincidir con el de tu consulta SQL.
            dni, nombres, apellido_paterno, apellido_materno = trabajador

            # Si el DNI es nulo, no podemos usarlo como ID, así que saltamos este registro.
            if dni is None:
                print(f"  -> ADVERTENCIA: Se omitió un registro por tener DNI nulo (Nombre: {nombres}).")
                continue
            
            # ### CAMBIO 3: Combinar los campos para formar el nombre completo ###
            # Aseguramos que los campos no sean nulos antes de unirlos.
            paterno = apellido_paterno if apellido_paterno else ""
            materno = apellido_materno if apellido_materno else ""
            nombre_solo = nombres if nombres else ""

            # Formateamos el nombre como "APELLIDO PATERNO APELLIDO MATERNO, Nombres"
            nombre_completo = f"{paterno} {materno}, {nombre_solo}".strip()

            # Crea el diccionario con la estructura de datos para Firestore
            data_para_firestore = {
                'activo': True,
                'cargo': "",  # Dejado en blanco, ya que no está en la tabla
                'deviceIDVinculado': None,
                'email': "",  # Dejado en blanco, ya que no está en la tabla
                'nombre': nombre_completo,
                'sexo': "",   # Dejado en blanco, ya que no está en la tabla
                'ubicacionesPermitidas': []
            }

            # ### CAMBIO 4: Usar el DNI como identificador del documento ###
            # Convertimos el DNI a string para usarlo como ID.
            doc_ref = db_firestore.collection(COLECCION_TRABAJADORES).document(str(dni))
            doc_ref.set(data_para_firestore)
            print(f"  -> Trabajador '{nombre_completo}' (DNI: {dni}) migrado exitosamente.")

        print("\n¡Migración completada con éxito!")

        # Cierra la comunicación con la base de datos
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error durante la migración: {error}")

    finally:
        if conn is not None:
            conn.close()
            print("Conexión a PostgreSQL cerrada.")

# --- Ejecutar el script ---
if __name__ == "__main__":
    migrar_trabajadores()