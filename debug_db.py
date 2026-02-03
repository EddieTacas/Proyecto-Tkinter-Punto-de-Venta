import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    print("--- Searching for products with 'CHOMPA' ---")
    cursor.execute("SELECT id, name, stock, is_active FROM products WHERE name LIKE '%CHOMPA%'")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    print("\n--- Searching for recent products (ID > last 10) ---")
    cursor.execute("SELECT MAX(id) from products")
    max_id = cursor.fetchone()[0]
    if max_id:
        cursor.execute("SELECT id, name, stock, is_active FROM products WHERE id > ?", (max_id - 10,))
        rows = cursor.fetchall()
        for row in rows:
            print(row)

    conn.close()
except Exception as e:
    print(e)
