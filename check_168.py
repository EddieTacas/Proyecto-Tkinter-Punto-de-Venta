
import database
import sqlite3

def check_168():
    conn = database.create_connection()
    cur = conn.cursor()
    
    print("Checking for NV01-168...")
    cur.execute("SELECT * FROM sales WHERE document_number = 'NV01-168'")
    row = cur.fetchone()
    if row:
        print("FOUND NV01-168 in Sales!")
        print(row)
    else:
        print("NV01-168 NOT found in Sales.")
        
    print("\nChecking PROFORMA Counter...")
    cur.execute("SELECT current_number FROM correlatives WHERE issuer_id = 1 AND doc_type = 'PROFORMA'")
    row2 = cur.fetchone()
    print(f"Current Config Number: {row2[0] if row2 else 'None'}")
    
    conn.close()

if __name__ == "__main__":
    check_168()
