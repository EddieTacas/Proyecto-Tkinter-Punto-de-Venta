
import database
import sqlite3

def consolidate():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Consolidating Counters for Issuer 1...")
    
    # 1. Get Counters
    cur.execute("SELECT doc_type, current_number FROM correlatives WHERE issuer_id=1 AND doc_type IN ('PROFORMA', 'NOTA DE VENTA')")
    rows = cur.fetchall()
    counters = {r[0]: r[1] for r in rows}
    print(f"Counters: {counters}")
    
    # 2. Get Max Sales
    cur.execute("SELECT MAX(CAST(SUBSTR(document_number, INSTR(document_number, '-') + 1) AS INTEGER)) FROM sales WHERE issuer_id=1 AND (document_type = 'NOTA DE VENTA' OR document_type = 'PROFORMA')")
    row = cur.fetchone()
    max_sale = row[0] if row and row[0] else 0
    print(f"Max Sale in DB: {max_sale}")
    
    # Calculate Target
    vals = list(counters.values()) + [max_sale]
    final_max = max(vals)
    print(f"Target Max: {final_max}")
    
    # 3. Update PROFORMA
    cur.execute("UPDATE correlatives SET current_number = ? WHERE issuer_id=1 AND doc_type='PROFORMA'", (final_max,))
    
    # 4. Delete NOTA DE VENTA
    cur.execute("DELETE FROM correlatives WHERE issuer_id=1 AND doc_type='NOTA DE VENTA'")
    
    conn.commit()
    print("Done. PROFORMA synced to matches max reality.")
    conn.close()

if __name__ == "__main__":
    consolidate()
