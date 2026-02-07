
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import database
import json
import os
from datetime import datetime

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, COLOR_BUTTON_PRIMARY, COLOR_BUTTON_SECONDARY, FONT_FAMILY

COLOR_PRIMARY_DARK = COLOR_PRIMARY
COLOR_SECONDARY_DARK = COLOR_SECONDARY
COLOR_ACCENT_BLUE = COLOR_ACCENT
COLOR_TEXT_LIGHT = COLOR_TEXT

GROUP_ORDER_FILE = 'group_order.json'
PRODUCT_ORDER_FILE = 'product_order.json'

class TouchMovementDialog(ttk.Toplevel):
    def __init__(self, parent, move_type, issuer_id, address, on_complete=None):
        super().__init__(parent)
        self.title(f"Registro de {move_type}")
        self.move_type = move_type
        self.issuer_id = issuer_id
        self.address = address
        self.parent_view = parent # Explicitly store parent to access methods later
        self.on_complete = on_complete
        self.state('zoomed')
        self.attributes('-topmost', True)
        self.configure(background=COLOR_PRIMARY_DARK)
        
        self.grab_set()
        self.focus_set()
        
        # Data
        self.cart = []
        self.products = {}
        self.product_order = {}
        self.product_colors = {}
        self.group_mapping = {} # Name -> ID
        self.code_map = {} # Code -> Product Data
        
        # UI Setup
        self.columnconfigure(0, weight=7) # Products
        self.columnconfigure(1, weight=3) # Cart
        self.rowconfigure(0, weight=1)
        
        style = ttk.Style.get_instance()
        style.configure('Touch.TButton', font=(FONT_FAMILY, 10, 'bold'))
        
        self.setup_left_pane()
        self.setup_right_pane()
        
        self.load_data()
        
    def load_data(self):
        # Load Products
        # Note: We need issuer_name/address to filter products via database.get_all_products?
        # The parent passed issuer_id and address. We need to find the issuer name?
        # Or database.get_all_products takes name/address.
        # Let's fetch issuer name from DB.
        
        conn = database.create_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM issuers WHERE id=?", (self.issuer_id,))
        row = cur.fetchone()
        conn.close()
        
        issuer_name = row[0] if row else "TODOS"
        
        raw_products = database.get_all_products(issuer_name, self.address)
        self.products = {}
        for p in raw_products:
             # id, name, price, stock, code, um, group_id, group_name ...
             # Mapping might vary, check database.py get_all_products
             # Assuming standard structure
             p_data = {
                'id': p[0],
                'name': p[1],
                'price': p[2],
                'stock': p[3],
                'um': p[5],
                'group_id': None, # Not returned explicitly separate from category name
                'group_name': p[9] if len(p) > 9 else "Sin Grupo" # Category is at index 9
             }
             self.products[p[1]] = p_data
             
             # Populate Code Map
             if p[4]: # if code exists
                 self.code_map[str(p[4]).strip()] = p_data
             
        self.load_group_order()
        self.load_product_order()
        self.populate_groups()
        
    def load_group_order(self):
        if os.path.exists(GROUP_ORDER_FILE):
            with open(GROUP_ORDER_FILE, 'r') as f:
                self.group_order_data = json.load(f) # List of lists (pages)
        else:
            self.group_order_data = []

    def load_product_order(self):
        if os.path.exists(PRODUCT_ORDER_FILE):
             try:
                data = json.load(f)
                self.product_order = data.get('order', {})
                self.product_colors = data.get('colors', {})
             except:
                pass
                
    def setup_left_pane(self):
        left_frame = ttk.Frame(self, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.rowconfigure(3, weight=1) # Product grid is now at row 3
        left_frame.columnconfigure(0, weight=1)
        
        # Scan Entry
        scan_frame = ttk.Frame(left_frame)
        scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(scan_frame, text="ESCANEAR:", font=(FONT_FAMILY, 12, "bold")).pack(side="left", padx=(0, 5))
        self.scan_entry = ttk.Entry(scan_frame, font=(FONT_FAMILY, 14))
        self.scan_entry.pack(side="left", fill="x", expand=True)
        self.scan_entry.bind("<Return>", self.handle_scan)
        self.scan_entry.bind("<KeyRelease>", self.check_scan_input) # Smart Scan
        # Keep focus
        self.scan_entry.focus_set()
        def keep_focus(e): 
            if e.widget == self or e.widget == left_frame: # Only re-focus if clicking background, not other inputs
                self.scan_entry.focus_set()
        self.bind("<Button-1>", keep_focus) 

        # Groups Header
        ttk.Label(left_frame, text=f"GRUPOS - {self.move_type}", font=(FONT_FAMILY, 14, "bold"), background=COLOR_ACCENT_BLUE, foreground=COLOR_TEXT_LIGHT, anchor="center").grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        # Group Grid Frame
        self.groups_frame = ttk.Frame(left_frame)
        self.groups_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        # 7 columns for groups
        for i in range(7): self.groups_frame.columnconfigure(i, weight=1)
        
        # Products Grid
        self.products_frame = ttk.Frame(left_frame)
        # Products Grid Container (Scrollable)
        self.products_container = ttk.Frame(left_frame)
        self.products_container.grid(row=3, column=0, sticky="nsew")
        
        # Scrollbar
        self.chk_scrollbar = ttk.Scrollbar(self.products_container, orient="vertical")
        self.chk_scrollbar.pack(side="right", fill="y")
        
        # Canvas
        self.products_canvas = tk.Canvas(
            self.products_container, 
            bd=0, 
            highlightthickness=0,
            yscrollcommand=self.chk_scrollbar.set,
            bg=COLOR_PRIMARY_DARK # Match parent bg or theme.
        )
        self.products_canvas.pack(side="left", fill="both", expand=True)
        
        self.chk_scrollbar.config(command=self.products_canvas.yview)
        
        # Inner Frame
        self.products_frame = ttk.Frame(self.products_canvas)
        self.products_window = self.products_canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        
        # Bindings for Scroll
        def _on_frame_configure(event):
            self.products_canvas.configure(scrollregion=self.products_canvas.bbox("all"))
            
        def _on_canvas_configure(event):
            # width = event.width
            self.products_canvas.itemconfig(self.products_window, width=event.width)
            
        self.products_frame.bind("<Configure>", _on_frame_configure)
        self.products_canvas.bind("<Configure>", _on_canvas_configure)
        
        # Mousewheel
        def _on_mousewheel(event):
            self.products_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        # Bind only when hovering
        def _bind_mousewheel(event):
            self.products_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_mousewheel(event):
            self.products_canvas.unbind_all("<MouseWheel>")
            
        self.products_canvas.bind("<Enter>", _bind_mousewheel)
        self.products_canvas.bind("<Leave>", _unbind_mousewheel)
        
        # Group Pagination State
        self.current_group_page = 0
        self.groups_per_page = 14 # 2 rows * 7 cols
        self.all_groups = []

    def populate_groups(self):
        # Filter groups from products
        groups = set()
        for p in self.products.values():
            g = p.get('group_name', 'Sin Grupo')
            if g: groups.add(g)
        
        self.all_groups = sorted(list(groups))
        self.update_group_grid()
            
    def update_group_grid(self):
        for w in self.groups_frame.winfo_children(): w.destroy()
        
        start = self.current_group_page * self.groups_per_page
        end = start + self.groups_per_page
        page_groups = self.all_groups[start:end]
        
        # Navigation Buttons (if needed)
        # We can place them if total > 14
        if len(self.all_groups) > self.groups_per_page:
             nav_frame = ttk.Frame(self.groups_frame)
             nav_frame.grid(row=2, column=0, columnspan=7, pady=5)
             
             if self.current_group_page > 0:
                 ttk.Button(nav_frame, text="<< Anterior", command=self.prev_group_page, bootstyle="secondary").pack(side="left", padx=10)
                 
             if end < len(self.all_groups):
                 ttk.Button(nav_frame, text="Siguiente >>", command=self.next_group_page, bootstyle="secondary").pack(side="left", padx=10)

        # Draw Grid (2 rows x 7 cols)
        for i, g in enumerate(page_groups):
            r = i // 7
            c = i % 7
            
            # Highlight Active Group? Maybe store active group and style differently.
            # Simple button for now.
            btn = ttk.Button(self.groups_frame, text=g, command=lambda g=g: self.show_products(g), bootstyle="info-outline")
            btn.grid(row=r, column=c, sticky="ew", padx=2, pady=2)
            
        # Select first group by default on first load?
        if self.current_group_page == 0 and page_groups and not hasattr(self, 'first_loaded'):
             self.show_products(page_groups[0])
             self.first_loaded = True

    def prev_group_page(self):
        if self.current_group_page > 0:
            self.current_group_page -= 1
            self.update_group_grid()

    def next_group_page(self):
        if (self.current_group_page + 1) * self.groups_per_page < len(self.all_groups):
            self.current_group_page += 1
            self.update_group_grid()
            
    def show_products(self, group_name):
        for w in self.products_frame.winfo_children(): w.destroy()
        
        # Filter products
        items = [p for p in self.products.values() if p.get('group_name') == group_name]
        
        # Grid Layout
        ROW_SIZE = 4
        for i, item in enumerate(items):
            r = i // ROW_SIZE
            c = i % ROW_SIZE
            
            # Custom Color
            color = self.product_colors.get(str(item['id']), '#E0E0E0')
            
            # Button with Price
            btn = tk.Button(
                self.products_frame,
                text=f"{item['name']}\nPrecio: S/ {item['price']:.2f}\nStock: {item['stock']:.2f}",
                bg=color,
                fg="black" if self._is_light(color) else "white",
                font=(FONT_FAMILY, 10, "bold"),
                wraplength=120,
                command=lambda p=item: self.add_to_cart(p)
            )
            btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
            
        for i in range(ROW_SIZE):
            self.products_frame.columnconfigure(i, weight=1)
            
    def _is_light(self, hex_color):
        if not hex_color.startswith('#'): return True
        hex_color = hex_color.lstrip('#')
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq >= 128
        except:
            return True

    def setup_right_pane(self):
        right_frame = ttk.Frame(self, padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right_frame, text="CARRITO", font=(FONT_FAMILY, 14, "bold"), anchor="center").pack(fill="x", pady=(0, 10))
        
        # Treeview (Added Precio column)
        cols = ("Producto", "Cant", "Precio", "Subtotal")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", bootstyle="primary")
        self.tree.heading("Producto", text="Producto")
        self.tree.heading("Cant", text="Cnt")
        self.tree.heading("Precio", text="P.Unit")
        self.tree.heading("Subtotal", text="Sub")
        
        self.tree.column("Producto", width=120, stretch=True)
        self.tree.column("Cant", width=40, anchor="center", stretch=False)
        self.tree.column("Precio", width=60, anchor="center", stretch=False)
        self.tree.column("Subtotal", width=60, anchor="center", stretch=False)
        
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind("<Double-1>", self.edit_qty)
        
        # Total
        self.total_label = ttk.Label(right_frame, text="Total: S/ 0.00", font=(FONT_FAMILY, 16, "bold"), bootstyle="inverse-success")
        self.total_label.pack(fill="x", pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="CONFIRMAR", command=self.confirm_movement, bootstyle="success").pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(btn_frame, text="ELIMINAR", command=self.delete_item, bootstyle="warning").pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(btn_frame, text="CANCELAR", command=self.destroy, bootstyle="danger").pack(side="right", fill="x", expand=True, padx=2)
        
    def delete_item(self):
        selected_item = self.tree.focus()
        if not selected_item: return
        
        idx = self.tree.index(selected_item)
        self.cart.pop(idx)
        self.update_tree()

    def add_to_cart(self, product):
        # Check if exists
        for i, item in enumerate(self.cart):
            if item['id'] == product['id']:
                item['quantity'] += 1
                item['subtotal'] = item['quantity'] * item['price']
                self.update_tree()
                return
                
        # Add new
        new_item = {
            'id': product['id'],
            'name': product['name'],
            'quantity': 1.0,
            'price': product['price'],
            'subtotal': product['price'],
            'unit_of_measure': product['um']
        }
        self.cart.append(new_item)
        self.update_tree()
        
    def edit_qty(self, event):
        item_id = self.tree.focus()
        if not item_id: return
        
        idx = self.tree.index(item_id)
        current_qty = self.cart[idx]['quantity']
        
        # Simple Dialog for Qty
        from tkinter import simpledialog
        new_qty = simpledialog.askfloat("Cantidad", f"Cantidad para {self.cart[idx]['name']}:", initialvalue=current_qty, parent=self)
        
        if new_qty is not None:
            if new_qty <= 0:
                self.cart.pop(idx)
            else:
                self.cart[idx]['quantity'] = new_qty
                self.cart[idx]['subtotal'] = new_qty * self.cart[idx]['price']
            self.update_tree()

    def update_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        total = 0
        for item in self.cart:
            self.tree.insert("", "end", values=(item['name'], f"{item['quantity']:.2f}", f"{item['price']:.2f}", f"{item['subtotal']:.2f}"))
            total += item['subtotal']
            
        self.total_label.config(text=f"Total: S/ {total:,.2f}")
        
    def confirm_movement(self):
        if not self.cart: return
        
        # Build reason (auto or blank? User previously wanted reason mandatory)
        # Let's mock reason or ask? 
        # User request: "automaticamente se agrega o disminuye" (implying quick action).
        # We can default the reason to "Movimiento Táctil" or "Ingreso Rápido".
        reason = f"{self.move_type} Táctil"
        
        total = sum(i['subtotal'] for i in self.cart)
        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            database.record_movement(self.move_type, reason, self.issuer_id, self.address, self.cart, total, date_time)
            messagebox.showinfo("Éxito", "Movimiento registrado.", parent=self)
            
            if self.on_complete:
                print(f"DEBUG: Calling on_complete with total: {total}")
                self.on_complete(total)
            else:
                print("DEBUG: No on_complete callback provided.")
            
            self.destroy()
            if hasattr(self.parent_view, 'load_movements_history'):
                self.parent_view.load_movements_history() 
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al guardar: {e}", parent=self)


    def handle_scan(self, event):
        code = self.scan_entry.get().strip()
        if not code: return
        
        # Find product
        product = self.code_map.get(code)
        
        if product:
             self.add_to_cart(product)
             self.scan_entry.delete(0, tk.END)
        else:
             messagebox.showwarning("Aviso", f"Producto no encontrado: {code}", parent=self)
             self.scan_entry.delete(0, tk.END)
             
        # Refocus logic is automatic?
        self.after(10, self.scan_entry.focus_set)

    def check_scan_input(self, event):
        """Checks if current input matches a product code exactly (Instant Scan)."""
        code = self.scan_entry.get().strip()
        if not code: return
        
        # Immediate match check
        if code in self.code_map:
             self.add_to_cart(self.code_map[code])
             self.scan_entry.delete(0, tk.END)
