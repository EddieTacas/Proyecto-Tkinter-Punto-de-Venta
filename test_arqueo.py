import database
import config_manager
from datetime import datetime

def test_arqueo_db():
    print("Setting up database...")
    database.setup_database()
    
    caja_id = "CAJA-01"
    
    print("\nTesting get_last_closure (should be None or existing)...")
    last = database.get_last_closure(caja_id)
    print(f"Last closure: {last}")
    
    print("\nTesting save_cash_count...")
    data = {
        'caja_id': caja_id,
        'start_time': '2023-01-01 08:00:00',
        'end_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': 'TEST_USER',
        'system_cash': 100.0,
        'counted_cash': 100.0,
        'difference': 0.0,
        'correlative': 'Cierre-TEST'
    }
    row_id = database.save_cash_count(data)
    print(f"Saved row ID: {row_id}")
    
    print("\nTesting get_last_closure again...")
    last = database.get_last_closure(caja_id)
    print(f"Last closure: {last}")
    assert last is not None
    assert last[8] == 'Cierre-TEST' # correlative is index 8
    
    print("\nTesting get_cash_counts_history...")
    history = database.get_cash_counts_history(caja_id)
    print(f"History count: {len(history)}")
    print(f"First history item: {history[0]}")
    
    print("\nTesting get_sales_total_in_range...")
    total = database.get_sales_total_in_range('2023-01-01 00:00:00', '2099-12-31 23:59:59', caja_id)
    print(f"Total sales: {total}")
    
    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    try:
        test_arqueo_db()
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)
