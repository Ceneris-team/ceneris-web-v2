import fitz  # PyMuPDF
import re
import os
import calendar
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from cenerisapp.models import Dispositivo, Certificado, PatronesCalibracion, Resultados, Empresa, Sensor

class Command(BaseCommand):
    help = 'Importa datos de certificados de calibración desde una carpeta de archivos PDF.'

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='La ruta a la carpeta que contiene los archivos PDF.')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        if not os.path.isdir(folder_path):
            raise CommandError(f'La ruta especificada no es una carpeta válida: {folder_path}')

        # Diccionario para convertir mes en español a número
        meses_es = { 'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12 }

        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(folder_path, filename)
                self.stdout.write(f"\n--- Procesando archivo: {filename} ---")
                
                try:
                    # 1. LEER TODO EL TEXTO DEL PDF
                    doc = fitz.open(file_path)
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text()
                    doc.close()

                    # --- 2. EXTRACCIÓN DE DATOS CON EXPRESIONES REGULARES (REGEX) ---
                    
                    # Datos del Certificado
                    nro_certificado = re.search(r'CERTIFICADO NRO:\s*(\S+)', full_text).group(1)
                    num_serie_dispositivo = re.search(r'Número de Serie:\s*(\S+)', full_text).group(1)
                    fecha_cal_str = re.search(r'Fecha de calibración:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text).group(1)
                    prox_fecha_cal_str = re.search(r'Próxima calibración:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text).group(1)
                    estado_inicial = re.search(r'Estado Inicial:\s*(\w+)', full_text).group(1)
                    estado_final = re.search(r'Estado Final:\s*(\w+)', full_text).group(1)
                    
                    # Datos Ambientales
                    temperatura = re.search(r'Temperatura\s*([\d\.]+\s*°C)', full_text).group(1)
                    presion = re.search(r'Presión\s*([\d\.]+\s*hPa)', full_text).group(1)
                    humedad = re.search(r'Humedad Relativa\s*(\d+\s*%)', full_text).group(1)


                    # --- EXTRACCIÓN DE PATRONES (LÓGICA FINAL Y ROBUSTA v3) ---
                    patrones_matches = []
                    # 1. Convertimos todo el texto en una lista de líneas limpias
                    lineas_texto = [line.strip() for line in full_text.split('\n') if line.strip()]

                    try:
                        # 2. Encontramos el índice de la línea que contiene el último encabezado ("Expiración")
                        indice_expiracion = -1
                        for i, linea in enumerate(lineas_texto):
                            if 'expiración' in linea.lower():
                                indice_expiracion = i
                                break
                        
                        if indice_expiracion != -1:
                            # 3. Los datos que nos interesan son las líneas que vienen DESPUÉS de "Expiración".
                            #    Sabemos que "Patrón Utilizado" puede ocupar 1 o 2 líneas.
                            lineas_de_datos = lineas_texto[indice_expiracion + 1:]
                            
                            self.stdout.write("    [DEBUG] Líneas de datos encontradas después de 'Expiración': " + str(lineas_de_datos))

                            # 4. Reconstruimos la fila de datos
                            #    Caso A: El "Patrón Utilizado" se partió en dos líneas (6 líneas de datos en total)
                            if len(lineas_de_datos) >= 6 and lineas_de_datos[0].startswith('4G'):
                                patron_util = f"{lineas_de_datos[0]} {lineas_de_datos[1]}"
                                fila_patron = [patron_util] + lineas_de_datos[2:6]
                                if len(fila_patron) == 5:
                                    patrones_matches = [tuple(fila_patron)]
                            #    Caso B: Todos los datos vinieron en 5 líneas
                            elif len(lineas_de_datos) >= 5:
                                fila_patron = lineas_de_datos[:5]
                                patrones_matches = [tuple(fila_patron)]
                                
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"    - ADVERTENCIA: Ocurrió un error al procesar las líneas de patrones: {e}"))


                    # --- VERIFICACIÓN EN TERMINAL ---
                    self.stdout.write(f"    - Patrones Encontrados: {len(patrones_matches)}")
                    if patrones_matches:
                        self.stdout.write(f"      - Fila 1: {' | '.join(patrones_matches[0])}")


                    # --- VERIFICACIÓN DE RESULTADOS (CORREGIDO) ---
                    resultados_matches = []
                    # Buscamos el bloque de texto que contiene los resultados
                    resultados_block = re.search(r'Resultados de Medición(.*?)Realizado:', full_text, re.DOTALL | re.IGNORECASE)
                    if resultados_block:
                        texto_resultados = resultados_block.group(1)
                        # La nueva regex es más específica para los gases y valores
                        resultados_matches = re.findall(r'([A-Z0-9/]+)\s+([\d.]+\s*%?\s*\w+)\s+([\d.]+\s*%?\s*\w+)\s+([\d.]+\s*%)', texto_resultados, re.IGNORECASE)

                    if resultados_matches:
                        self.stdout.write(f"    - Resultados Encontrados: {len(resultados_matches)}")
                        for i, r in enumerate(resultados_matches):
                            self.stdout.write(f"      - Fila {i+1}: {' | '.join(r)}")
                    else:
                        self.stdout.write(self.style.WARNING("    - Resultados: No encontrados."))
                    
                    # --- ¡NUEVO! SECCIÓN DE VERIFICACIÓN EN TERMINAL ---
                    self.stdout.write("    [VERIFICACIÓN DE DATOS EXTRAÍDOS]")
                    self.stdout.write(f"    - N° Certificado: {nro_certificado}")
                    self.stdout.write(f"    - N° Serie Dispositivo: {num_serie_dispositivo}")
                    self.stdout.write(f"    - Fecha Calibración: {fecha_cal_str}")
                    self.stdout.write(f"    - Próxima Calibración: {prox_fecha_cal_str}")
                    self.stdout.write(f"    - Estado Inicial: {estado_inicial}")
                    self.stdout.write(f"    - Estado Final: {estado_final}")
                    self.stdout.write(f"    - Temperatura: {temperatura}")
                    self.stdout.write(f"    - Presión: {presion}")
                    self.stdout.write(f"    - Humedad: {humedad}")


                    # 3. PROCESAR Y GUARDAR (solo si los datos clave existen)
                    if not all([nro_certificado, num_serie_dispositivo, fecha_cal_str, prox_fecha_cal_str]):
                        self.stdout.write(self.style.ERROR("  - Error: Faltan datos clave del certificado. Saltando guardado."))
                        continue
                    
                    dispositivo = Dispositivo.objects.get(ns=num_serie_dispositivo)
                    fecha_cal = datetime.strptime(fecha_cal_str, '%d/%m/%Y')
                    prox_fecha_cal = datetime.strptime(prox_fecha_cal_str, '%d/%m/%Y').date()
                    fecha_cal_aware = timezone.make_aware(fecha_cal, timezone.get_default_timezone())

                    certificado, created = Certificado.objects.update_or_create(
                        nro_certificado=nro_certificado,
                        defaults={
                            'dispositivo': dispositivo, 'id_empresa': dispositivo.id_empresa,
                            'estado_inicial': estado_inicial, 'estadoFinal': estado_final,
                            'fechCertificado': fecha_cal_aware, 'proxFecha': prox_fecha_cal,
                            'temp': temperatura or '', 'presion': presion or '', 'humedadRelativa': humedad or '',
                        }
                    )

                    if created: self.stdout.write(self.style.SUCCESS(f"  + CREADO Certificado: {nro_certificado}"))
                    else:
                        self.stdout.write(f"  = ACTUALIZADO Certificado: {nro_certificado}")
                        PatronesCalibracion.objects.filter(certificado=certificado).delete()
                        Resultados.objects.filter(id_certificado=certificado).delete()
                        self.stdout.write("    - Patrones y Resultados antiguos borrados para recarga.")

                    # Guardar Patrón (si se encontró)
                    if patrones_matches:
                        for patron_data in patrones_matches:
                            # Extraemos los datos de la tupla del 'match'
                            patron_util = patron_data[0].strip()
                            n_p = patron_data[1].strip()
                            n_lote = patron_data[2].strip()
                            n_certificado_patron = patron_data[3].strip()
                            exp_str = patron_data[4].strip()

                            # Convertir fecha de expiración
                            try:
                                mes_abreviado, ano = exp_str.split('-')
                                mes = meses_es[mes_abreviado.lower()]
                                ano_full = int(f"20{ano}")
                                exp_date = date(ano_full, mes, calendar.monthrange(ano_full, mes)[1])

                                PatronesCalibracion.objects.create(
                                    certificado=certificado,
                                    patronUtil=patron_util,
                                    n_p=n_p,
                                    n_lote=n_lote,
                                    n_certificado=n_certificado_patron,
                                    fechaExpiracion=exp_date
                                )
                            except (ValueError, KeyError) as e:
                                self.stdout.write(self.style.WARNING(f"    - Advertencia: No se pudo procesar la fecha de expiración '{exp_str}'. Saltando patrón. Error: {e}"))
                                continue
                        
                        self.stdout.write(self.style.SUCCESS(f"    + {len(patrones_matches)} registros de Patrones GUARDADOS."))
                    
                    # Guardar Resultados (si se encontraron)
                    if resultados_matches:
                        for match in resultados_matches:
                            Resultados.objects.create(
                                id_certificado=certificado, gas=match[0], lecturaPatron=match[1],
                                lecturaEquipo=match[2], prob_error=match[3]
                            )
                        self.stdout.write(self.style.SUCCESS(f"    + {len(resultados_matches)} registros de Resultados GUARDADOS."))

                except Dispositivo.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"  - Error: Dispositivo con N/S o código '{num_serie_dispositivo}' no encontrado. Saltando certificado."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  - Error GENERAL al procesar el archivo {filename}: {e}"))
                    import traceback
                    traceback.print_exc()

            self.stdout.write(self.style.SUCCESS('\n¡Proceso de importación finalizado!'))