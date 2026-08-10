import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from cenerisapp.models import (
    Empresa, Empleado, Dispositivo, AreaTrabajo, 
    ObservacionDispositivo, Modificacion, Mantenimiento, Sensor, Inventario, Alarma, InformeCalibracion, Parte, PuntoExacto
)
from datetime import datetime, date
import json

def buscar_o_crear_empleado(nombre, stdout):
    if not nombre or pd.isna(nombre):
        return None
    try:
        # Búsqueda insensible a mayúsculas/minúsculas
        empleado = Empleado.objects.get(nomEmpleado__iexact=nombre)
        return empleado
    except Empleado.DoesNotExist:
        try:
            # Si no existe, lo creamos con valores por defecto
            nuevo_empleado = Empleado.objects.create(
                nomEmpleado=nombre,
                puesto='Por Definir', # Valor por defecto
            )
            stdout.write(stdout.style.SUCCESS(f"      -> Creado nuevo empleado '{nombre}' porque no existía."))
            return nuevo_empleado
        except Exception as e:
            stdout.write(stdout.style.WARNING(f"      -> Advertencia: No se pudo crear al empleado '{nombre}'. Error: {e}"))
            return None
    except Empleado.MultipleObjectsReturned:
        stdout.write(stdout.style.WARNING(f"      -> Advertencia: Múltiples empleados encontrados para '{nombre}'. Se usará el primero."))
        return Empleado.objects.filter(nomEmpleado__iexact=nombre).first()

    
