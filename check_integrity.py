import sqlite3

try:
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check")
    print(cur.fetchall())
    conn.close()
except Exception as e:
    print(e)
