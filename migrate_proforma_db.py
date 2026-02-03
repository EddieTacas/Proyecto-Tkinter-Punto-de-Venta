import sqlite3
import os

DB_FILE = 'database.db'

def migrate_database():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        print("Migrating 'sales' table...")
        cur.execute("UPDATE sales SET document_type = 'NOTA DE VENTA' WHERE document_type = 'PROFORMA'")
        print(f"Updated {cur.rowcount} rows in 'sales'.")

        print("Migrating 'correlatives' table...")
        cur.execute("UPDATE correlatives SET doc_type = 'NOTA DE VENTA' WHERE doc_type = 'PROFORMA'")
        print(f"Updated {cur.rowcount} rows in 'correlatives'.")

        conn.commit()
        print("Migration completed successfully.")

    except sqlite3.Error as e:
        print(f"Error migrating database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()
