import sqlite3
import os

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

def check_schema():
    print("--- SCHEMA ---")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issuers'")
        result = cur.fetchone()
        if result:
            print(result[0])
        else:
            print("Table 'issuers' not found.")
        conn.close()
    except Exception as e:
        print(f"Error checking schema: {e}")

def test_insertion():
    print("\n--- TEST INSERTION ---")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Clean up test data if exists
        cur.execute("DELETE FROM issuers WHERE ruc = '99999999999'")
        conn.commit()
        
        print("Inserting Branch 1...")
        cur.execute("""
            INSERT INTO issuers (name, ruc, address, commercial_name) 
            VALUES ('TEST EMPRESA', '99999999999', 'DIRECCION 1', 'COMERCIAL 1')
        """)
        conn.commit()
        print("Branch 1 inserted.")
        
        print("Inserting Branch 2 (Same Name/RUC, Diff Address)...")
        cur.execute("""
            INSERT INTO issuers (name, ruc, address, commercial_name) 
            VALUES ('TEST EMPRESA', '99999999999', 'DIRECCION 2', 'COMERCIAL 2')
        """)
        conn.commit()
        print("Branch 2 inserted.")
        
        # Clean up
        cur.execute("DELETE FROM issuers WHERE ruc = '99999999999'")
        conn.commit()
        print("Test data cleaned up.")
        
        conn.close()
        print("SUCCESS: Multiple branches allowed.")
        
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    check_schema()
    test_insertion()
