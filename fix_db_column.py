import sqlite3
import os

DB_NAME = 'database.db'

def fix_db():
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        # Check if column exists
        cur.execute("PRAGMA table_info(sale_details)")
        columns = [info[1] for info in cur.fetchall()]
        
        if "original_price" not in columns:
            print("Adding missing column 'original_price' to 'sale_details'...")
            cur.execute("ALTER TABLE sale_details ADD COLUMN original_price REAL DEFAULT 0.0")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'original_price' already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_db()
