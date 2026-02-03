
import database
import sqlite3

def diagnose():
    conn = database.create_connection()
    cur = conn.cursor()
    
    with open("diag_output.txt", "w", encoding="utf-8") as f:
        f.write("--- ISSUERS ---\n")
        cur.execute("SELECT id, name, address FROM issuers")
        issuers = {row[0]: f"{row[1]} ({row[2]})" for row in cur.fetchall()}
        for iid, name in issuers.items():
            f.write(f"ID {iid}: {name}\n")
            
        f.write("\n--- SALES (NV01-%) ---\n")
        cur.execute("SELECT id, issuer_id, document_type, document_number FROM sales WHERE document_number LIKE 'NV01-%' ORDER BY id DESC LIMIT 10")
        for row in cur.fetchall():
            iid = row[1]
            iname = issuers.get(iid, "Unknown")
            f.write(f"Sale {row[0]}: Issuer={iid} ({iname}), Type='{row[2]}', DocNum='{row[3]}'\n")
            
        f.write("\n--- CORRELATIVES TABLE ---\n")
        cur.execute("SELECT issuer_id, doc_type, series, current_number FROM correlatives")
        for row in cur.fetchall():
            iid = row[0]
            iname = issuers.get(iid, "Unknown")
            f.write(f"Corr: Issuer={iid} ({iname}), Type='{row[1]}', Series='{row[2]}', Num={row[3]}\n")
        
    conn.close()

if __name__ == "__main__":
    diagnose()
