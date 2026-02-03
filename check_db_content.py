
import database
import sqlite3

def check():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("--- DISTINCT DOCUMENT TYPES & COUNTS ---")
    cur.execute("SELECT document_type, COUNT(*), MAX(document_number) FROM sales GROUP BY document_type")
    for row in cur.fetchall():
        print(f"Type: '{row[0]}', Count: {row[1]}, MaxNum: {row[2]}")
        
    print("\n--- SAMPLE NUMBERS FOR NOTA DE VENTA/PROFORMA ---")
    cur.execute("SELECT document_number FROM sales WHERE document_type IN ('NOTA DE VENTA', 'PROFORMA') ORDER BY id DESC LIMIT 5")
    for row in cur.fetchall():
        print(f"Num: {row[0]}")
        
    conn.close()

if __name__ == "__main__":
    check()
