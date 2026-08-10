import sqlite3
import datetime

c = sqlite3.connect('db.sqlite3')
cur = c.cursor()

print('=== TRABAJADORES ACTIVOS ===')
trabajadores = cur.execute('SELECT id, nombres, apellido_paterno FROM recursoshumanos_trabajador WHERE activo=1 LIMIT 5').fetchall()
for t in trabajadores:
    print(f"ID: {t[0]}, Nombre: {t[1]} {t[2]}")

print('\n=== TAREOS RECIENTES (últimos 10) ===')
tareos = cur.execute('SELECT id, trabajador_id, fecha, resultado, horas_tardanza FROM recursoshumanos_tareodiario ORDER BY fecha DESC LIMIT 10').fetchall()
for tareo in tareos:
    print(f"ID: {tareo[0]}, Trabajador: {tareo[1]}, Fecha: {tareo[2]}, Resultado: {tareo[3]}, Horas Tardanza: {tareo[4]}")

print('\n=== TAREOS MARZO 2026 ===')
count_marzo = cur.execute("SELECT COUNT(*) FROM recursoshumanos_tareodiario WHERE fecha >= '2026-03-01' AND fecha <= '2026-03-31'").fetchone()
print(f"Total tareos en marzo 2026: {count_marzo[0]}")

print('\n=== TAREOS POR TRABAJADOR (primeros 3 trabajadores) ===')
for t in trabajadores[:3]:
    count_por_trabajador = cur.execute(f"SELECT COUNT(*) FROM recursoshumanos_tareodiario WHERE trabajador_id = {t[0]}").fetchone()
    print(f"{t[1]} {t[2]} (ID {t[0]}): {count_por_trabajador[0]} tareos")

print('\n=== RANGO DE FECHAS EN TAREOS ===')
min_fecha = cur.execute("SELECT MIN(fecha), MAX(fecha) FROM recursoshumanos_tareodiario").fetchone()
print(f"Fecha mínima: {min_fecha[0]}, Fecha máxima: {min_fecha[1]}")

c.close()
