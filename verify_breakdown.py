class MockLabel:
    def __init__(self, name):
        self.name = name
        self.text = ""
    
    def config(self, text=None):
        if text is not None:
            self.text = text
            print(f"[{self.name}] Updated text: '{self.text}'")

class MockSalesTouchView:
    def __init__(self):
        self.cart = []
        self.total = 0.0
        self.surcharge_label = MockLabel("Surcharge Label")
        self.discount_label = MockLabel("Discount Label")
        self.total_label = MockLabel("Total Label")
        self.total_items_label = MockLabel("Items Label")

    def update_total(self):
        self.total = sum(item['subtotal'] for item in self.cart)
        
        # Calculate Base Total (Original Price * Quantity)
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        
        difference = self.total - base_total
        
        print(f"Total: {self.total}, Base Total: {base_total}, Difference: {difference}")
        
        # Update Labels
        if difference > 0.001: # Surcharge
            self.surcharge_label.config(text=f"Sobreprecio: S/ {difference:.2f}")
            self.discount_label.config(text="")
        elif difference < -0.001: # Discount
            self.surcharge_label.config(text="")
            self.discount_label.config(text=f"Descuento: S/ {abs(difference):.2f}")
        else:
            self.surcharge_label.config(text="")
            self.discount_label.config(text="")
            
        self.total_label.config(text=f"Total Neto: S/ {self.total:.2f}")
        
        # Update Items Count
        total_qty = sum(item['quantity'] for item in self.cart)
        if total_qty.is_integer():
             self.total_items_label.config(text=f"Items: {int(total_qty)}")
        else:
             self.total_items_label.config(text=f"Items: {total_qty:.2f}")

def test_breakdown():
    view = MockSalesTouchView()
    
    print("\n--- Test 1: Normal Item (No Difference) ---")
    # Item: Price 10, Original 10, Qty 1
    view.cart = [{'price': 10.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 10.0}]
    view.update_total()
    
    print("\n--- Test 2: Surcharge ---")
    # Item: Price 12, Original 10, Qty 1 (Surcharge 2)
    view.cart = [{'price': 12.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 12.0}]
    view.update_total()
    
    print("\n--- Test 3: Discount ---")
    # Item: Price 8, Original 10, Qty 1 (Discount 2)
    view.cart = [{'price': 8.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 8.0}]
    view.update_total()
    
    print("\n--- Test 4: Mixed Items ---")
    # Item 1: Price 12, Original 10 (Surcharge 2)
    # Item 2: Price 15, Original 20 (Discount 5)
    # Net: Discount 3
    view.cart = [
        {'price': 12.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 12.0},
        {'price': 15.0, 'original_price': 20.0, 'quantity': 1, 'subtotal': 15.0}
    ]
    view.update_total()

if __name__ == "__main__":
    test_breakdown()
