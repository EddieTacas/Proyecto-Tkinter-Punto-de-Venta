
import database
import sqlite3

def force_reset():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Force Resetting Invoice Counter for PROFORMA (Issuer 1) to 167...")
    cur.execute("UPDATE correlatives SET current_number = 167 WHERE issuer_id = 1 AND doc_type = 'PROFORMA'")
    conn.commit()
    print("Done.")
    
    conn.close()

if __name__ == "__main__":
    force_reset()
