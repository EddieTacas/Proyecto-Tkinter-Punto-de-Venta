import database

def inspect_schema():
    conn = database.create_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(sales)")
    columns = cur.fetchall()
    print("Columns in sales table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    inspect_schema()
