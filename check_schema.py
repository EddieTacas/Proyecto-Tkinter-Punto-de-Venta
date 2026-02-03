import sqlite3

try:
    conn = sqlite3.connect('c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db')
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issuers'")
    result = cur.fetchone()
    if result:
        print(result[0])
    else:
        print("Table 'issuers' not found.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
