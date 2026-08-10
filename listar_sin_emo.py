import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')
django.setup()

from recursoshumanos.models import Trabajador

print("=" * 80)
print("TRABAJADORES SIN EMO REGISTRADO")
print("=" * 80)

trabajadores_sin_emo = Trabajador.objects.filter(
    activo=True,
    historial_emo__isnull=True
).order_by('apellido_paterno', 'nombres')

print(f"\nTotal: {trabajadores_sin_emo.count()} trabajadores sin EMO\n")

for i, t in enumerate(trabajadores_sin_emo, 1):
    # Obtener su asignación actual
    asignacion = t.asignaciones.filter(activo=True).first()
    proyecto = asignacion.proyecto.nombre if asignacion else "N/A"
    cargo = asignacion.cargo.nombre if asignacion and asignacion.cargo else "N/A"
    empresa = t.empresa.nombre if t.empresa else "N/A"
    
    print(f"{i:2d}. {t.nombre_completo:40s} | DNI: {t.dni:10s} | Empresa: {empresa:30s}")
    print(f"    Proyecto: {proyecto} | Cargo: {cargo}\n")

print("=" * 80)
