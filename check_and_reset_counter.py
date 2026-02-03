
import database
import sqlite3

def check_and_reset():
    conn = database.create_connection()
    cur = conn.cursor()
    
    # Check max sales for Issuer 1 PROFORMA/NOTA DE VENTA
    # We consolidate to 'PROFORMA' internally now (per my Fix V3), but sales history has 'NOTA DE VENTA'
    # Wait, my Fix V3 deleted 'NOTA DE VENTA' from *correlatives*.
    # Sales table still has 'NOTA DE VENTA' strings in document_type column likely.
    
    # 1. Get Max from Sales
    print("Finding Max Sale Number...")
    # Get all sales types to be sure
    cur.execute("SELECT issuer_id, document_type, document_number FROM sales WHERE issuer_id = 1 ORDER BY id DESC LIMIT 5")
    for r in cur.fetchall():
        print(f"Latest Sale: {r}")
        
    cur.execute("""
        SELECT MAX(CAST(SUBSTR(document_number, INSTR(document_number, '-') + 1) AS INTEGER))
        FROM sales
        WHERE issuer_id = 1 AND document_number LIKE 'NV01-%'
    """)
    row = cur.fetchone()
    max_num = row[0] if row and row[0] else 0
    print(f"Max Number detected in Sales History: {max_num}")
    
    # 2. Get Current Config
    cur.execute("SELECT current_number FROM correlatives WHERE issuer_id = 1 AND doc_type = 'PROFORMA'")
    conf_row = cur.fetchone()
    conf_num = conf_row[0] if conf_row else -1
    print(f"Current Config Number in DB: {conf_num}")
    
    # 3. Reset if needed
    if max_num > 0 and conf_num > max_num:
        print(f"Config ({conf_num}) is ahead of History ({max_num}). Resetting to {max_num}...")
        cur.execute("UPDATE correlatives SET current_number = ? WHERE issuer_id = 1 AND doc_type = 'PROFORMA'", (max_num,))
        conn.commit()
        print("Reset Complete.")
    else:
        print("Config is consistent (or behind). No reset needed.")
        
    conn.close()

if __name__ == "__main__":
    check_and_reset()
