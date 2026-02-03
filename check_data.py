import sqlite3

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*), name FROM issuers GROUP BY id")
    rows = cur.fetchall()
    print(f"Total issuers found: {len(rows)}")
    for row in rows:
        print(f"- {row[1]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
