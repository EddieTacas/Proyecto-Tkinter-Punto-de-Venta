import sqlite3
import os

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

def test_location_hypothesis():
    print("\n--- TEST LOCATION HYPOTHESIS ---")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Clean up test data
        cur.execute("DELETE FROM issuers WHERE ruc = '88888888888'")
        conn.commit()
        
        print("Inserting Branch 1 (Addr='Calle 1', Dist='Lima')...")
        cur.execute("""
            INSERT INTO issuers (name, ruc, address, district, province, department) 
            VALUES ('TEST LOCATION', '88888888888', 'Calle 1', 'Lima', 'Lima', 'Lima')
        """)
        conn.commit()
        print("Branch 1 inserted.")
        
        print("Inserting Branch 2 (Addr='Calle 1', Dist='Miraflores')...")
        # Same Address, Different District
        try:
            cur.execute("""
                INSERT INTO issuers (name, ruc, address, district, province, department) 
                VALUES ('TEST LOCATION', '88888888888', 'Calle 1', 'Miraflores', 'Lima', 'Lima')
            """)
            conn.commit()
            print("Branch 2 inserted (Unexpected if constraint is strictly (name, ruc, address)).")
        except sqlite3.IntegrityError as e:
            print(f"Branch 2 FAILED as expected: {e}")
            
        # Clean up
        cur.execute("DELETE FROM issuers WHERE ruc = '88888888888'")
        conn.commit()
        
        conn.close()
        
    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    test_location_hypothesis()
