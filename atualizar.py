# verificar_tipos.py
import sqlite3, os

db_path = os.path.join(os.environ.get('LOCALAPPDATA'), 'My Network', 'mynetwork.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT tipo, COUNT(*) FROM equipamentos GROUP BY tipo")
for row in cursor.fetchall():
    print(f"tipo='{row[0]}' → {row[1]} equipamentos")

conn.close()