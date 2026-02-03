import sqlite3
import os

def fix_stock():
    db_file = 'database.db'
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    product_name = "anillo de acero"
    
    # Check current stock
    cur.execute("SELECT id, name, stock FROM products WHERE name LIKE ?", (f"%{product_name}%",))
    products = cur.fetchall()
    
    if not products:
        print(f"No product found matching '{product_name}'")
        return

    for p in products:
        p_id, name, stock = p
        print(f"Found product: ID={p_id}, Name='{name}', Current Stock={stock}")
        
        # Update stock to -1 as requested
        new_stock = -1.0
        cur.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, p_id))
        print(f"Updated stock for '{name}' to {new_stock}")
        
    conn.commit()
    conn.close()
    print("Stock correction complete.")

if __name__ == "__main__":
    fix_stock()
