import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'metricas%'")
tables = cursor.fetchall()

print('Tablas de metricas_ceneris encontradas:')
for table in tables:
    print(f"  - {table[0]}")

if not tables:
    print("  ¡No se encontraron tablas de metricas_ceneris!")

conn.close()
