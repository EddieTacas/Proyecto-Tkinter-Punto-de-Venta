
import state_manager
try:
    qty = state_manager.get_global_reserved_quantity(47, exclude_caja_id=2)
    print(f"Reserved Quantity for ID 47 (exclude 2): {qty}")
except Exception as e:
    print(f"Error: {e}")
