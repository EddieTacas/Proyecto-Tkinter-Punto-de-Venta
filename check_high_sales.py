
import database
import sqlite3

def check_high():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Checking sales > 160...")
    cur.execute("SELECT id, document_number FROM sales WHERE issuer_id=1 AND document_number > 'NV01-160' ORDER BY id DESC")
    rows = cur.fetchall()
    for r in rows:
        print(r)
        
    conn.close()

if __name__ == "__main__":
    check_high()
