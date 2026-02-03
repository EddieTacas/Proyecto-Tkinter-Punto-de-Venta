import json
import os
import time

# Use absolute path relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, 'sales_state.json')

def load_all_states():
    if not os.path.exists(STATE_FILE):
        return {}
    
    # Retry mechanism for robustness
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                # Validate content isn't empty on read
                content = f.read().strip()
                if not content: return {}
                return json.loads(content)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error loading state after retries: {e}")
                return {}
            time.sleep(0.05) # Wait 50ms before retry
    return {}

def save_box_state(caja_id, data):
    states = load_all_states()
    states[str(caja_id)] = data
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(states, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

def clear_box_state(caja_id):
    states = load_all_states()
    if str(caja_id) in states:
        del states[str(caja_id)]
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(states, f, indent=4)
        except Exception as e:
            print(f"Error clearing state: {e}")

def has_pending_items():
    states = load_all_states()
    for caja_id, data in states.items():
        if data.get('cart') and len(data['cart']) > 0:
            return True
    return False

def get_global_reserved_quantity(product_id, exclude_caja_id=None):
    """
    Calcula la cantidad total de un producto que está 'reservada' en los carritos
    de otras cajas (o todas si exclude_caja_id es None).
    """
    states = load_all_states()
    total_reserved = 0.0
    
    for caja_id, data in states.items():
        # Skip our own caja (since we calculate our own addition separately or it's not relevant for 'others')
        if exclude_caja_id is not None and str(caja_id) == str(exclude_caja_id):
            continue
            
        cart = data.get('cart', [])
        for item in cart:
            try:
                # Check ID match (converting to str/int to be safe)
                if str(item.get('id')) == str(product_id):
                    total_reserved += float(item.get('quantity', 0))
            except:
                pass
                
    return total_reserved
