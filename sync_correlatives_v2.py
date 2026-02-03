
import database
import sqlite3

def sync():
    print("Starting Correlative Sync V2...")
    conn = database.create_connection()
    cur = conn.cursor()
    
    # 1. Get all issuers
    cur.execute("SELECT id, name FROM issuers")
    issuers = cur.fetchall()
    
    # Mapping Display -> Internal (used in config)
    # If the DB has 'NOTA DE VENTA', we treat it as 'PROFORMA' for config
    type_map = {
        "NOTA DE VENTA": "PROFORMA",
        "PROFORMA": "PROFORMA", 
        "BOLETA": "BOLETA",
        "BOLETA DE VENTA ELECTRÓNICA": "BOLETA",
        "FACTURA": "FACTURA",
        "FACTURA ELECTRÓNICA": "FACTURA"
    }

    # Fetch all max numbers from sales grouping by issuer and doc_type
    sql = """
        SELECT issuer_id, document_type, MAX(CAST(SUBSTR(document_number, INSTR(document_number, '-') + 1) AS INTEGER)), MAX(document_number)
        FROM sales
        GROUP BY issuer_id, document_type
    """
    cur.execute(sql)
    rows = cur.fetchall()
    
    updates = {} # Key: (issuer_id, internal_type) -> (max_num, series)
    
    for row in rows:
        issuer_id = row[0]
        raw_type = row[1]
        max_num = row[2]
        max_doc = row[3] # e.g. NV01-160
        
        if not max_num: continue
        
        internal_type = type_map.get(raw_type, raw_type)
        
        # Extract series
        series = "0001"
        if max_doc and '-' in max_doc:
            series = max_doc.split('-')[0]
            
        print(f"Found Sales: Issuer={issuer_id}, Type={raw_type}, Max={max_num} (Series={series}) -> Maps to {internal_type}")
        
        # We want the HIGHEST number for this internal type
        curr = updates.get((issuer_id, internal_type), (0, ""))
        if max_num > curr[0]:
            updates[(issuer_id, internal_type)] = (max_num, series)

    # Apply updates
    for (issuer_id, internal_type), (max_num, series) in updates.items():
        print(f"Updating Correlatives: Issuer={issuer_id}, Type={internal_type} -> Series={series}, Num={max_num}")
        database.set_correlative(issuer_id, internal_type, series, max_num)
        
    conn.close()
    print("Sync V2 Completed.")

if __name__ == "__main__":
    sync()
