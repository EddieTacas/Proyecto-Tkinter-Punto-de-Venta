import sqlite3

db_path = 'c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db'

def restore_data():
    print("Restoring data...")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get columns from backup table
        cur.execute("PRAGMA table_info(_issuers_old_v13)")
        columns_info = cur.fetchall()
        columns = [info[1] for info in columns_info]
        columns_str = ", ".join(columns)
        print(f"Columns: {columns_str}")
        
        # Insert data
        sql = f"INSERT INTO issuers ({columns_str}) SELECT {columns_str} FROM _issuers_old_v13"
        cur.execute(sql)
        rows_affected = cur.rowcount
        print(f"Restored {rows_affected} rows.")
        
        conn.commit()
        
        # Verify restoration
        cur.execute("SELECT count(*) FROM issuers")
        count = cur.fetchone()[0]
        if count == rows_affected and count > 0:
            print("Restoration verified. Dropping backup table...")
            cur.execute("DROP TABLE _issuers_old_v13")
            conn.commit()
            print("Backup table dropped.")
        else:
            print("Restoration verification failed. Backup table NOT dropped.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_data()
