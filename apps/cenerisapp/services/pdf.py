"""Generacion de PDF de certificados (sin dependencia de HttpRequest).

Extraido de cenerisapp/views.py durante la modularizacion.
Los cuerpos de las funciones son identicos al original.
"""

import os

from datetime import date
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint.urls import default_url_fetcher
from cenerisapp.models import DatosPDF, InformeCalibracion


def static_file_path(path):
    """
    Toma una ruta estática (ej. 'img/logo.png') y devuelve
    una URL 'file://' con la ruta absoluta del sistema de archivos.
    """

    # find() devuelve la ruta absoluta del archivo en el sistema.
    # Esto funciona tanto en DEBUG=True como en DEBUG=False (después de collectstatic)
    absolute_path = staticfiles_storage.path(path)
    
    # WeasyPrint necesita el prefijo 'file://'
    return f'file://{absolute_path}'


def generar_pdf_respuesta(request,certificado):
    """
    Toma un objeto Certificado y los datos limpios de un formulario,
    procesa toda la información y devuelve una respuesta HTTP con el PDF.
    """
    print("\n[PASO 1] Entrando en generar_pdf_respuesta...")
    patrones = certificado.patronescalibracion_set.all()
    resultados = certificado.resultados_set.all()
    dispositivo_asociado = certificado.dispositivo # Obtenemos el dispositivo directamente

    
    nombre_equipo = 'N/A'
    nombre_modelo = 'N/A'
    nombre_fabricante = 'N/A'
    nombre_area = 'N/A'
    tag_dispositivo = 'N/A'
    sensores_texto = 'N/A'
    ns_sensores_texto = 'N/A'
    es_portatil = False
    texto_area_completa = 'N/A'

    if dispositivo_asociado:
        es_portatil = dispositivo_asociado.tipoDisp == 'Portatil'
        nombre_fabricante = dispositivo_asociado.fabDisp
        area_texto = dispositivo_asociado.area_general or ""
        
        # Si tiene un área de trabajo fija asignada, la añadimos
        if dispositivo_asociado.id_areaTrabajo_fijo:
            # Añadimos un separador si ya teníamos un área general
            if area_texto:
                area_texto += " - "
            # Concatenamos el nombre del área específica
            area_texto += dispositivo_asociado.id_areaTrabajo_fijo.nombreA
        
        # Si después de todo, la cadena no está vacía, la usamos.
        if area_texto:
            texto_area_completa = area_texto

        tag_dispositivo = dispositivo_asociado.tag
        
        if es_portatil:
            nombre_equipo = 'Detector multigas'
            nombre_modelo = dispositivo_asociado.nomDisp # Para portátiles, el modelo es el nombre
            
            
            todos_sensores = dispositivo_asociado.sensor_set.all()
            if todos_sensores.exists():
                lista_de_gases = list(filter(None, [s.tipGas for s in todos_sensores]))
                sensores_texto = ", ".join(lista_de_gases) if lista_de_gases else 'No especificado'
                lista_de_series = [s.nSerieActual for s in todos_sensores]
                ns_sensores_texto = ", ".join(lista_de_series)
            else:
                sensores_texto = 'Sin sensores asignados'
                ns_sensores_texto = 'N/A'
        else: # Es Fijo
            nombre_equipo = 'Monitor estacionario'
            nombre_modelo = dispositivo_asociado.nomDisp
            
            # --- ¡LÓGICA CORREGIDA Y MEJORADA PARA FIJOS! ---
            
            # 1. Obtenemos el sensor específico desde el certificado que estamos procesando.
            sensor_calibrado = None
            if certificado.componente and hasattr(certificado.componente, 'sensor'):
                sensor_calibrado = certificado.componente.sensor
                
            if sensor_calibrado:
                # Si encontramos el sensor, llenamos sus datos básicos.
                sensores_texto = sensor_calibrado.tipGas
                
                # 2. Buscamos el último InformeCalibracion para ESE sensor.
                ultimo_informe = InformeCalibracion.objects.filter(sensor=sensor_calibrado).order_by('-fecha_informe').first()
                
                # 3. Asignamos el valor de 'encontrado_calibracion' a la variable de la plantilla.
                if ultimo_informe and ultimo_informe.encontrado_calibracion:
                    ns_sensores_texto = ultimo_informe.encontrado_calibracion
                else:
                    # Si no hay informe o el campo está vacío, usamos el N/S del sensor como un valor de respaldo (fallback).
                    self.stdout.write(self.style.WARNING(f"    - Advertencia: No se encontró 'encontrado_calibracion' para el sensor {sensor_calibrado}. Usando N/S como fallback."))
                    ns_sensores_texto = sensor_calibrado.nSerieActual or 'N/A'
            else:
                # Fallback si el certificado no está vinculado a un sensor.
                sensores_texto = 'Sensor no especificado'
                ns_sensores_texto = 'N/A'   
    
    estado_inicial_texto = certificado.estado_inicial or "Primera Calibración"

    
    try:
        # Usamos el 'related_name' que definimos en el modelo
        datos_pdf = certificado.datos_pdf 
    except DatosPDF.DoesNotExist:
        datos_pdf = None
    
    fecha_generacion = date.today()
    static_root = os.path.join(settings.BASE_DIR, 'cenerisapp', 'static')

    
    context_pdf = {
        'certificado': certificado,
        'patrones': patrones,
        'resultados': resultados,
        'logo_path': os.path.join(static_root, 'img', 'logo_ceneris.jpg'),
        'watermark_path': os.path.join(static_root, 'img', 'marca_de_agua.png'),
        'es_portatil': es_portatil,
        'nombre_equipo': nombre_equipo,
        'nombre_modelo': nombre_modelo,
        'nombre_fabricante': nombre_fabricante,
        'nombre_area': texto_area_completa,
        'tag_dispositivo': tag_dispositivo,
        'ns_dispositivo': dispositivo_asociado.num_serie if dispositivo_asociado else 'N/A',
        'sensores_texto': sensores_texto,
        'ns_sensores_texto': ns_sensores_texto,
        'estado_inicial_texto': estado_inicial_texto,
        'num_paginas_pdf': datos_pdf.num_paginas_pdf if datos_pdf else 'N/A',
        'codigo_pdf': datos_pdf.codigo_pdf if datos_pdf else 'N/A',
        'version_pdf': datos_pdf.version_pdf if datos_pdf else 'N/A',
        'fecha_generacion': fecha_generacion,
    }
    print("[PASO 2] Contexto del PDF preparado con éxito.")

    def s3_and_static_fetcher(url):
        # ---------------------------------------------
        # CASO 1: Archivos ESTÁTICOS (logos, css)
        # ---------------------------------------------
        # Estos SÍ están en el disco local del servidor en la carpeta 'staticfiles'
        if url.startswith(settings.STATIC_URL):
            path = url[len(settings.STATIC_URL):]
            absolute_path = finders.find(path)
            if absolute_path:
                print(f"✅ WeasyPrint (STATIC): Abriendo archivo local: {absolute_path}")
                return default_url_fetcher(f'file://{absolute_path}')
            else:
                print(f"❌ WeasyPrint ERROR (STATIC): No se encontró: {path}")
        
        # ---------------------------------------------
        # CASO 2: Archivos MULTIMEDIA (anexos de S3)
        # ---------------------------------------------
        # La URL completa de S3 o la relativa /media/
        elif settings.MEDIA_URL in url:
            # Extraemos la ruta del archivo dentro del bucket/media
            # ej. de '/media/anexos/img.png' -> 'anexos/img.png'
            path = url.split(settings.MEDIA_URL, 1)[-1]
            try:
                # 'default_storage' en producción es tu S3Boto3Storage.
                # .open() usa la API de boto3 para obtener un stream del archivo,
                # lo cual es mucho más rápido y fiable que una petición HTTP.
                print(f"✅ WeasyPrint (MEDIA): Abriendo desde S3 storage: {path}")
                file = default_storage.open(path)
                
                # Le pasamos el contenido en memoria a WeasyPrint
                return {'file_obj': file}
            
            except Exception as e:
                print(f"❌ WeasyPrint ERROR (MEDIA): No se pudo abrir desde S3: {path}. Error: {e}")

        # Para cualquier otra URL externa, usa la lógica por defecto (descarga HTTP)
        return default_url_fetcher(url)
    
    print("[PASO 3] Renderizando la plantilla HTML...")
    
    try:
        # --- Renderizado del HTML ---
        print("[PASO 4] Renderizando la plantilla HTML a string...")
        html_string = render_to_string('certificado/certificado_detalle.html', context_pdf, request=request)
        print("[PASO 5] Plantilla HTML renderizada con éxito.")
        
        # --- Creación del objeto WeasyPrint ---
        print("[PASO 6] Creando objeto HTML de WeasyPrint...")
        html = HTML(string=html_string, url_fetcher=s3_and_static_fetcher)
        print("[PASO 7] Objeto HTML de WeasyPrint creado.")

        # --- ¡EL PUNTO MÁS PROBABLE DE FALLO! ---
        print("[PASO 8] INICIANDO renderizado del PDF con html.write_pdf()... (Este puede tardar)")
        pdf_file = html.write_pdf()
        print("[PASO 9] ¡PDF renderizado con éxito en memoria!") # Si ves esto, el problema está después

        # --- Creación de la Respuesta HTTP ---
        print("[PASO 10] Creando respuesta HTTP...")
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Certificado-Nro-{certificado.nro_certificado}.pdf"'
        print("[PASO 11] Respuesta HTTP creada. Devolviendo al navegador.")
        return response
    except Exception as e:
        print(f"!!!!!!!!!!!!!!! ERROR INESPERADO DENTRO DE generar_pdf_respuesta !!!!!!!!!!!!!!!")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje: {e}")
        import traceback
        traceback.print_exc()
        # Devolvemos un error 500 explícito para que no haya timeout
        return HttpResponse("Ocurrió un error interno al generar el PDF.", status=500)
