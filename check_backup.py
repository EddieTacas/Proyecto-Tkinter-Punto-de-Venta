import sqlite3

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # List all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables found:")
    for table in tables:
        print(f"- {table[0]}")
        
    # Check if _issuers_old_v13 exists and has data
    if ('_issuers_old_v13',) in tables:
        cur.execute("SELECT count(*) FROM _issuers_old_v13")
        count = cur.fetchone()[0]
        print(f"Rows in _issuers_old_v13: {count}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
