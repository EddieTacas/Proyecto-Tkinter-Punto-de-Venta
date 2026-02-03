
import database
import sqlite3

def fix_proforma():
    conn = database.create_connection()
    cur = conn.cursor()
    
    # Get all issuers
    cur.execute("SELECT id FROM issuers")
    issuer_ids = [r[0] for r in cur.fetchall()]
    
    for iid in issuer_ids:
        print(f"Processing Issuer {iid}...")
        
        # Check NOTA DE VENTA and PROFORMA in CORRELATIVES
        cur.execute("SELECT doc_type, current_number, series FROM correlatives WHERE issuer_id = ? AND doc_type IN ('NOTA DE VENTA', 'PROFORMA')", (iid,))
        rows = cur.fetchall()
        
        if not rows:
            continue
            
        print(f"  Found rows: {rows}")
        
        # Calculate true max
        max_num = 0
        series = "NV01" # Default
        found_types = []
        
        for r in rows:
            dtype = r[0]
            num = r[1]
            if r[2] and r[2].startswith("NV"):
                series = r[2] # Capture the series used
            
            if num > max_num:
                max_num = num
            found_types.append(dtype)
            
        # We want to keep/create PROFORMA with max_num
        # And delete NOTA DE VENTA
        
        if "PROFORMA" in found_types or "NOTA DE VENTA" in found_types:
            print(f"  Consolidating to PROFORMA: Max={max_num}, Series={series}")
            
            # 1. Delete both to clear conflicts
            cur.execute("DELETE FROM correlatives WHERE issuer_id = ? AND doc_type IN ('NOTA DE VENTA', 'PROFORMA')", (iid,))
            
            # 2. Insert PROFORMA
            cur.execute("INSERT INTO correlatives (issuer_id, doc_type, series, current_number) VALUES (?, ?, ?, ?)", (iid, "PROFORMA", series, max_num))
            
            conn.commit()
            print("  Updated.")

    conn.close()

if __name__ == "__main__":
    fix_proforma()
