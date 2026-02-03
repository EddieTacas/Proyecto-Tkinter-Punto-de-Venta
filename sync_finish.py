
import database
import sqlite3

def sync_171():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Syncing PROFORMA (Issuer 1) to 171...")
    cur.execute("UPDATE correlatives SET current_number = 171 WHERE issuer_id = 1 AND doc_type = 'PROFORMA'")
    conn.commit()
    print("Done.")
    
    conn.close()

if __name__ == "__main__":
    sync_171()
