
import database
import sqlite3

def reset_171():
    conn = database.create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE correlatives SET current_number = 171 WHERE issuer_id = 1 AND doc_type = 'PROFORMA'")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_171()
