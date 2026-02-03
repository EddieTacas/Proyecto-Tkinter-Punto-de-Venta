import database
import sqlite3

try:
    # 1. Add product
    print("Adding dummy product...")
    pid = database.add_product("TEST_DELETE", 10.0, 0.0, "TEST001", "NIU", "Gravada", "Issuer", "Addr", "Cat")
    print(f"Added product ID: {pid}")
    
    # 2. Verify active
    conn = database.create_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_active FROM products WHERE id=?", (pid,))
    active = cur.fetchone()[0]
    print(f"Product Active Before: {active}")
    
    # 3. Delete
    print("Deleting product...")
    database.delete_product(pid)
    
    # 4. Verify inactive
    cur.execute("SELECT is_active FROM products WHERE id=?", (pid,))
    active_after = cur.fetchone()[0]
    print(f"Product Active After: {active_after}")
    conn.close()
    
    if active_after == 0:
        print("SUCCESS: Product was soft-deleted.")
    else:
        print("FAILURE: Product is still active.")

except Exception as e:
    print(f"ERROR: {e}")
