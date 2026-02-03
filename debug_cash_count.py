import database
import sqlite3
import json

def check_schema():
    print("Checking 'cash_counts' schema...")
    conn = database.create_connection()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(cash_counts)")
        columns = cur.fetchall()
        print("Columns found:")
        found_cols = []
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            found_cols.append(col[1])
            
        required = ['initial_balance', 'system_cards', 'expenses', 'details_json']
        missing = [c for c in required if c not in found_cols]
        
        if missing:
            print(f"MISSING COLUMNS: {missing}")
            return False
        else:
            print("All required columns present.")
            return True
            
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False
    finally:
        conn.close()

def test_insertion():
    print("\nTesting save_cash_count...")
    data = {
        'caja_id': '1',
        'start_time': '2025-01-01 10:00:00',
        'end_time': '2025-01-01 20:00:00',
        'user_id': 'Debug',
        'system_cash': 100.0,
        'counted_cash': 100.0,
        'difference': 0.0,
        'correlative': 'DEBUG-001',
        'initial_balance': 50.0,
        'system_cards': 20.0,
        'expenses': 10.0,
        'counted_cards': 20.0,
        'change_next_day': 5.0,
        'collected_total': 135.0,
        'details_json': json.dumps({'test': True})
    }
    
    try:
        idx = database.save_cash_count(data)
        if idx:
            print(f"Success! Inserted row ID: {idx}")
        else:
            print("Failed to insert row (returned None).")
    except Exception as e:
        print(f"Exception during save_cash_count: {e}")

if __name__ == "__main__":
    if check_schema():
        test_insertion()
    else:
        print("Skipping insertion due to schema mismatch.")
