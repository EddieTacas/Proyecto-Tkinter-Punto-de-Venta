class MockLabel:
    def __init__(self, name):
        self.name = name
        self.text = ""
    
    def config(self, text=None):
        if text is not None:
            self.text = text
            print(f"[{self.name}] Updated text: '{self.text}'")

class MockSalesView:
    def __init__(self):
        self.cart = []
        self.total = 0.0
        self.total_label = MockLabel("Total Label (Left Pane)")
        self.footer_surcharge_label = MockLabel("Footer Surcharge")
        self.footer_discount_label = MockLabel("Footer Discount")
        self.footer_total_label = MockLabel("Footer Net Total")
        self.footer_items_label = MockLabel("Footer Items")
        self.change_label = MockLabel("Change Label")
        self.amount_paid_var = type('obj', (object,), {'get': lambda: 0.0})
        self.amount_paid_var2 = type('obj', (object,), {'get': lambda: 0.0})

    def calculate_change(self):
        pass
    
    def update_ticket_preview(self):
        pass

    def update_total(self):
        self.total = sum(item['subtotal'] for item in self.cart)
        self.total_label.config(text=f"Total: S/ {self.total:.2f}")
        
        # --- Calculate Breakdown for Footer ---
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        difference = self.total - base_total
        
        # Update Footer Labels
        if difference > 0.001: # Surcharge
            self.footer_surcharge_label.config(text=f"Sobreprecio: S/ {difference:.2f}")
            self.footer_discount_label.config(text="")
        elif difference < -0.001: # Discount
            self.footer_surcharge_label.config(text="")
            self.footer_discount_label.config(text=f"Descuento: S/ {abs(difference):.2f}")
        else:
            self.footer_surcharge_label.config(text="")
            self.footer_discount_label.config(text="")
            
        self.footer_total_label.config(text=f"Total Neto: S/ {self.total:.2f}")
        
        # Update Items Count
        total_qty = sum(item['quantity'] for item in self.cart)
        if total_qty.is_integer():
             self.footer_items_label.config(text=f"Items: {int(total_qty)}")
        else:
             self.footer_items_label.config(text=f"Items: {total_qty:.2f}")

        self.calculate_change()
        self.update_ticket_preview()

def test_manual_breakdown():
    view = MockSalesView()
    
    print("\n--- Test 1: Normal Item (No Difference) ---")
    view.cart = [{'price': 10.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 10.0}]
    view.update_total()
    
    print("\n--- Test 2: Surcharge ---")
    view.cart = [{'price': 12.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 12.0}]
    view.update_total()
    
    print("\n--- Test 3: Discount ---")
    view.cart = [{'price': 8.0, 'original_price': 10.0, 'quantity': 1, 'subtotal': 8.0}]
    view.update_total()

if __name__ == "__main__":
    test_manual_breakdown()
