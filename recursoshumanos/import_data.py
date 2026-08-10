# recursoshumanos/import_data.py

import os
import sys
import django
import pathlib
import pandas as pd
from datetime import datetime

# Asegurar que la raíz del proyecto está en sys.path para poder importar el paquete del proyecto
# cuando se ejecuta este script directamente (python recursoshumanos/import_data.py)
PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configura el entorno de Django
# Usar el módulo de settings correcto (el proyecto principal es `admin_panel`)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')
django.setup()

from recursoshumanos.models import Empresa, Proyecto, CentroCosto, Cargo, Trabajador

def run_import(excel_file_path):
    print(f"Iniciando importación desde: {excel_file_path}")

    try:
        # Usamos engine='openpyxl' para una mejor compatibilidad con .xlsx
        # skiprows=5 para saltar las primeras 5 filas y que la fila 6 sea la de cabecera
        df = pd.read_excel(excel_file_path, skiprows=5, engine='openpyxl')
        
        # Leemos el nombre de la empresa de la celda B1 (fila 1, columna B, 0-indexado)
        # Necesitamos leer el archivo de nuevo para obtener la celda B1
        df_full = pd.read_excel(excel_file_path, header=None, engine='openpyxl')
        empresa_nombre = df_full.iloc[0, 1] # Fila 0 (1ra fila), Columna 1 (B)
        
        if pd.isna(empresa_nombre) or not str(empresa_nombre).strip():
            print("Error: No se encontró el nombre de la empresa en la celda B1. Usando 'Empresa Por Defecto'.")
            empresa_nombre = "Empresa Por Defecto"
        else:
            empresa_nombre = str(empresa_nombre).strip()

        # Limpiar nombres de columnas: eliminar espacios, caracteres especiales, convertir a minúsculas
        # Esto es importante porque pandas puede cargar los nombres con espacios o caracteres no deseados
        df.columns = df.columns.str.strip().str.upper().str.replace('[^A-Z0-9_]', '', regex=True)

        # Mapeo de columnas del Excel (ya limpiadas a MAYÚSCULAS) a campos del modelo Django
        column_mapping = {
            'APELLIDOP': 'apellido_paterno',
            'APELLIDOM': 'apellido_materno',
            'NOMBRES': 'nombres',
            'IDTRAB': 'dni',
            'CARGO': 'cargo_codigo_excel', # Usaremos para Cargo.codigo
            'CARGO_1': 'cargo_nombre_excel', # Usaremos para Cargo.nombre
            'F_INGR': 'fecha_ingreso',
            'FICO': 'fecha_inicio_contrato', # Tu modelo tiene 'fecha_inicio_contrato'
            'FFCO': 'fecha_fin_contrato',
            'C_COSTO': 'centro_costo_codigo_excel', # Usaremos para CentroCosto.codigo
            'C_COSTO_1': 'centro_costo_nombre_excel', # Usaremos para CentroCosto.nombre
            'FECNAC': 'fecha_nacimiento',
            'SEXO': 'sexo_excel', # 'M' o 'F'
            'PROYECTO': 'proyecto_codigo_excel', # Usaremos para Proyecto.codigo
            'PROYECTO_1': 'proyecto_nombre_excel', # Usaremos para Proyecto.nombre
            'CORREO': 'email',
        }
        df = df.rename(columns=column_mapping)

        # Eliminar columnas que no vamos a usar
        columns_to_drop = [
            'APENOM', 'DUCO', 'PLMOTCES', 'PLMOTCES_1', 'SEXO_1'
        ]
        # Asegurarse de que las columnas existan antes de intentar eliminarlas
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

        # Convertir columnas de fecha a objetos date de Python o None
        # IMPORTANTE: pandas usa NaT para valores faltantes; Django espera None o objetos date/datetime.
        # Si dejamos NaT, Django tratará de acceder a utcoffset() y lanzará "NaTType does not support utcoffset".
        date_columns = ['fecha_ingreso', 'fecha_inicio_contrato', 'fecha_fin_contrato', 'fecha_nacimiento']
        for col in date_columns:
            if col in df.columns:
                # Primero parsear a datetime (NaT en errores)
                parsed = pd.to_datetime(df[col], errors='coerce')
                # Luego convertir a objetos date de Python o None para que Django los acepte
                df[col] = parsed.apply(lambda x: x.date() if pd.notna(x) else None)

        # Convertir 'sexo_excel' a 'M'/'F' para el modelo
        if 'sexo_excel' in df.columns:
            df['sexo'] = df['sexo_excel'].astype(str).str.upper().apply(lambda x: 'M' if 'M' in x else ('F' if 'F' in x else None))
        else:
            df['sexo'] = None # Si no hay columna de sexo, dejar en None

        # --- Obtener o crear la Empresa (una sola para todos) ---
        empresa_obj, created = Empresa.objects.get_or_create(
            nombre=empresa_nombre,
            defaults={'ruc': 'PENDIENTE', 'direccion': 'PENDIENTE'} # Añade defaults si es la primera creación
        )
        if created:
            print(f"Empresa '{empresa_nombre}' creada.")
        else:
            print(f"Empresa '{empresa_nombre}' encontrada.")

        # Iterar sobre cada fila del DataFrame (datos de trabajadores)
        for index, row in df.iterrows():
            # El DNI es crucial y primary_key, así que lo validamos primero
            dni = str(row.get('dni', '')).strip()
            if not dni or len(dni) != 8 or not dni.isdigit():
                print(f"Saltando fila {index + 7}: DNI inválido o vacío '{row.get('dni')}'. (Fila original de Excel: {index + 2})")
                continue # Saltar esta fila y pasar a la siguiente

            try:
                # --- Obtener o crear Cargo ---
                cargo_nombre = str(row.get('cargo_nombre_excel', '')).strip()
                cargo_codigo = str(row.get('cargo_codigo_excel', '')).strip()

                cargo_obj = None
                if cargo_nombre or cargo_codigo:
                    # Preferimos buscar por nombre si está disponible, o por código si el nombre no está claro.
                    # Si ambos están, priorizamos nombre y actualizamos código, o viceversa si solo hay código.
                    if cargo_nombre:
                        cargo_obj, created = Cargo.objects.get_or_create(
                            nombre=cargo_nombre,
                            defaults={'codigo': cargo_codigo if cargo_codigo else None}
                        )
                        if created:
                            print(f"  Cargo '{cargo_nombre}' creado.")
                        elif cargo_codigo and cargo_obj.codigo != cargo_codigo:
                            # Si ya existía pero el código es diferente, actualizamos
                            cargo_obj.codigo = cargo_codigo
                            cargo_obj.save()
                            # print(f"  Cargo '{cargo_nombre}' actualizado con código '{cargo_codigo}'.")
                    elif cargo_codigo: # Si no hay nombre pero sí código, lo usamos como nombre
                        cargo_obj, created = Cargo.objects.get_or_create(
                            codigo=cargo_codigo,
                            defaults={'nombre': cargo_codigo} # Usar el código como nombre por defecto
                        )
                        if created:
                            print(f"  Cargo '{cargo_codigo}' creado (usando código como nombre).")

                # --- Obtener o crear CentroCosto ---
                centro_costo_nombre = str(row.get('centro_costo_nombre_excel', '')).strip()
                centro_costo_codigo = str(row.get('centro_costo_codigo_excel', '')).strip()
                
                centro_costo_obj = None
                if centro_costo_nombre or centro_costo_codigo:
                    if centro_costo_nombre:
                        centro_costo_obj, created = CentroCosto.objects.get_or_create(
                            nombre=centro_costo_nombre,
                            defaults={'codigo': centro_costo_codigo if centro_costo_codigo else None}
                        )
                        if created:
                            print(f"  Centro de Costo '{centro_costo_nombre}' creado.")
                        elif centro_costo_codigo and centro_costo_obj.codigo != centro_costo_codigo:
                            centro_costo_obj.codigo = centro_costo_codigo
                            centro_costo_obj.save()
                    elif centro_costo_codigo:
                        centro_costo_obj, created = CentroCosto.objects.get_or_create(
                            codigo=centro_costo_codigo,
                            defaults={'nombre': centro_costo_codigo}
                        )
                        if created:
                            print(f"  Centro de Costo '{centro_costo_codigo}' creado (usando código como nombre).")

                # --- Obtener o crear Proyecto ---
                proyecto_nombre = str(row.get('proyecto_nombre_excel', '')).strip()
                proyecto_codigo = str(row.get('proyecto_codigo_excel', '')).strip()
                
                proyecto_obj = None
                if proyecto_nombre or proyecto_codigo:
                    # Siempre necesitamos una empresa para un proyecto.
                    # Si ya tienes una lógica para múltiples empresas, este punto necesitará ajuste.
                    if proyecto_nombre:
                        proyecto_obj, created = Proyecto.objects.get_or_create(
                            nombre=proyecto_nombre,
                            empresa=empresa_obj, # Asocia al proyecto con la empresa definida en B1
                            defaults={'codigo': proyecto_codigo if proyecto_codigo else None}
                        )
                        if created:
                            print(f"  Proyecto '{proyecto_nombre}' creado.")
                        elif proyecto_codigo and proyecto_obj.codigo != proyecto_codigo:
                            proyecto_obj.codigo = proyecto_codigo
                            proyecto_obj.save()
                    elif proyecto_codigo:
                        proyecto_obj, created = Proyecto.objects.get_or_create(
                            codigo=proyecto_codigo,
                            empresa=empresa_obj,
                            defaults={'nombre': proyecto_codigo}
                        )
                        if created:
                            print(f"  Proyecto '{proyecto_codigo}' creado (usando código como nombre).")

                # --- Crear o actualizar Trabajador ---
                trabajador_data = {
                    'apellido_paterno': str(row.get('apellido_paterno', '')).strip(),
                    'apellido_materno': str(row.get('apellido_materno', '')).strip(),
                    'nombres': str(row.get('nombres', '')).strip(),
                    'empresa': empresa_obj,
                    'cargo': cargo_obj,
                    'proyecto_actual': proyecto_obj,
                    'centro_costo': centro_costo_obj,
                    'fecha_ingreso': row.get('fecha_ingreso'),
                    'fecha_inicio_contrato': row.get('fecha_inicio_contrato'),
                    'fecha_fin_contrato': row.get('fecha_fin_contrato'),
                    'fecha_nacimiento': row.get('fecha_nacimiento'),
                    'sexo': row.get('sexo'),
                    'email': str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                    'telefono': '', # Tu Excel no tiene columna de teléfono. Se deja vacío.
                }
                
                # Update_or_create utiliza el 'dni' (primary_key) para buscar.
                trabajador, created = Trabajador.objects.update_or_create(
                    dni=dni,
                    defaults=trabajador_data
                )

                if created:
                    print(f"Trabajador {trabajador.nombres} {trabajador.apellido_paterno} (DNI: {dni}) creado.")
                else:
                    print(f"Trabajador {trabajador.nombres} {trabajador.apellido_paterno} (DNI: {dni}) actualizado.")

            except Exception as e:
                print(f"Error procesando fila {index + 7} (DNI: {dni}): {e}") # +7 para reflejar fila real de Excel
                import traceback
                traceback.print_exc()

    except FileNotFoundError:
        print(f"Error: El archivo '{excel_file_path}' no fue encontrado.")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la importación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Ruta al archivo Excel (calculada respecto al directorio del script)
    # Esto asegura que el script encuentre el archivo aunque ejecutes el comando desde otra carpeta
    excel_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Lista_de_Trabajadores.xlsx')
    
    run_import(excel_file)