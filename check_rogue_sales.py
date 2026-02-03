
import database
import sqlite3

def check_rogue():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Checking sales > 171...")
    cur.execute("SELECT id, document_number FROM sales WHERE issuer_id=1 AND document_number > 'NV01-171' ORDER BY id DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"ROGUE SALE: {r}")
        
    print("\nCheck Counters:")
    cur.execute("SELECT doc_type, current_number FROM correlatives WHERE issuer_id=1 AND doc_type IN ('PROFORMA', 'NOTA DE VENTA')")
    for r in cur.fetchall():
        print(f"Counter {r[0]}: {r[1]}")
        
    conn.close()

if __name__ == "__main__":
    check_rogue()
