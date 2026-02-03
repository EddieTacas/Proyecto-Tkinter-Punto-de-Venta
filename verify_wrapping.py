import textwrap

def test_wrapping():
    products = [
        {'name': 'Short Name', 'price': 10.0, 'stock': 100},
        {'name': 'A Very Long Product Name That Should Be Wrapped', 'price': 25.5, 'stock': 50},
        {'name': 'Another Long Name For Testing Purposes', 'price': 5.0, 'stock': 0}
    ]

    print("--- Testing Product Button Text Wrapping ---")
    for prod in products:
        stock = prod.get('stock', 0)
        wrapped_name = textwrap.fill(prod['name'], width=20)
        text = f"{wrapped_name}\nS/ {prod['price']:.2f}\nStock: {stock}"
        
        print(f"\nOriginal Name: {prod['name']}")
        print("Generated Button Text:")
        print("-" * 20)
        print(text)
        print("-" * 20)

if __name__ == "__main__":
    test_wrapping()
