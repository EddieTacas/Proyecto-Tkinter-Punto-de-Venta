import sqlite3

def fix_polo():
    db_path = 'database.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("--- Searching 'POLO SIN CUELLO' ---")
    cur.execute("SELECT id, name, stock, is_active, typeof(is_active) FROM products WHERE name LIKE '%POLO SIN CUELLO%'")
    rows = cur.fetchall()
    
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Stock: {row[2]}, Active: {row[3]}, Type: {row[4]}")
        
    print("\n--- Listing ALL Active Products ---")
    cur.execute("SELECT id, name, is_active FROM products WHERE is_active = 1 OR is_active = '1'")
    rows = cur.fetchall()
    found = False
    for row in rows:
        if "POLO" in row[1]:
            print(f"FOUND ACTIVE POLO: {row}")
            found = True
            
    if not found:
        print("POLO is NOT in the active list (Good).")
    
    conn.close()

if __name__ == "__main__":
    fix_polo()
