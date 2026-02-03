import sqlite3

def fix_polo():
    db_path = 'database.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("--- Buscando 'POLO SIN CUELLO' ---")
    cur.execute("SELECT id, name, stock, is_active FROM products WHERE name LIKE '%POLO SIN CUELLO%'")
    rows = cur.fetchall()
    
    if not rows:
        print("No se encontraron productos.")
        return

    print(f"Encontrados {len(rows)} productos:")
    for row in rows:
        print(row)
        pid = row[0]
        name = row[1]
        
        print(f"Intentando desactivar (soft delete) ID: {pid}...")
        try:
            cur.execute("UPDATE products SET is_active = 0 WHERE id = ?", (pid,))
            if cur.rowcount > 0:
                print("  -> Actualización exitosa (rowcount > 0).")
            else:
                print("  -> ERROR: rowcount es 0.")
        except Exception as e:
            print(f"  -> ERROR EXCEPCION: {e}")

    conn.commit()
    
    print("\n--- Verificación Final ---")
    cur.execute("SELECT id, name, stock, is_active FROM products WHERE name LIKE '%POLO SIN CUELLO%'")
    rows_after = cur.fetchall()
    for row in rows_after:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    fix_polo()
