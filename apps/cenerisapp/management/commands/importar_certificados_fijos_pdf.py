import fitz  # PyMuPDF
import re
import os
import calendar
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from cenerisapp.models import Dispositivo, Sensor, Certificado, PatronesCalibracion, Resultados, InformeCalibracion

class Command(BaseCommand):
    help = 'Importa datos de certificados de calibración para DISPOSITIVOS FIJOS desde una carpeta de PDFs.'

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='La ruta a la carpeta que contiene los archivos PDF de fijos.')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        if not os.path.isdir(folder_path):
            raise CommandError(f'La ruta especificada no es una carpeta válida: {folder_path}')

        meses_es_rev = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

        for filename in os.listdir(folder_path):
            if not filename.lower().endswith('.pdf'):
                continue

            file_path = os.path.join(folder_path, filename)
            self.stdout.write(f"\n--- Procesando archivo de Fijo: {filename} ---")
            
            try:
                doc = fitz.open(file_path)
                full_text = "".join([page.get_text() for page in doc])
                doc.close()

                def find_value(pattern, text, group=1):
                    match = re.search(pattern, text, re.IGNORECASE)
                    return match.group(group).strip() if match else None

                # 1. EXTRACCIÓN DE DATOS PRINCIPALES DEL CERTIFICADO
                nro_certificado = find_value(r'CERTIFICADO NRO:\s*(\S+)', full_text)
                codigo_smcv = find_value(r'Código SMCV:\s*(\S+)', full_text) # <-- Nueva clave de búsqueda
                tipo_sensor_str = find_value(r'Tipo de sensor:\s*(\S+)', full_text)
                ns_sensor_str = find_value(r'N/S:\s*([\w\-]+)', full_text) # ej: Mar-24
                
                fecha_cal_str = find_value(r'Fecha de calibración:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text)
                prox_fecha_cal_str = find_value(r'Próxima calibración:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text)
                
                estado_inicial = find_value(r'Estado Inicial:\s*(\w+)', full_text)
                estado_final = find_value(r'Estado Final:\s*(\w+)', full_text)
                
                temp = find_value(r'Temperatura\s*([\d\.]+\s*°C)', full_text)
                presion = find_value(r'Presión\s*([\d\.]+\s*hPa)', full_text)
                humedad = find_value(r'Humedad Relativa\s*(\d+\s*%)', full_text)
                rango_medicion = find_value(r'Gases y Rango de Medición:\s*(.*)', full_text)

                # --- VERIFICACIÓN EN TERMINAL ---
                self.stdout.write("    [VERIFICACIÓN DE DATOS EXTRAÍDOS]")
                self.stdout.write(f"    - N° Certificado: {nro_certificado}")
                self.stdout.write(f"    - Código SMCV (Dispositivo): {codigo_smcv}")
                self.stdout.write(f"    - Tipo de Sensor (Gas): {tipo_sensor_str}")
                self.stdout.write(f"    - N/S (Dato extra): {ns_sensor_str}")
                self.stdout.write(f"    - Fecha Calibración: {fecha_cal_str}")

                # 2. VALIDACIÓN Y BÚSQUEDA DE OBJETOS
                if not all([nro_certificado, codigo_smcv, tipo_sensor_str, fecha_cal_str]):
                    self.stdout.write(self.style.ERROR("  - Error: Faltan datos clave. Saltando archivo."))
                    continue
                
                # Buscamos el dispositivo por 'num_serie' que coincide con 'Código SMCV'
                dispositivo = Dispositivo.objects.get(num_serie=codigo_smcv)

                # --- ¡LÓGICA DE BÚSQUEDA DE DOS PASOS RESTAURADA Y ADAPTADA! ---
                sensor = None
                
                # PASO 1: Intentar identificar el sensor a través de un informe existente (usando el campo N/S del PDF).
                # El valor de 'N/S' del PDF (ej. Mar-24) se busca en el 'encontrado_calibracion' del Informe.
                if ns_sensor_str:
                    informes_coincidentes = InformeCalibracion.objects.filter(
                        sensor__dispositivo_instalado=dispositivo,
                        sensor__tipGas__iexact=tipo_sensor_str,
                        encontrado_calibracion__icontains=ns_sensor_str
                    ).select_related('sensor')
                    
                    if informes_coincidentes.count() == 1:
                        sensor = informes_coincidentes.first().sensor
                        self.stdout.write(f"    - Sensor '{sensor}' identificado vía informe existente con '{ns_sensor_str}'.")
                    elif informes_coincidentes.count() > 1:
                        self.stdout.write(self.style.WARNING(f"    - ADVERTENCIA: Múltiples informes previos con '{ns_sensor_str}'. Se usará el primero."))
                        sensor = informes_coincidentes.first().sensor

                # PASO 2: Si el PASO 1 falló (no se encontró informe o 'N/S' estaba vacío), intentamos la búsqueda directa.
                if not sensor:
                    self.stdout.write(self.style.WARNING(f"    - No se encontró informe previo con '{ns_sensor_str}'. Intentando búsqueda directa por tipo de gas."))
                    
                    sensores_posibles = Sensor.objects.filter(
                        dispositivo_instalado=dispositivo,
                        tipGas__iexact=tipo_sensor_str
                    ).order_by('pk')

                    if sensores_posibles.exists():
                        sensor = sensores_posibles.first()
                        if sensores_posibles.count() > 1:
                            self.stdout.write(self.style.WARNING(
                                f"    - ADVERTENCIA: Se encontraron {sensores_posibles.count()} sensores de tipo '{tipo_sensor_str}'. "
                                f"Se asignará al primero encontrado: '{sensor}'."
                            ))
                        else:
                             self.stdout.write(f"    - Sensor '{sensor}' identificado directamente (único con ese tipo de gas).")
                    else:
                        raise Sensor.DoesNotExist

                # 3. PROCESAR DATOS Y GUARDAR
                fecha_cal = datetime.strptime(fecha_cal_str, '%d/%m/%Y')
                fecha_cal_aware = timezone.make_aware(fecha_cal, timezone.get_default_timezone())
                prox_fecha_cal = datetime.strptime(prox_fecha_cal_str, '%d/%m/%Y').date() if prox_fecha_cal_str else None

                certificado, created = Certificado.objects.update_or_create(
                    nro_certificado=nro_certificado,
                    defaults={
                        'dispositivo': dispositivo, 'id_empresa': dispositivo.id_empresa,
                        'componente': sensor, 'estado_inicial': estado_inicial, 'estadoFinal': estado_final,
                        'fechCertificado': fecha_cal_aware, 'proxFecha': prox_fecha_cal,
                        'temp': temp or '', 'presion': presion or '', 'humedadRelativa': humedad or '',
                        'rango_medicion': rango_medicion or '',
                    }
                )

                if created: self.stdout.write(self.style.SUCCESS(f"  + CREADO Certificado '{nro_certificado}'"))
                else:
                    self.stdout.write(f"  = ACTUALIZADO Certificado '{nro_certificado}'")
                    PatronesCalibracion.objects.filter(certificado=certificado).delete()
                    Resultados.objects.filter(id_certificado=certificado).delete()
                    self.stdout.write("    - Patrones y Resultados antiguos borrados.")
                
                # --- Guardar Patrones ---
                # N° | Patrón Utilizado | N/P | Lote N° | N° Certificado | Expiración
                patrones_matches = re.findall(r'Cilindro \d+\s+(.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\w\-]+)', full_text, re.IGNORECASE)
                
                patrones_guardados_count = 0
                for match in patrones_matches:
                    exp_date = None
                    exp_str = match[4].strip()

                    try:
                        # --- ¡LÓGICA DE FECHA ROBUSTA! ---
                        # Dividimos 'Abr-2030'
                        mes_abreviado, ano_str = exp_str.split('-')
                        # Buscamos el mes en nuestro diccionario
                        mes_num = meses_es_rev[mes_abreviado.lower().strip()]
                        
                        # Convertimos el año. Si tiene 2 dígitos, asumimos 20xx.
                        ano_num = int(ano_str)
                        if ano_num < 100:
                            ano_num += 2000 
                        
                        # --- TU REQUERIMIENTO: Usar el día 28 ---
                        dia = 28
                        
                        # Creamos el objeto de fecha
                        exp_date = date(ano_num, mes_num, dia)

                    except (ValueError, KeyError) as e:
                        self.stdout.write(self.style.WARNING(f"    - ADVERTENCIA: No se pudo procesar la fecha de expiración '{exp_str}'. Saltando este patrón. Error: {e}"))
                        continue # <-- Saltamos al siguiente patrón si la fecha es inválida

                    # Si llegamos aquí, 'exp_date' es una fecha válida. Procedemos a guardar.
                    PatronesCalibracion.objects.create(
                        certificado=certificado,
                        numPatron=f"Cilindro {len(patrones_matches)}",
                        patronUtil=match[0].strip(),
                        n_p=match[1].strip(),
                        n_lote=match[2].strip(),
                        n_certificado=match[3].strip(),
                        fechaExpiracion=exp_date # <-- Ahora siempre es un objeto de fecha válido
                    )
                    patrones_guardados_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"    + {patrones_guardados_count} de {len(patrones_matches)} registros de Patrones GUARDADOS."))
                
                # --- Guardar Resultados ---
                # Gas | Lectura Patrón | Lectura del equipo | % Error
                resultados_matches = re.findall(
                    r'^\s*([A-Z0-9/]+)\s+'                      # 1: Gas (al inicio de la línea)
                    r'([\d.]+\s*%\s*Vol\.?|[\d.]+\s*ppm)\s+'   # 2: Lectura Patrón
                    r'([\d.]+\s*%\s*Vol\.?|[\d.]+\s*ppm)\s+'   # 3: Lectura Equipo
                    r'([\d.]+\s*%)',                           # 4: Error
                    full_text,
                    re.MULTILINE | re.IGNORECASE
                )

                # 2. VERIFICACIÓN EN TERMINAL
                self.stdout.write(f"    - Resultados encontrados por la Regex: {len(resultados_matches)}")
                for i, r in enumerate(resultados_matches):
                    self.stdout.write(f"      - Fila {i+1}: {' | '.join(r)}")

                # 3. LÓGICA DE GUARDADO
                resultados_guardados_count = 0
                if resultados_matches:
                    for match in resultados_matches:
                        gas = match[0].strip()
                        lectura_patron = match[1].strip()
                        lectura_equipo = match[2].strip()
                        porc_error = match[3].strip()

                        # Usamos update_or_create para evitar duplicados si el script se re-ejecuta
                        resultado, created = Resultados.objects.update_or_create(
                            id_certificado=certificado,
                            gas=gas,
                            defaults={
                                'lecturaPatron': lectura_patron,
                                'lecturaEquipo': lectura_equipo,
                                'prob_error': porc_error
                            }
                        )
                        resultados_guardados_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"    + {resultados_guardados_count} de {len(resultados_matches)} registros de Resultados GUARDADOS/ACTUALIZADOS."))

            except Dispositivo.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  - Error: Dispositivo con Código SMCV '{codigo_smcv}' no encontrado."))
            except Sensor.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  - Error: No se encontró un sensor de tipo '{tipo_sensor_str}' en el dispositivo '{codigo_smcv}'."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error GENERAL al procesar el archivo {filename}: {e}"))
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS('\n¡Proceso de importación de fijos finalizado!'))