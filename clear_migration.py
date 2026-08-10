import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Eliminar el registro de la migración de metricas_ceneris
cursor.execute("DELETE FROM django_migrations WHERE app = 'metricas_ceneris'")
conn.commit()

print(f"Registros eliminados: {cursor.rowcount}")

conn.close()