class Command(BaseCommand):
    help = 'Importa y sincroniza datos desde un archivo Excel con múltiples hojas.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='La ruta completa al archivo Excel.')
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Borra TODOS los datos de las tablas relacionadas antes de importar.',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        do_clean = options['clean']

        if do_clean:
            self.stdout.write(self.style.WARNING('--- MODO LIMPIEZA ACTIVADO ---'))
            self.stdout.write('Borrando datos existentes. El orden es importante para respetar las relaciones.')

            # ¡ORDEN DE BORRADO IMPORTANTE! De "hijos" a "padres".
            self.stdout.write("Borrando datos transaccionales...")
            #Alarma.objects.all().delete()
            #InformeCalibracion.objects.all().delete()
            #Modificacion.objects.all().delete()
            #Mantenimiento.objects.all().delete()
            #ObservacionDispositivo.objects.all().delete()
            
            self.stdout.write("Borrando componentes y partes...")
            #Sensor.objects.all().delete() # Borrar sensores borra componentes padre

            self.stdout.write("Borrando datos maestros principales...")
            #Dispositivo.objects.all().delete()
            #Inventario.objects.all().delete()
            #Empleado.objects.all().delete()
            #AreaTrabajo.objects.all().delete()
            #PuntoExacto.objects.all().delete()
            #Empresa.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('¡Datos anteriores borrados!'))

        try:
            xls = pd.ExcelFile(file_path)
            self.stdout.write(f"Leyendo archivo: {file_path}")
            
            df_empresas = pd.read_excel(xls, 'Empresas', dtype=str).fillna('')
            df_empleados = pd.read_excel(xls, 'Empleados', dtype=str).fillna('')
            df_dispositivos = pd.read_excel(xls, 'Dispositivos', dtype=str).fillna('')
            df_observaciones = pd.read_excel(xls, 'ObservacionDispositivo', dtype=str).fillna('')
            df_modificaciones = pd.read_excel(xls, 'HistorialModificaciones', dtype=str).fillna('')
            df_mantenimientos = pd.read_excel(xls, 'Mantenimiento', dtype=str).fillna('')
            df_inventario = pd.read_excel(xls, 'inventario')
            df_inventario['cantIngreso'] = pd.to_numeric(df_inventario['cantIngreso'], errors='coerce')

            # Rellenamos los NaN en 'cantIngreso' con 0 (o puedes elegir otro valor por defecto)
            df_inventario['cantIngreso'] = df_inventario['cantIngreso'].fillna(0).astype(int)

            # Rellenamos el resto de las columnas (que sí son texto) con strings vacíos
            df_inventario = df_inventario.fillna('')
            df_dispositivos_fijos = pd.read_excel(xls, 'DispositivosFijos', dtype=str).fillna('')
            df_sensores_fijos = pd.read_excel(xls, 'SensorFijo', dtype=str).fillna('')
            df_alarmas = pd.read_excel(xls, 'Alarmas', dtype=str).fillna('')
            df_informes = pd.read_excel(xls, 'InformeCalibracion', dtype=str).fillna('')
            df_partes = pd.read_excel(xls, 'Partes', dtype=str).fillna('')
            df_areas = pd.read_excel(xls, 'AreaTrabajo', dtype=str).fillna('')

        except Exception as e:
            raise CommandError(f"Error al leer el archivo Excel. Asegúrate de que todas las hojas existan y tengan los nombres correctos. Detalle: {e}")

        #self.import_empresas(df_empresas)
        # Importamos áreas desde la hoja de dispositivos, no necesita hoja propia.
        #self.import_empleados(df_empleados)
        self.import_inventario(df_inventario)
        #self.import_dispositivos(df_dispositivos) # Portátiles
        #self.import_dispositivos(df_dispositivos_fijos) # Fijos
        #self.import_sensores_fijos(df_sensores_fijos)
        #self.import_alarmas(df_alarmas)
        #self.import_informes_calibracion(df_informes)
        #self.import_observaciones(df_observaciones)
        #self.import_modificaciones(df_modificaciones)
        #self.import_mantenimientos(df_mantenimientos)
        self.import_partes(df_partes)
        self.import_areas_y_puntos(df_areas)

        self.stdout.write(self.style.SUCCESS('¡Proceso de importación finalizado con éxito!'))

    def import_empresas(self, df):
        self.stdout.write("\n--- Importando Empresas ---")
        for index, row in df.iterrows():
            try:
                empresa, created = Empresa.objects.update_or_create(
                    ruc=row['ruc'],  # Usamos el RUC como identificador único para evitar duplicados
                    defaults={
                        'abreviacion': row['abreviacion'],
                        'nombreE': row['nombreE'],
                        'direccion': row['direccion'],
                        'departamento': row['departamento'],
                        'telefono': row['telefono'],
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + Creada empresa: {empresa.nombreE}"))
                else:
                    self.stdout.write(f"  = Actualizada empresa: {empresa.nombreE}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error en la fila {index + 2} de Empresas: {e}"))

    def import_empleados(self, df):
        self.stdout.write("\n--- Importando Empleados ---")
        for index, row in df.iterrows():
            try:
                empresa = None
                if row['empresa_nombre']:
                    try:
                        # Buscamos la empresa por su nombre exacto
                        empresa = Empresa.objects.get(nombreE=row['empresa_nombre'])
                    except Empresa.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"  - Advertencia: Empresa '{row['empresa_nombre']}' no encontrada para el empleado '{row['nomEmpleado']}'. Se asignará nulo."))
                
                empleado, created = Empleado.objects.update_or_create(
                    dni=row['dni'], # Usamos el DNI como identificador único
                    defaults={
                        'nomEmpleado': row['nomEmpleado'],
                        'puesto': row['puesto'],
                        'empresa': empresa,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + Creado empleado: {empleado.nomEmpleado}"))
                else:
                    self.stdout.write(f"  = Actualizado empleado: {empleado.nomEmpleado}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error en la fila {index + 2} de Empleados: {e}"))

    def import_dispositivos(self, df):
        self.stdout.write("\n--- Importando Dispositivos ---")
        for index, row in df.iterrows():
            try:
                empresa = None
                if row['nombre_empresa']:
                    try:
                        empresa = Empresa.objects.get(nombreE=row['nombre_empresa'])
                    except Empresa.DoesNotExist:
                         self.stdout.write(self.style.WARNING(f"  - Advertencia: Empresa '{row['nombre_empresa']}' no encontrada para el dispositivo '{row['num_serie']}'. Se asignará nulo."))

                area_trabajo = None
                if row['nombre_areaTrabajo_fijo']:
                    try:
                        # Usamos get_or_create para crear áreas si no existen, una flexibilidad útil
                        area_trabajo, _ = AreaTrabajo.objects.get_or_create(nombreA=row['nombre_areaTrabajo_fijo'])
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  - Advertencia: No se pudo encontrar o crear el Área de Trabajo '{row['nombre_areaTrabajo_fijo']}'. Se asignará nulo. Detalle: {e}"))

                # Convertir fechas, manejando celdas vacías
                def parse_date(date_str):
                    if pd.isna(date_str) or not date_str:
                        return None
                    try:
                        # Intenta convertir de varios formatos comunes
                        return pd.to_datetime(date_str).date()
                    except (ValueError, TypeError):
                        return None
                
                fec_ingreso = parse_date(row['fecIngreso'])
                fec_venc_garantia = parse_date(row['fecVencimientoGarantia'])
                fec_irreparable = parse_date(row.get('fec_irreparable')) # .get() para columnas opcionales
                fec_inoperativo = parse_date(row.get('fec_inoperativo'))
                
                # Manejar booleano
                cardex_revisado = str(row.get('cardex_revisado', '')).strip().upper() in ['TRUE', 'VERDADERO', '1', 'SI', 'SÍ']

                dispositivo, created = Dispositivo.objects.update_or_create(
                    num_serie=row['num_serie'], # Usamos el N/S como identificador único
                    defaults={
                        'nomDisp': row['nomDisp'],
                        'id_empresa': empresa,
                        'id_areaTrabajo_fijo': area_trabajo,
                        'tipoDisp': row['tipoDisp'],
                        'tag': row['tag'],
                        'estadoD': row['estadoD'],
                        'marca': row['marca'],
                        'fabDisp': row['fabDisp'],
                        'fecIngreso': fec_ingreso,
                        'fecVencimientoGarantia': fec_venc_garantia,
                        'fecFabricacion': str(row['fecFabricacion']),
                        'alarmaPortatil': row.get('alarmaPortatil'),
                        'fec_irreparable': fec_irreparable,
                        'fec_inoperativo': fec_inoperativo,
                        'ns': row.get('ns'),
                        'codigo_equipo': row.get('codigo_equipo'),
                        'cardex_revisado': cardex_revisado,
                        'area_general': row.get('area_general'),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + Creado dispositivo: {dispositivo.nomDisp} ({dispositivo.num_serie})"))
                else:
                    self.stdout.write(f"  = Actualizado dispositivo: {dispositivo.nomDisp} ({dispositivo.num_serie})")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error en la fila {index + 2} de Dispositivos: {e}"))
            
    def import_observaciones(self, df):
        self.stdout.write("\n--- Importando Observaciones (Carga Limpia) ---")
        
        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'ObservacionDispositivo' vacía. Saltando."))
            return

        for index, row in df.iterrows():
            try:
                # Obtenemos los valores y los limpiamos de espacios
                dispositivo_serie = str(row.get('dispositivo_num_serie', '')).strip()
                comentario_texto = str(row.get('comentario', '')).strip()

                # Verificamos que los datos esenciales existan
                if not dispositivo_serie:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: 'dispositivo_num_serie' está vacío. Saltando observación."))
                    continue
                if not comentario_texto:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: 'comentario' está vacío. Saltando observación."))
                    continue

                # Buscamos el dispositivo al que pertenece la observación
                dispositivo = Dispositivo.objects.get(num_serie=dispositivo_serie)
                
                # Creamos el nuevo registro de observación
                # Como la tabla se limpió antes, .create() es seguro y rápido.
                ObservacionDispositivo.objects.create(
                    dispositivo=dispositivo,
                    comentario=comentario_texto
                    # El campo 'autor' se quedará nulo, como en el modelo.
                )
                self.stdout.write(self.style.SUCCESS(f"  + Añadida observación para el dispositivo '{dispositivo.num_serie}'"))

            except Dispositivo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Dispositivo con N/S '{dispositivo_serie}' no encontrado. No se pudo guardar la observación."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de Observaciones: {e}"))

    # Dentro de la clase Command en cenerisapp/management/commands/import_maestros.py

    def import_modificaciones(self, df):
        self.stdout.write("\n--- Importando Historial de Modificaciones (Carga Limpia) ---")
        
        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'HistorialModificaciones' vacía. Saltando."))
            return
            
        sensor_types = ['LEL', 'O2', 'DUAL', 'SO2', 'CO2', 'NH3', 'CL2', 'HCN', 'PID'] # Ajusta esta lista

        for index, row in df.iterrows():
            try:
                dispositivo_serie = str(row.get('dispositivo_num_serie', '')).strip()
                if not dispositivo_serie: continue
                
                dispositivo = Dispositivo.objects.get(num_serie=dispositivo_serie)
            except Dispositivo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Dispositivo con N/S '{dispositivo_serie}' no encontrado. Saltando fila."))
                continue
            except KeyError:
                continue

            for sensor_type in sensor_types:
                col_serie_actual = f'n_serie_actual_{sensor_type}'
                
                # Procesamos si la columna existe y la celda tiene un valor
                if col_serie_actual in row and pd.notna(row[col_serie_actual]) and row[col_serie_actual]:
                    self.stdout.write(f"  Procesando modificación de {sensor_type} para {dispositivo.num_serie}...")
                    
                    try:
                        # --- 1. Recolectar datos ---
                        serie_anterior = str(row.get(f'n_serie_anterior_{sensor_type}', '')).strip()
                        serie_actual = str(row[col_serie_actual]).strip()
                        fecha_instalacion_str = row.get(f'fec_inst_{sensor_type}')
                        nombre_responsable = str(row.get(f'responsable_dni_{sensor_type}', '')).strip()

                        if not fecha_instalacion_str or not nombre_responsable:
                            self.stdout.write(self.style.ERROR(f"    - Error: Faltan datos (fecha o responsable) para sensor {sensor_type}. Saltando."))
                            continue
                        
                        fecha_instalacion = pd.to_datetime(fecha_instalacion_str).date()

                        # --- 2. Buscar/Crear Empleado ---
                        responsable = buscar_o_crear_empleado(nombre_responsable, self.stdout)
                        if not responsable:
                            self.stdout.write(self.style.ERROR(f"    - Error: No se pudo gestionar al responsable '{nombre_responsable}'. Saltando."))
                            continue
                        
                        # --- 3. MANEJAR SENSOR SALIENTE ---
                        sensor_saliente = None
                        if serie_anterior:
                            # Busca o crea el sensor saliente para mantener la integridad del historial
                            sensor_saliente, created = Sensor.objects.get_or_create(
                                nSerieActual=serie_anterior,
                                defaults={ 'nomComp': f'Sensor {sensor_type}', 'tipGas': sensor_type }
                            )
                            sensor_saliente.estComp = 'Inoperativo por cambio'
                            sensor_saliente.dispositivo_instalado = None
                            sensor_saliente.save()
                            self.stdout.write(f"    - Sensor saliente '{serie_anterior}' {'creado y' if created else ''} actualizado a Inoperativo.")
                        
                        # --- 4. MANEJAR SENSOR ENTRANTE (MAESTRO) ---
                        sensor_entrante, created = Sensor.objects.get_or_create(
                            nSerieActual=serie_actual,
                            defaults={ 'nomComp': f'Sensor {sensor_type}', 'tipGas': sensor_type }
                        )

                        # Actualizamos los datos del sensor entrante
                        sensor_entrante.dispositivo_instalado = dispositivo
                        sensor_entrante.fecInst = fecha_instalacion
                        sensor_entrante.estComp = row.get(f'estatus_sensor_{sensor_type}', 'Operativo')
                        if row.get(f'fec_fab_{sensor_type}'):
                            sensor_entrante.fecFabComp = pd.to_datetime(row.get(f'fec_fab_{sensor_type}')).date()
                        if row.get(f'fec_venc_garantia_{sensor_type}'):
                            sensor_entrante.fecVencGarantia = pd.to_datetime(row.get(f'fec_venc_garantia_{sensor_type}')).date()
                        sensor_entrante.nro_guia_ingreso = row.get(f'n_guia_ingreso_{sensor_type}', '')
                        sensor_entrante.item_guia = row.get(f'item_guia_{sensor_type}', '')
                        sensor_entrante.save()
                        self.stdout.write(f"    - Sensor entrante '{serie_actual}' {'creado y' if created else ''} actualizado e instalado en {dispositivo.num_serie}.")

                        # --- 5. Crear el registro de Modificación ---
                        Modificacion.objects.create( # Usamos .create() porque la tabla se limpió
                            id_dispositivo=dispositivo,
                            sensor_saliente=sensor_saliente,
                            componente_entrante=sensor_entrante,
                            id_trabajador=responsable,
                            MotivoCambio=f"Reemplazo de sensor {sensor_type}",
                            fecInstalacionMod=fecha_instalacion,
                            tipoServicio='Reparacion',
                            descrTrabajo=f"Carga masiva: reemplazo de sensor {sensor_type}."
                        )
                        self.stdout.write(self.style.SUCCESS(f"    - Registro de Modificación para {sensor_type} guardado."))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  - Error Fila {index+2}, Sensor {sensor_type}: Error inesperado - {e}"))
    
    def import_mantenimientos(self, df):
        self.stdout.write("\n--- Importando Mantenimientos (Carga Limpia) ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'Mantenimiento' vacía. Saltando."))
            return

        for index, row in df.iterrows():
            try:
                # 1. Validar y obtener datos esenciales
                dispositivo_serie = str(row.get('dispositivo_num_serie', '')).strip()
                nombre_tecnico = str(row.get('tecnico_a_cargo_dni', '')).strip() # El campo es el nombre, no el DNI
                fecha_intervencion_str = row.get('fecha_intervencion')
                
                if not dispositivo_serie or not nombre_tecnico or not fecha_intervencion_str:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Faltan datos esenciales (dispositivo, técnico o fecha). Saltando."))
                    continue

                # 2. Buscar objetos relacionados
                dispositivo = Dispositivo.objects.get(num_serie=dispositivo_serie)
                tecnico = buscar_o_crear_empleado(nombre_tecnico, self.stdout)
                if not tecnico:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: No se pudo encontrar o crear al técnico '{nombre_tecnico}'. Saltando."))
                    continue

                # 3. Procesar datos complejos (fecha y JSON)
                fecha_intervencion = pd.to_datetime(fecha_intervencion_str) # pandas maneja la conversión a datetime
                
                checklist = {}
                checklist_str = row.get('checklist_partes', '')
                if checklist_str:
                    try:
                        checklist = json.loads(checklist_str)
                    except json.JSONDecodeError:
                        self.stdout.write(self.style.WARNING(f"  - Fila {index+2}: 'checklist_partes' no es un JSON válido. Se guardará como vacío."))
                
                # 4. Crear el registro de Mantenimiento
                mantenimiento = Mantenimiento.objects.create(
                    dispositivo=dispositivo,
                    tecnico_a_cargo=tecnico,
                    fecha_intervencion=fecha_intervencion,
                    estado_inicial_equipo=str(row.get('estado_inicial_equipo', '')),
                    estado_final_equipo=str(row.get('estado_final_equipo', '')),
                    checklist_partes=checklist,
                    componentes_mal_estado=str(row.get('componentes_mal_estado', '')),
                    componentes_estado_regular=str(row.get('componentes_estado_regular', '')),
                    cambios_realizados=str(row.get('cambios_realizados', '')),
                    observacion_msa=str(row.get('observacion_msa', ''))
                )
                self.stdout.write(self.style.SUCCESS(f"  + Creado mantenimiento #{mantenimiento.id_mantenimiento} para '{dispositivo.num_serie}'"))

            except Dispositivo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Dispositivo '{dispositivo_serie}' no encontrado. Saltando mantenimiento."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de Mantenimiento: {e}"))

    def import_inventario(self, df):
        self.stdout.write("\n--- Importando Lotes de Inventario (Carga Limpia) ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'Inventario' vacía. Saltando."))
            return

        for index, row in df.iterrows():
            try:
                # --- VALIDACIÓN INICIAL ---
                trabajador_dni = str(row.get('trabajador_dni', '')).strip()
                descrip_inv = str(row.get('descripInv', '')).strip()
                # Leemos como string y limpiamos
                cant_ingreso_str = str(row.get('cantIngreso', '')).strip() 

                # Usamos 'cant_ingreso_str' en la validación
                if not trabajador_dni or not descrip_inv or not cant_ingreso_str:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Faltan datos clave (DNI, descripción o cantidad). Saltando lote."))
                    continue

                # --- PROCESAMIENTO CON BLOQUES AISLADOS ---

                # Bloque 1: Convertir cantidad
                try:
                    # Usamos 'cant_ingreso_str' para la conversión
                    cantidad = int(float(cant_ingreso_str))
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"  - Error Fila {index + 2}: El valor en 'cantIngreso' ('{cant_ingreso_str}') no es un número válido. Saltando."))
                    continue

                # Bloque 2: Convertir fecha
                fecha_entrega = None
                fec_entrega_str = row.get('fecEntregaCeneris')
                if pd.notna(fec_entrega_str) and fec_entrega_str:
                    try:
                        fecha_entrega = pd.to_datetime(fec_entrega_str).date()
                    except (ValueError, TypeError):
                        self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: El formato de 'fecEntregaCeneris' ('{fec_entrega_str}') es inválido. Se guardará como nulo."))

                # Bloque 3: Buscar Empleado
                try:
                    trabajador = Empleado.objects.get(dni=trabajador_dni)
                except Empleado.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Empleado con DNI '{trabajador_dni}' no encontrado. Saltando."))
                    continue
                
                # Bloque 4: Crear el objeto Inventario
                inventario = Inventario.objects.create(
                    id_trabajador=trabajador,
                    ubiImv=str(row.get('ubiImv', '')),
                    cantIngreso=cantidad,
                    fecEntregaCeneris=fecha_entrega,
                    descripInv=descrip_inv,
                    comentInv=str(row.get('comentInv', '')),
                    tipInv=str(row.get('tipInv', '')),
                    estadInv=str(row.get('estadInv', ''))
                )
                self.stdout.write(self.style.SUCCESS(f"  + Creado lote de inventario #{inventario.id_inventario}: {inventario.descripInv}"))

            except Exception as e:
                # Captura cualquier otro error inesperado (como un NameError)
                self.stdout.write(self.style.ERROR(f"  - Error inesperado GENERAL en la fila {index + 2}: {e}"))
        
    def import_sensores_fijos(self, df):
        self.stdout.write("\n--- Actualizando/Creando Sensores de Fijos ---")
        
        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'SensorFijo' vacía. Saltando."))
            return
            
        meses_es = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        for index, row in df.iterrows():
            try:
                # 1. Validar y obtener datos esenciales
                dispositivo_serie = str(row.get('dispositivo_num_serie', '')).strip()
                sensor_n_serie = str(row.get('nSerieActual', '')).strip()
                
                if not dispositivo_serie or not sensor_n_serie:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Faltan datos esenciales (N/S de dispositivo o sensor). Saltando."))
                    continue

                # 2. Buscar el dispositivo padre
                dispositivo = Dispositivo.objects.get(num_serie=dispositivo_serie)
                
                # 3. Construir la fecha de vencimiento de garantía
                fec_venc_garantia = None
                mes_str = str(row.get('MES DE VENCIMIENTO', '')).lower().strip()
                ano_str = str(row.get('AÑO DE VENCIMIENTO', '')).strip()

                if mes_str in meses_es and ano_str.isdigit():
                    mes_num = meses_es[mes_str]
                    ano_num = int(ano_str)
                    fec_venc_garantia = date(ano_num, mes_num, 28)

                # 4. Usar update_or_create para crear o actualizar el sensor (dato maestro)
                sensor, created = Sensor.objects.update_or_create(
                    nSerieActual=sensor_n_serie,
                    defaults={
                        'nomComp': str(row.get('nomComp', '')),
                        'dispositivo_instalado': dispositivo,
                        'estComp': str(row.get('estComp', '')),
                        'tipGas': str(row.get('tipGas', '')),
                        'fecVencGarantia': fec_venc_garantia,
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + Creado sensor '{sensor.nSerieActual}' para {dispositivo.num_serie}"))
                else:
                    self.stdout.write(f"  = Actualizado sensor '{sensor.nSerieActual}' para {dispositivo.num_serie}")

            except Dispositivo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Dispositivo '{dispositivo_serie}' no encontrado. Saltando sensor."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de SensorFijo: {e}"))

    def import_alarmas(self, df):
        self.stdout.write("\n--- Importando Alarmas (Carga Limpia) ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'Alarmas' vacía. Saltando."))
            return

        for index, row in df.iterrows():
            try:
                # 1. Validar y obtener el N/S del sensor
                sensor_n_serie = str(row.get('sensor_num_serie', '')).strip()
                if not sensor_n_serie:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: La columna 'sensor_num_serie' está vacía. Saltando alarma."))
                    continue
                
                # 2. Buscar el sensor padre
                sensor = Sensor.objects.get(nSerieActual=sensor_n_serie)
                
                # 3. Crear el registro de Alarma (como la tabla se limpió, usamos .create())
                alarma = Alarma.objects.create(
                    sensor=sensor,
                    primera=str(row.get('primera', '')),
                    segunda=str(row.get('segunda', '')),
                    tercera=str(row.get('tercera', '')),
                    und=str(row.get('und', '')),
                    equipo=str(row.get('equipo', '')),
                    cilindro=str(row.get('cilindro', '')),
                )
                
                self.stdout.write(self.style.SUCCESS(f"  + Creada alarma #{alarma.id_alarma} para sensor '{sensor.nSerieActual}'"))

            except Sensor.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Sensor con N/S '{sensor_n_serie}' no encontrado. No se pudo crear la alarma."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de Alarmas: {e}"))
                
    def import_informes_calibracion(self, df):
        self.stdout.write("\n--- Sincronizando Informes de Calibración (Update or Create) ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'InformeCalibracion' vacía. Saltando."))
            return
            
        if 'fecha_informe' in df.columns:
            df['fecha_informe_dt'] = pd.to_datetime(df['fecha_informe'], errors='coerce')
        else:
            self.stdout.write(self.style.ERROR("  - Error Crítico: La columna 'fecha_informe' no existe."))
            return

        for index, row in df.iterrows():
            try:
                # 1. Validar y obtener datos esenciales
                sensor_n_serie = str(row.get('sensor_id', '')).strip()
                informe_texto = str(row.get('informe', '')).strip()

                if not sensor_n_serie:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: 'sensor_id' está vacío. Saltando."))
                    continue
                if not informe_texto:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: 'informe' está vacío. Saltando."))
                    continue

                # 2. Buscar objetos relacionados
                sensor = Sensor.objects.get(nSerieActual=sensor_n_serie)

                empresa = None
                empresa_nombre = str(row.get('empresa_realizadora', '')).strip()
                if empresa_nombre:
                    empresa, _ = Empresa.objects.get_or_create(nombreE=empresa_nombre)

                # 3. Procesar otros datos
                fecha_informe_db = row['fecha_informe_dt'].date() if pd.notna(row['fecha_informe_dt']) else None
                sensor_cambiado_bool = str(row.get('sensor_cambiado', '')).strip().upper() in ['TRUE', 'VERDADERO', 'SI', 'SÍ', '1']
                encontrado_cal_texto = str(row.get('encontrado_calibracion', ''))
                observacion_texto = str(row.get('observacion', ''))
                
                # --- ¡LÓGICA DE UPDATE_OR_CREATE! ---
                informe, created = InformeCalibracion.objects.update_or_create(
                    # Campos para BUSCAR el registro:
                    sensor=sensor,
                    informe=informe_texto,
                    
                    # Campos para ACTUALIZAR o CREAR:
                    defaults={
                        'encontrado_calibracion': encontrado_cal_texto,
                        'sensor_cambiado': sensor_cambiado_bool,
                        'fecha_informe': fecha_informe_db,
                        'empresa_realizadora': empresa,
                        'observacion': observacion_texto
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + Creado informe para sensor '{sensor.nSerieActual}' con informe '{informe_texto[:20]}...'"))
                else:
                    self.stdout.write(f"  = Actualizado informe para sensor '{sensor.nSerieActual}' con informe '{informe_texto[:20]}...'")

            except Sensor.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Sensor con N/S '{sensor_n_serie}' no encontrado."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2}: {e}"))

    def import_partes(self, df):
        self.stdout.write("\n--- Asignando Partes a Dispositivos por Modelo ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'Partes' vacía. Saltando."))
            return

        partes_creadas = 0
        partes_existentes = 0

        # Iteramos sobre cada fila de la hoja 'Partes' del Excel
        for index, row in df.iterrows():
            try:
                # 1. Obtenemos los datos de la fila
                nombre_dispositivo = str(row.get('dispositivo_nomDisp', '')).strip()
                nombre_parte = str(row.get('nomPart', '')).strip()
                estado_parte = str(row.get('estado', 'Operativo')).strip()

                if not nombre_dispositivo or not nombre_parte:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: Faltan datos (nombre de dispositivo o de parte). Saltando."))
                    continue
                
                # 2. Buscamos TODOS los dispositivos que coincidan con ese nombre/modelo
                dispositivos_a_asignar = Dispositivo.objects.filter(nomDisp__iexact=nombre_dispositivo)
                
                if not dispositivos_a_asignar.exists():
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: No se encontraron dispositivos con el nombre '{nombre_dispositivo}'."))
                    continue
                
                self.stdout.write(f"  -> Asignando '{nombre_parte}' a {dispositivos_a_asignar.count()} dispositivo(s) del modelo '{nombre_dispositivo}'...")

                # 3. Iteramos sobre cada dispositivo encontrado y le creamos la parte
                for dispositivo in dispositivos_a_asignar:
                    # Usamos get_or_create para manejar la restricción 'unique_together'
                    # y evitar errores si la parte ya existe.
                    parte, created = Parte.objects.get_or_create(
                        id_dispositivo=dispositivo,
                        nomPart=nombre_parte,
                        defaults={'estado': estado_parte} # 'estado' solo se usa si se crea el objeto
                    )
                    
                    if created:
                        partes_creadas += 1
                    else:
                        # Opcional: Si quieres actualizar el estado si la parte ya existe
                        # parte.estado = estado_parte
                        # parte.save()
                        partes_existentes += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de Partes: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"  + Proceso de asignación de partes finalizado. {partes_creadas} partes nuevas creadas. {partes_existentes} partes ya existían."))
    
    def import_areas_y_puntos(self, df):
        self.stdout.write("\n--- Sincronizando Áreas de Trabajo y Puntos Exactos ---")

        if df.empty:
            self.stdout.write(self.style.WARNING("  -> Hoja 'AreaTrabajo' vacía. Saltando."))
            return

        areas_creadas = 0
        puntos_creados = 0
        puntos_existentes = 0

        for index, row in df.iterrows():
            try:
                # 1. Obtenemos los datos de la fila
                nombre_area = str(row.get('nombreA', '')).strip()
                nombre_punto = str(row.get('nombre_punto', '')).strip()

                # El nombre del área es esencial para crear cualquier cosa
                if not nombre_area:
                    self.stdout.write(self.style.WARNING(f"  - Fila {index + 2}: 'nombreA' está vacío. Saltando fila completa."))
                    continue
                
                # 2. Creamos o encontramos el objeto AreaTrabajo.
                #    Usamos get_or_create que es perfecto para esto.
                area_trabajo, created_area = AreaTrabajo.objects.get_or_create(
                    nombreA=nombre_area
                )
                if created_area:
                    self.stdout.write(self.style.SUCCESS(f"  + Creada nueva Área: '{nombre_area}'"))
                    areas_creadas += 1
                
                # 3. Si hay un nombre de punto en la fila, lo creamos o encontramos.
                if nombre_punto:
                    # Buscamos o creamos el PuntoExacto vinculado al AreaTrabajo que acabamos de obtener.
                    punto_exacto, created_punto = PuntoExacto.objects.get_or_create(
                        area_trabajo=area_trabajo,
                        nombre_punto=nombre_punto
                    )

                    if created_punto:
                        self.stdout.write(f"    - Creado nuevo Punto Exacto: '{nombre_punto}' en '{nombre_area}'")
                        puntos_creados += 1
                    else:
                        puntos_existentes += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado en la fila {index + 2} de AreaTrabajo: {e}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"  + Proceso finalizado. {areas_creadas} áreas nuevas creadas. "
            f"{puntos_creados} puntos nuevos creados, {puntos_existentes} puntos ya existían."
        ))