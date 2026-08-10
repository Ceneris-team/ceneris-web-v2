#!/usr/bin/env python
"""
Script de prueba para debuggear el problema de renderización de fechas/horas en EMO
Simula el flujo de creación de EMO sin necesidad del servidor Django
Se ejecuta con: python manage.py shell < test_emo_debug_shell.py
"""

import os
import re
from datetime import date, time as time_obj

from django.template.loader import render_to_string
from calidad.models import EMO, Clinica
from recursoshumanos.models import Trabajador

print("[TEST] === INICIANDO PRUEBA DE RENDER EMO ===\n")

try:
    trabajador = Trabajador.objects.first()
    clinica = Clinica.objects.first()
    
    if not trabajador:
        print("[ERROR] No hay trabajadores en la BD")
    elif not clinica:
        print("[ERROR] No hay clínicas en la BD")
    else:
        print(f"[TEST] Trabajador: {trabajador.nombres}")
        print(f"[TEST] Clínica: {clinica.nombre}\n")
        
        # Crear EMO TEMPORAL (sin guardar en BD)
        emo = EMO(
            trabajador=trabajador,
            tipo_emo='Retiro',
            fecha_programada=date(2025, 12, 12),
            hora_examen=time_obj(13, 56, 0),
            lugar_examen=clinica,
            estado='Programado',
            aptitud='Pendiente',
        )
        
        print(f"[TEST] === EMO TEMPORAL CREADO ===")
        print(f"[TEST] emo.fecha_programada = {emo.fecha_programada} (tipo: {type(emo.fecha_programada).__name__})")
        print(f"[TEST] emo.hora_examen = {emo.hora_examen} (tipo: {type(emo.hora_examen).__name__})")
        print(f"[TEST] bool(emo.fecha_programada) = {bool(emo.fecha_programada)}")
        print(f"[TEST] bool(emo.hora_examen) = {bool(emo.hora_examen)}")
        print(f"[TEST] emo.lugar_examen.google_maps_url = {emo.lugar_examen.google_maps_url}")
        print(f"[TEST] emo.lugar_examen.imagen_fachada = {emo.lugar_examen.imagen_fachada}\n")
        
        # Renderizar el template
        print(f"[TEST] === RENDERIZANDO TEMPLATE ===\n")
        
        clinica_fachada_url = ''
        if emo.lugar_examen and getattr(emo.lugar_examen, 'imagen_fachada', None):
            clinica_fachada_url = f"/media/{emo.lugar_examen.imagen_fachada}"
        
        html_content = render_to_string('calidad/emails/notificacion_emo_programado.html', {
            'trabajador': emo.trabajador,
            'emo': emo,
            'comentario_alerta': 'Test comment',
            'clinica_fachada_url': clinica_fachada_url,
        })
        
        # Analizar el HTML resultante
        print(f"[TEST] === ANALIZANDO HTML GENERADO ===\n")
        
        # Extraer la sección de clínica
        clinica_match = re.search(
            r'Información de la Clínica.*?(?=</section>|</div>)',
            html_content,
            re.DOTALL | re.IGNORECASE
        )
        
        if clinica_match:
            clinica_section = clinica_match.group(0)
            print(f"[TEST] ✓ Sección de clínica encontrada\n")
            
            # Buscar la palabra "Fecha" en la sección
            if 'Fecha' in clinica_section:
                print(f"[TEST] ✓ Etiqueta 'Fecha' encontrada en HTML")
                # Extraer la fila de fecha
                fecha_row = re.search(r'<tr>.*?Fecha.*?</tr>', clinica_section, re.DOTALL | re.IGNORECASE)
                if fecha_row:
                    print(f"[TEST] Fila Fecha:\n{fecha_row.group(0)}\n")
            else:
                print(f"[TEST] ✗ 'Fecha' NO encontrada en la sección de clínica\n")
            
            # Buscar la palabra "Hora"
            if 'Hora' in clinica_section:
                print(f"[TEST] ✓ Etiqueta 'Hora' encontrada en HTML")
                # Extraer la fila de hora
                hora_row = re.search(r'<tr>.*?Hora.*?</tr>', clinica_section, re.DOTALL | re.IGNORECASE)
                if hora_row:
                    print(f"[TEST] Fila Hora:\n{hora_row.group(0)}\n")
            else:
                print(f"[TEST] ✗ 'Hora' NO encontrada en la sección de clínica\n")
            
            # Buscar Google Maps
            if 'maps.google.com' in html_content or 'google_maps' in html_content:
                print(f"[TEST] ✓ URL Google Maps encontrada\n")
                maps_links = re.findall(r'href="([^"]*maps[^"]*)"', html_content)
                for link in maps_links:
                    print(f"[TEST] Link Google Maps: {link[:80]}...\n")
            else:
                print(f"[TEST] ✗ URL Google Maps NO encontrada\n")
            
            print(f"[TEST] === MOSTRANDO SECCIÓN DE CLÍNICA (primeras 1500 caracteres) ===\n")
            print(clinica_section[:1500])
            print("\n[TEST] ...\n")
        else:
            print(f"[TEST] ✗ Sección de clínica NO encontrada en HTML\n")
        
        # Guardar HTML a archivo para inspección manual
        debug_dir = 'debug_emails'
        os.makedirs(debug_dir, exist_ok=True)
        debug_file = os.path.join(debug_dir, 'test_email.html')
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n[TEST] ✓ HTML completo guardado en: {debug_file}")
        print(f"[TEST] Puedes abrirlo en el navegador para verlo renderizado\n")

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

print("[TEST] === FIN DE PRUEBA ===")
