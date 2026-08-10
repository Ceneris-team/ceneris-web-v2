# en inventario/management/commands/import_inventario.py

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from django.apps import apps

class Command(BaseCommand):
    help = 'Importa datos de inventario, áreas y personal desde un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='La ruta al archivo Excel a importar')

    @staticmethod
    def normalize_columns(df):
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        return df

    def handle(self, *args, **options):
        # --- OBTENEMOS LOS MODELOS DE FORMA DINÁMICA ---
        # Esto evita importaciones directas al principio del archivo.
        AreaTrabajo = apps.get_model('personal', 'AreaTrabajo')
        Personal = apps.get_model('personal', 'Personal')
        Insumo = apps.get_model('inventario', 'Insumo')
        ItemInsumo = apps.get_model('inventario', 'ItemInsumo')
        Accesorio = apps.get_model('inventario', 'Accesorio')
        
        excel_file_path = options['excel_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importación desde {excel_file_path}...'))

        try:
            xls = pd.ExcelFile(excel_file_path)
            df_insumos = self.normalize_columns(pd.read_excel(xls, sheet_name='Insumo'))
            df_items = self.normalize_columns(pd.read_excel(xls, sheet_name='ItemsInsumo'))
            df_accesorios = self.normalize_columns(pd.read_excel(xls, sheet_name='Accesorio'))
            df_areas = self.normalize_columns(pd.read_excel(xls, sheet_name='AreaTrabajo'))
            df_personal = self.normalize_columns(pd.read_excel(xls, sheet_name='Personal'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocurrió un error al leer el archivo Excel: {e}'))
            return

        # --- IMPORTACIÓN EN ORDEN DE DEPENDENCIA ---

        # 1. Importar AreaTrabajo (no depende de nadie)
        self.stdout.write(self.style.SUCCESS('Importando Áreas de Trabajo...'))
        for index, row in df_areas.iterrows():
            nombre_area = str(row['nombre']).strip()
            if nombre_area:
                AreaTrabajo.objects.update_or_create(nombre=nombre_area)
        
        # 2. Importar Personal (depende de AreaTrabajo)
        self.stdout.write(self.style.SUCCESS('Importando Personal...'))
        for index, row in df_personal.iterrows():
            try:
                dni = str(row['dni']).strip()
                if not dni: continue
                
                nombre_area_trabajo = str(row.get('area_trabajo', '')).strip()
                area_obj = None
                if nombre_area_trabajo:
                    # Buscamos el objeto AreaTrabajo por su nombre
                    area_obj, _ = AreaTrabajo.objects.get_or_create(nombre=nombre_area_trabajo)

                Personal.objects.update_or_create(
                    dni=dni,
                    defaults={
                        'nombre': str(row.get('nombre', '')).strip(),
                        'apellido': str(row.get('apellido', '')).strip(),
                        'cargo': str(row.get('cargo', '')).strip(),
                        'correo': str(row.get('correo', '')).strip(),
                        'telefono': str(row.get('telefono', '')).strip(),
                        'area_trabajo': area_obj # Asignamos el objeto FK
                    }
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error inesperado en fila {index} (Personal): {e}"))

        # --- 1. Importar Tipos de Insumo ---
        self.stdout.write(self.style.SUCCESS('Importando Insumos...'))
        for index, row in df_insumos.iterrows():
            try:
                # Limpiamos los datos de la fila
                nombre = str(row['nombre']).strip()
                if not nombre: continue

                costo = row.get('costo_unitario_actual')
        
                # 2. Comprobamos si el valor es 'nan' (celda vacía) y lo convertimos a 0.00.
                #    También podrías usar None si tu campo permite null=True.
                if pd.isna(costo):
                    costo = 0.00

                obj, created = Insumo.objects.update_or_create(
                    nombre=nombre,
                    defaults={
                        'descripcion': str(row.get('descripcion', '')).strip(),
                        'unidad_medida': str(row.get('unidad_medida', '')).strip(),
                        'costo_unitario_actual': costo
                    }
                )
            except KeyError as e:
                self.stdout.write(self.style.ERROR(f"Error en fila {index} (Insumo): Falta la columna requerida {e}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error inesperado en fila {index} (Insumo): {e}"))
        
        # --- 2. Importar Items de Insumo ---
        self.stdout.write(self.style.SUCCESS('Importando ItemsInsumo...'))
        for index, row in df_items.iterrows():
            try:
                # Limpiamos y validamos datos clave
                numero_serie = str(row['numero_serie']).strip()
                insumo_padre_nombre = str(row['insumo_padre']).strip()
                if not numero_serie or not insumo_padre_nombre:
                    self.stdout.write(self.style.WARNING(f"Advertencia en fila {index} (ItemInsumo): Se omitió por faltar 'numero_serie' o 'insumo_padre'."))
                    continue
                
                insumo_padre = Insumo.objects.get(nombre=insumo_padre_nombre)
                
                # Manejo de fechas seguro
                def parse_date(date_val):
                    if pd.isna(date_val): return None
                    return pd.to_datetime(date_val).date()

                obj, created = ItemInsumo.objects.update_or_create(
                    numero_serie=numero_serie,
                    defaults={
                        'insumo_padre': insumo_padre,
                        'codigo_interno': str(row.get('codigo_interno', '')).strip(),
                        'marca': str(row.get('marca', '')).strip(),
                        'modelo': str(row.get('modelo', '')).strip(),
                        'fecha_calibracion': parse_date(row.get('fecha_calibracion')),
                        'fecha_prox_calibracion': parse_date(row.get('fecha_prox_calibracion')),
                        'estado': str(row.get('estado', 'EN STOCK')).strip(),
                    }
                )
            except Insumo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Advertencia en fila {index}: No se encontró el insumo padre '{row['insumo_padre']}'. Se omitió."))
            except KeyError as e:
                self.stdout.write(self.style.ERROR(f"Error en fila {index} (ItemInsumo): Falta la columna requerida {e}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error inesperado en fila {index} (ItemInsumo) con serie '{numero_serie}': {e}"))
                
        # --- 3. Importar Accesorios ---
        self.stdout.write(self.style.SUCCESS('Importando Accesorios...'))
        for index, row in df_accesorios.iterrows():
            try:
                item_insumo_serie = str(row.get('item_insumo_serie', '')).strip()
                nombre_accesorio = str(row.get('nombre', '')).strip()
                
                if not item_insumo_serie or not nombre_accesorio:
                    self.stdout.write(self.style.WARNING(f"Advertencia en fila {index} (Accesorio): Se omitió por faltar 'item_insumo_serie' o 'nombre'."))
                    continue
                    
                item_insumo = ItemInsumo.objects.get(numero_serie=item_insumo_serie)
                
                obj, created = Accesorio.objects.update_or_create(
                    item_insumo=item_insumo,
                    nombre=nombre_accesorio,
                    # Hacemos que la clave única incluya también el S/N si existe
                    numero_serie=str(row.get('numero_serie', '')).strip(),
                    defaults={
                        'fecha_calibracion': parse_date(row.get('fecha_calibracion')),
                        'fecha_prox_calibracion': parse_date(row.get('fecha_prox_calibracion')),
                    }
                )
            except ItemInsumo.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Advertencia en fila {index}: No se encontró el item padre con serie '{item_insumo_serie}'. Se omitió."))
            except KeyError as e:
                self.stdout.write(self.style.ERROR(f"Error en fila {index} (Accesorio): Falta la columna requerida {e}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error inesperado en fila {index} (Accesorio) con nombre '{nombre_accesorio}': {e}"))

        self.stdout.write(self.style.SUCCESS('¡Importación completada!'))