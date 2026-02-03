
import database
import sqlite3

def test_inc():
    conn = database.create_connection()
    cur = conn.cursor()
    
    # 1. Read Current
    cur.execute("SELECT current_number FROM correlatives WHERE issuer_id=1 AND doc_type='PROFORMA'")
    start_num = cur.fetchone()[0]
    print(f"Start: {start_num}") # Expect 171
    
    conn.close()
    
    # 2. Increment (Simulate Sale)
    print("Calling get_next_correlative...")
    s, n = database.get_next_correlative(1, "PROFORMA")
    print(f"Returned: {n} (Series {s})") # Expect 172
    
    # 3. Read Current (Simulate Reset)
    # Using get_correlative (which opens new conn)
    print("Calling get_correlative...")
    s2, n2 = database.get_correlative(1, "PROFORMA")
    print(f"Correlative Read: {n2}") # Expect 172
    
    if n2 == n:
        print("SUCCESS: Persistence confirmed.")
    else:
        print(f"FAILURE: Read {n2} but updated to {n}.")

if __name__ == "__main__":
    test_inc()
