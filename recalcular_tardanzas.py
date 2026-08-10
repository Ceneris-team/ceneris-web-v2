"""
Script para recalcular horas_tardanza en todos los tareos existentes.
Aplica la lógica correcta: tardanza solo si hora_entrada > 8:30
"""
import os
import django
from datetime import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.settings")
django.setup()

from recursoshumanos.models import TareoDiario

print("=" * 70)
print("RECALCULANDO HORAS DE TARDANZA (Base: 8:30 AM)")
print("=" * 70)

# Obtener todos los tareos con hora_entrada_real registrada
tareos = TareoDiario.objects.filter(hora_entrada_real__isnull=False).order_by('-fecha')

total = tareos.count()
actualizados = 0
sin_tardanza = 0

print(f"\nTotal de tareos a procesar: {total}\n")

HORA_ENTRADA_BASE = time(8, 30)

for idx, tareo in enumerate(tareos, 1):
    hora_entrada = tareo.hora_entrada_real
    
    # Verificar si la entrada es después de las 8:30
    if hora_entrada > HORA_ENTRADA_BASE:
        # Calcular la tardanza correctamente
        # h_tarde = horas totales - 8.5 horas
        minutos_entrada = hora_entrada.hour * 60 + hora_entrada.minute
        minutos_base = 8 * 60 + 30  # 8:30 = 510 minutos
        minutos_tardanza = minutos_entrada - minutos_base
        horas_tardanza = minutos_tardanza / 60.0
        
        tareo.horas_tardanza = round(horas_tardanza, 2)
    else:
        # Si entra antes o a las 8:30, no hay tardanza
        tareo.horas_tardanza = 0.0
        sin_tardanza += 1
    
    tareo.save(update_fields=['horas_tardanza'])
    actualizados += 1
    
    if idx % 50 == 0 or idx == total:
        print(f"  Procesados: {idx}/{total} ({tareo.fecha})")

print("\n" + "=" * 70)
print(f"✓ ACTUALIZACIÓN COMPLETADA")
print(f"  - Tareos procesados: {actualizados}")
print(f"  - Sin tardanza (entrada ≤ 8:30): {sin_tardanza}")
print(f"  - Con tardanza (entrada > 8:30): {actualizados - sin_tardanza}")
print("=" * 70)
