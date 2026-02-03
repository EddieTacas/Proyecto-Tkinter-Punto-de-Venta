import sqlite3

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issuers'")
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print(f"Error: {e}")
