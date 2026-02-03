import sqlite3
import os

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

def test_fix():
    print("\n--- TEST FIX ---")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Clean up test data
        cur.execute("DELETE FROM issuers WHERE ruc = '88888888888'")
        conn.commit()
        
        print("Inserting Branch 1...")
        cur.execute("""
            INSERT INTO issuers (name, ruc, address, district, province, department) 
            VALUES ('TEST LOCATION', '88888888888', 'Calle 1', 'Lima', 'Lima', 'Lima')
        """)
        conn.commit()
        
        print("Inserting Branch 2 (Same Address, Diff District)...")
        # This should now SUCCEED
        try:
            cur.execute("""
                INSERT INTO issuers (name, ruc, address, district, province, department) 
                VALUES ('TEST LOCATION', '88888888888', 'Calle 1', 'Miraflores', 'Lima', 'Lima')
            """)
            conn.commit()
            print("Branch 2 inserted SUCCESSFULLY.")
        except sqlite3.IntegrityError as e:
            print(f"Branch 2 FAILED: {e}")
            raise e
            
        # Clean up
        cur.execute("DELETE FROM issuers WHERE ruc = '88888888888'")
        conn.commit()
        
        conn.close()
        print("VERIFICATION SUCCESSFUL: Multiple branches allowed.")
        
    except Exception as e:
        print(f"VERIFICATION FAILED: {e}")

if __name__ == "__main__":
    test_fix()
