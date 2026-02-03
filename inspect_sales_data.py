import sqlite3


def inspect_data():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    print("--- SALES ---")
    cur.execute("SELECT id, total_amount, sale_date FROM sales ORDER BY id DESC LIMIT 5")
    sales = cur.fetchall()
    for s in sales:
        print(s)
        
    print("\n--- SALE DETAILS (for last 5 sales) ---")
    if sales:
        sale_ids = [str(s[0]) for s in sales]
        query = f"""
            SELECT sale_id, product_id, quantity_sold, price_per_unit, subtotal, original_price 
            FROM sale_details 
            WHERE sale_id IN ({','.join(sale_ids)})
        """
        cur.execute(query)
        details = cur.fetchall()
        for d in details:
            print(d)
            
    conn.close()

if __name__ == "__main__":
    inspect_data()
