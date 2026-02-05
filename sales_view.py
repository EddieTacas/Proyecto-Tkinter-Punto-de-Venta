import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import database
from datetime import datetime
import config_manager
import json
import requests
import threading
import io
from PIL import Image
import qrcode
import utils
import state_manager

try:
    import win32print
    import win32ui
except ImportError:
    win32print = None
    win32ui = None
    print("ADVERTENCIA: Módulo 'pywin32' no encontrado. La funcionalidad de impresión no estará disponible.")

# --- Constantes de Estilo (Modo Oscuro) ---
FONT_FAMILY = "Segoe UI" # o "Arial", "Roboto"
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_HEADER = 16

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, COLOR_BUTTON_PRIMARY, COLOR_BUTTON_SECONDARY

COLOR_PRIMARY_DARK = COLOR_PRIMARY
COLOR_SECONDARY_DARK = COLOR_SECONDARY
COLOR_ACCENT_BLUE = COLOR_ACCENT
COLOR_TEXT_LIGHT = COLOR_TEXT
# Special for Sales
COLOR_TOTAL_CHANGE = "#4CAF50" # Verde lima (Good for both dark and light for Money?) or defined in theme?
# For now keep hardcoded or move to theme. User asked for general theme. 
# #4CAF50 is dark enough for white bg and bright enough for dark bg.

class SalesView(ttk.Frame):
    def __init__(self, master, caja_id=None):
        super().__init__(master, padding=10, style='SalesView.TFrame')
        
        # --- Configuración de Estilos (Dark Mode) ---
        # --- Configuración del Layout Principal (3 columnas) ---
        self.columnconfigure(0, weight=2, uniform="group1") # Columna de formularios
        self.columnconfigure(1, weight=3, uniform="group1") # Columna de carrito (más ancha)
        self.columnconfigure(2, weight=2, uniform="group1") # Columna de vista previa
        self.rowconfigure(1, weight=1)

        # --- Estilos personalizados con ttkbootstrap ---
        # --- Estilos personalizados con ttkbootstrap ---
        style = ttk.Style.get_instance()
        
        # Eliminadas configuraciones globales que forzaban modo oscuro en inputs y labels
        style.configure('SalesView.TFrame') 
        
        # Estilos personalizados específicos (sin forzar background global)
        style.configure('Custom.TButton', font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        style.configure('Large.TLabel', font=(FONT_FAMILY, FONT_SIZE_LARGE, 'bold'))
        style.configure('Success.Large.TLabel', font=(FONT_FAMILY, FONT_SIZE_LARGE, 'bold'), foreground=COLOR_TOTAL_CHANGE)
        style.configure('Header.TLabel', font=(FONT_FAMILY, FONT_SIZE_HEADER, 'bold'), foreground=COLOR_ACCENT_BLUE)
        style.configure('info.TLabel', foreground=COLOR_ACCENT_BLUE)

        # --- Inicialización de variables ---
        self.products = {}
        self.issuers = {}
        self.cart = []
        self.total = 0.0
        self.editing_item_index = None
        self.doc_type_var = tk.StringVar(value="NOTA DE VENTA")
        self.doc_series_var = tk.StringVar()
        self.doc_number_var = tk.StringVar()
        self.payment_method_var2 = tk.StringVar(value="NINGUNO")
        self.payment_method_var2 = tk.StringVar(value="NINGUNO")
        self.amount_paid_var2 = tk.DoubleVar(value=0.0)
        self.current_anulado = 0.0

        # --- Fila 0: Emisor y Fecha ---
        self.setup_top_bar()
        
        # Cargar ID de Caja
        # Cargar ID de Caja
        if caja_id:
            self.caja_id = str(caja_id)
        else:
            self.caja_id = config_manager.load_setting('caja_id', '1')

        # --- Cargar datos previos a la UI ---
        self.load_units_of_measure()

        # --- Paneles Principales ---
        self.setup_left_pane()
        self.setup_center_pane()
        self.setup_right_pane()

        # --- Carga de datos y bindings ---
        self.bind_events()
        
        # Cargar datos AL FINAL, después de que toda la UI y variables estén listas
        self.load_issuers_from_db()
        # self.load_products_from_db() # Moved inside load_issuers_from_db or called after setting issuer
        
        self.load_state()
        self.after(200, lambda: self.product_combo.focus_set())
        self.update_ticket_preview()

    def load_units_of_measure(self):
        try:
            with open(utils.resource_path('unidades_medida.json'), 'r', encoding='utf-8') as f:
                self.units_data = json.load(f)
            
            self.um_description_to_code = {item['descripcion']: item['codigo_sunat'] for item in self.units_data}
            self.um_code_to_description = {item['codigo_sunat']: item['descripcion'] for item in self.units_data}
            self.um_descriptions = sorted(list(self.um_description_to_code.keys()))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar 'unidades_medida.json'.\n{e}", parent=self.winfo_toplevel())
            self.units_data = []
            self.um_description_to_code = {}
            self.um_code_to_description = {}
            self.um_descriptions = []

    def setup_top_bar(self):
        top_frame = ttk.Frame(self, bootstyle="default")
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Label(top_frame, text="Emisor:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold")).pack(side=LEFT, padx=(5, 5))
        self.issuer_var = tk.StringVar()
        self.issuer_combo = ttk.Combobox(top_frame, textvariable=self.issuer_var, state="readonly", width=30)
        self.issuer_combo.pack(side=LEFT, fill=X, expand=True, padx=5)

        ttk.Label(top_frame, text="Dirección:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold")).pack(side=LEFT, padx=(15, 5))
        self.address_var = tk.StringVar()
        self.address_combo = ttk.Combobox(top_frame, textvariable=self.address_var, state="readonly", width=40)
        self.address_combo.pack(side=LEFT, fill=X, expand=True, padx=5)

        # ttk.Label(top_frame, text="Tipo Comprobante:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold")).pack(side=LEFT, padx=(15, 5))
        # doc_values = ["NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA", "FACTURA ELECTRÓNICA"]
        # self.doc_type_combo = ttk.Combobox(top_frame, textvariable=self.doc_type_var, values=doc_values, state="readonly", width=25)
        # self.doc_type_combo.pack(side=LEFT, padx=5)
        # self.doc_type_combo.bind("<<ComboboxSelected>>", self.on_doc_type_select)

        self.datetime_var = tk.StringVar()
        self.datetime_entry = ttk.Entry(top_frame, textvariable=self.datetime_var, state="readonly", width=20, justify='center', font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"))
        self.datetime_entry.pack(side=RIGHT, padx=5)
        ttk.Label(top_frame, text="Fecha y Hora:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold")).pack(side=RIGHT)
        self.update_datetime()
        
        # Arqueo Button
        ttk.Button(top_frame, text="ARQUEO DE CAJA", command=self.open_cash_count, bootstyle="warning").pack(side=RIGHT, padx=5)

    def setup_left_pane(self):
        # Contenedor principal del panel izquierdo
        left_pane_container = ttk.Frame(self)
        left_pane_container.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_pane_container.rowconfigure(0, weight=1)
        left_pane_container.columnconfigure(0, weight=1)

        # Canvas y Scrollbar
        canvas = tk.Canvas(left_pane_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_pane_container, orient="vertical", command=canvas.yview)
        
        # Frame scrollable dentro del canvas
        self.scrollable_frame = ttk.Frame(canvas, style='SalesView.TFrame')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        
        # Configurar el canvas para expandirse con la ventana
        def on_canvas_configure(event):
            canvas.itemconfig(canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw"), width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindings para scroll con rueda del mouse (solo cuando el mouse está encima)
        def _on_mousewheel(event):
            # Verificar si el widget bajo el mouse no es un combobox o entry que necesite scroll propio
            # Aunque en este caso, queremos que el panel principal haga scroll
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        # Bindear eventos de entrada/salida al contenedor principal del panel izquierdo
        left_pane_container.bind('<Enter>', _bind_mousewheel)
        left_pane_container.bind('<Leave>', _unbind_mousewheel)

        self.canvas = canvas # Guardar referencia para scroll manual

        self.canvas = canvas # Guardar referencia para scroll manual

        # --- Frame Datos del Producto ---
        product_frame = ttk.Labelframe(self.scrollable_frame, text="Datos del Producto", padding=10)
        product_frame.pack(fill="x", pady=(0, 15))
        product_frame.columnconfigure(1, weight=1)
        
        # --- Escaneo de Productos ---
        ttk.Label(product_frame, text="Escaneo:").grid(row=0, column=0, sticky="w", pady=3)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(product_frame, textvariable=self.scan_var, bootstyle="warning")
        self.scan_entry.grid(row=0, column=1, sticky="ew", pady=3)
        
        # Placeholder logic
        self.scan_placeholder = "Escaneo de Productos"
        self._setup_placeholder(self.scan_entry, self.scan_placeholder)
        
        self.scan_entry.bind("<Return>", self.handle_scan)
        self.scan_entry.bind("<KP_Enter>", self.handle_scan)

        ttk.Label(product_frame, text="Producto:").grid(row=1, column=0, sticky="w", pady=3)
        self.product_var = tk.StringVar()
        self._trace_uppercase(self.product_var)
        self.product_combo = ttk.Combobox(product_frame, textvariable=self.product_var)
        self.product_combo.grid(row=1, column=1, sticky="ew", pady=3)
        
        self.stock_label = ttk.Label(product_frame, text="Stock: -", bootstyle="info", font=(FONT_FAMILY, 10, "bold"), foreground=COLOR_ACCENT_BLUE)
        self.stock_label.grid(row=2, column=1, sticky="w", pady=3)

        ttk.Label(product_frame, text="Cantidad:").grid(row=3, column=0, sticky="w", pady=3)
        self.quantity_var = tk.DoubleVar(value=1.0)
        self.quantity_entry = ttk.Entry(product_frame, textvariable=self.quantity_var, width=12)
        self.quantity_entry.grid(row=3, column=1, sticky="w", pady=3)

        ttk.Label(product_frame, text="Precio Venta:").grid(row=4, column=0, sticky="w", pady=3)
        self.price_var = tk.DoubleVar()
        self.price_entry = ttk.Entry(product_frame, textvariable=self.price_var, width=12)
        self.price_entry.grid(row=4, column=1, sticky="w", pady=3)

        ttk.Label(product_frame, text="U. Medida:").grid(row=5, column=0, sticky="w", pady=3)
        self.unit_of_measure_var = tk.StringVar()
        self.unit_of_measure_combo = ttk.Combobox(product_frame, textvariable=self.unit_of_measure_var, values=self.um_descriptions, width=12)
        self.unit_of_measure_combo.grid(row=5, column=1, sticky="w", pady=3)

        self.add_button = ttk.Button(product_frame, text="✚ Añadir al Carrito", command=self.add_to_cart, bootstyle="primary")
        self.add_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Bindings para auto-scroll en Producto
        for w in [self.scan_entry, self.product_combo, self.quantity_entry, self.price_entry, self.unit_of_measure_combo]:
            w.bind("<FocusIn>", self._on_focus_scroll, add="+")

        # --- Frame Datos del Cliente ---
        customer_frame = ttk.Labelframe(self.scrollable_frame, text="Datos del Cliente", padding=10)
        customer_frame.pack(fill="x", pady=(0, 15))
        customer_frame.columnconfigure(1, weight=1)

        ttk.Label(customer_frame, text="DNI/RUC:").grid(row=0, column=0, sticky="w", pady=3)
        self.customer_doc_var = tk.StringVar()
        self._trace_uppercase(self.customer_doc_var)
        doc_entry_frame = ttk.Frame(customer_frame)
        doc_entry_frame.grid(row=0, column=1, sticky="ew")
        doc_entry_frame.columnconfigure(0, weight=1)
        self.customer_doc_entry = ttk.Entry(doc_entry_frame, textvariable=self.customer_doc_var)
        self.customer_doc_entry.grid(row=0, column=0, sticky="ew")
        self.search_customer_button = ttk.Button(doc_entry_frame, text="🔍", command=self.search_customer, bootstyle="secondary", width=3)
        self.search_customer_button.grid(row=0, column=1, sticky="e", padx=(5,0))

        ttk.Label(customer_frame, text="Nombre:").grid(row=1, column=0, sticky="w", pady=3)
        self.customer_name_var = tk.StringVar()
        self._trace_uppercase(self.customer_name_var)
        self.customer_name_combo = ttk.Combobox(customer_frame, textvariable=self.customer_name_var)
        self.customer_name_combo.grid(row=1, column=1, sticky="ew", pady=3)
        self.customer_name_combo.bind('<KeyRelease>', self.on_customer_name_type)
        self.customer_name_combo.bind('<<ComboboxSelected>>', self.on_customer_name_select)

        ttk.Label(customer_frame, text="Dirección:").grid(row=2, column=0, sticky="w", pady=3)
        self.customer_address_var = tk.StringVar()
        self._trace_uppercase(self.customer_address_var)
        self.customer_address_entry = ttk.Entry(customer_frame, textvariable=self.customer_address_var)
        self.customer_address_entry.grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(customer_frame, text="Celular:").grid(row=3, column=0, sticky="w", pady=3)
        self.customer_phone_var = tk.StringVar()
        self._trace_uppercase(self.customer_phone_var)
        self.customer_phone_entry = ttk.Entry(customer_frame, textvariable=self.customer_phone_var)
        self.customer_phone_entry.grid(row=3, column=1, sticky="ew", pady=3)

        # Bindings para auto-scroll en Cliente
        for w in [self.customer_doc_entry, self.customer_name_combo, self.customer_address_entry, self.customer_phone_entry]:
            w.bind("<FocusIn>", self._on_focus_scroll, add="+")

        # --- Frame de Pago y Comprobante (Contenedor) ---
        payment_doc_container = ttk.Frame(self.scrollable_frame)
        payment_doc_container.pack(fill="x", pady=(0, 0))
        payment_doc_container.columnconfigure(0, weight=1)

        # --- Frame Pago y Comprobante ---
        total_frame = ttk.Labelframe(payment_doc_container, text="Pago y Comprobante", padding=10)
        total_frame.grid(row=0, column=0, sticky="ew")
        total_frame.columnconfigure(1, weight=1)

        self.total_label = ttk.Label(total_frame, text="Total: S/ 0.00", style="Success.Large.TLabel", foreground=COLOR_TOTAL_CHANGE)
        self.total_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(5, 10))
        
        ttk.Label(total_frame, text="Medio de Pago 1:").grid(row=1, column=0, sticky="w", pady=3)
        self.payment_method_var = tk.StringVar(value="EFECTIVO")
        self.payment_method_combo = ttk.Combobox(total_frame, textvariable=self.payment_method_var, values=["EFECTIVO", "YAPE", "BCP", "BBVA", "INTERBANK"])
        self.payment_method_combo.grid(row=1, column=1, sticky="ew", pady=3)
        
        ttk.Label(total_frame, text="Importe Cobrado 1:").grid(row=2, column=0, sticky="w", pady=3)
        self.amount_paid_var = tk.DoubleVar(value=0.0)
        self.amount_paid_entry = ttk.Entry(total_frame, textvariable=self.amount_paid_var)
        self.amount_paid_entry.grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(total_frame, text="Medio de Pago 2:").grid(row=3, column=0, sticky="w", pady=3)
        self.payment_method_combo2 = ttk.Combobox(total_frame, textvariable=self.payment_method_var2, values=["NINGUNO", "EFECTIVO", "YAPE", "BCP", "BBVA", "INTERBANK"])
        self.payment_method_combo2.grid(row=3, column=1, sticky="ew", pady=3)
        
        ttk.Label(total_frame, text="Importe Cobrado 2:").grid(row=4, column=0, sticky="w", pady=3)
        self.amount_paid_entry2 = ttk.Entry(total_frame, textvariable=self.amount_paid_var2)
        self.amount_paid_entry2.grid(row=4, column=1, sticky="ew", pady=3)
        
        # --- Row 6: Anulado & Vuelto Combo Frame ---
        av_frame = ttk.Frame(total_frame)
        av_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(5, 10))
        
        # Anulado Label (Left)
        self.anulado_label = ttk.Label(av_frame, text="Anulado: S/ 0.00", font=("Segoe UI", 10, "bold"), foreground="orange")
        self.anulado_label.pack(side="left", padx=(0, 5))
        
        # Anulado Button (Center/Left)
        ttk.Button(av_frame, text="ANULADO", bootstyle="warning", command=self.open_anulado_dialog).pack(side="left", padx=5)
        
        # Vuelto Label (Right)
        self.change_label = ttk.Label(av_frame, text="Vuelto: S/ 0.00", style="Warning.Large.TLabel", font=("Segoe UI", 12, "bold"), foreground=COLOR_ACCENT) # Blue-ish if possible or keep style
        self.change_label.pack(side="right", padx=(5, 0))

        doc_types = ["NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA", "FACTURA ELECTRÓNICA"]
        ttk.Label(total_frame, text="Tipo Doc:").grid(row=7, column=0, sticky="w", pady=3)
        self.doc_type_combo = ttk.Combobox(total_frame, textvariable=self.doc_type_var, values=doc_types, state="readonly")
        self.doc_type_combo.grid(row=7, column=1, sticky="ew", pady=3)
        self.doc_type_combo.bind("<<ComboboxSelected>>", self.on_doc_type_select)

        series_frame = ttk.Frame(total_frame)
        series_frame.grid(row=8, column=1, sticky="ew", pady=3)
        series_frame.columnconfigure(1, weight=1)
        self.doc_series_entry = ttk.Entry(series_frame, textvariable=self.doc_series_var, state="readonly", width=8)
        self.doc_series_entry.grid(row=0, column=0, sticky="ew")
        self.doc_number_entry = ttk.Entry(series_frame, textvariable=self.doc_number_var, state="readonly")
        self.doc_number_entry.grid(row=0, column=1, sticky="ew", padx=(5,0))
        ttk.Label(total_frame, text="Serie-Nro:").grid(row=7, column=0, sticky="w", pady=3)

        # Bindings para auto-scroll en Pago
        for w in [self.payment_method_combo, self.amount_paid_entry, self.payment_method_combo2, self.amount_paid_entry2, self.doc_type_combo]:
            w.bind("<FocusIn>", self._on_focus_scroll, add="+")

        # --- Frame de Acciones ---
        action_frame = ttk.Frame(self.scrollable_frame)
        action_frame.pack(fill="x", pady=(15, 20))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        ttk.Button(action_frame, text="🖨️ Imprimir Ticket", command=self.print_ticket, bootstyle="secondary-outline").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(action_frame, text="📄 Generar Documento", command=self.process_sale, bootstyle="success").grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def setup_center_pane(self):
        center_pane = ttk.Labelframe(self, text="Carrito de Compras", padding=10)
        center_pane.grid(row=1, column=1, sticky="nsew", padx=10)
        center_pane.rowconfigure(0, weight=1)
        center_pane.columnconfigure(0, weight=1)

        self.cart_tree = ttk.Treeview(center_pane, columns=("producto", "cantidad", "unidad_medida", "precio", "subtotal"), show="headings", bootstyle="primary")
        self.cart_tree.heading("producto", text="Producto")
        self.cart_tree.heading("cantidad", text="Cantidad")
        self.cart_tree.heading("unidad_medida", text="U.Medida")
        self.cart_tree.heading("precio", text="P. Unit.")
        self.cart_tree.heading("subtotal", text="Subtotal")
        self.cart_tree.column("producto", width=180)
        self.cart_tree.column("cantidad", width=60, anchor="center")
        self.cart_tree.column("unidad_medida", width=70, anchor="center")
        self.cart_tree.column("precio", width=70, anchor="e")
        self.cart_tree.column("subtotal", width=80, anchor="e")
        
        scrollbar = ttk.Scrollbar(center_pane, orient=VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        cart_actions_frame = ttk.Frame(center_pane)
        cart_actions_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10,0))
        ttk.Button(cart_actions_frame, text="Modificar Fila", command=self.modify_cart_item, bootstyle="info-outline").pack(side=LEFT, expand=True, fill=X, padx=(0,5))
        ttk.Button(cart_actions_frame, text="Eliminar Fila", command=self.remove_from_cart, bootstyle="danger-outline").pack(side=LEFT, expand=True, fill=X)

        obs_frame = ttk.Labelframe(center_pane, text="Observaciones", padding=(10,5))
        obs_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10,0))
        obs_frame.columnconfigure(0, weight=1)
        self.observations_text = tk.Text(obs_frame, height=3, font=(FONT_FAMILY, 10), relief="solid", borderwidth=1)
        self.observations_text.grid(row=0, column=0, sticky="ew")
        self.observations_text.bind("<KeyRelease>", self._text_to_uppercase)

        # --- Totals Footer (Below Cart) ---
        totals_footer = ttk.Frame(center_pane)
        totals_footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Order: Items, Descuento, Sobreprecio, Total Neto
        # Frame Items
        self.frame_items = ttk.Frame(totals_footer)
        self.frame_items.pack(side="left", padx=10)
        ttk.Label(self.frame_items, text="Items", font=(FONT_FAMILY, 10, "bold")).pack(side="top")
        self.footer_items_value = ttk.Label(self.frame_items, text="0", font=(FONT_FAMILY, 10, "bold"))
        self.footer_items_value.pack(side="top")
        
        # Frame Discount (Hidden by default)
        self.frame_discount = ttk.Frame(totals_footer)
        # self.frame_discount.pack(side="left", padx=10) 
        ttk.Label(self.frame_discount, text="DSCTO", font=(FONT_FAMILY, 10, "bold"), foreground="#D32F2F").pack(side="top")
        self.footer_discount_value = ttk.Label(self.frame_discount, text="0.00", font=(FONT_FAMILY, 10, "bold"), foreground="#D32F2F")
        self.footer_discount_value.pack(side="top")
        
        # Frame Surcharge (Hidden by default)
        self.frame_surcharge = ttk.Frame(totals_footer)
        # self.frame_surcharge.pack(side="left", padx=10)
        ttk.Label(self.frame_surcharge, text="ADIC.", font=(FONT_FAMILY, 10, "bold"), foreground="#1976D2").pack(side="top")
        self.footer_surcharge_value = ttk.Label(self.frame_surcharge, text="0.00", font=(FONT_FAMILY, 10, "bold"), foreground="#1976D2")
        self.footer_surcharge_value.pack(side="top")
        
        # Frame Total
        frame_total = ttk.Frame(totals_footer)
        frame_total.pack(side="right", padx=10)
        ttk.Label(frame_total, text="Total N.", font=(FONT_FAMILY, 12, "bold"), foreground="#4CAF50").pack(side="top", anchor="e")
        self.footer_total_value = ttk.Label(frame_total, text="S/ 0.00", font=(FONT_FAMILY, 12, "bold"), foreground="#4CAF50")
        self.footer_total_value.pack(side="top", anchor="e")

    def setup_right_pane(self):
        right_pane = ttk.Labelframe(self, text="Vista Previa de Ticket", padding=0)
        right_pane.grid(row=1, column=2, sticky="nsew", padx=(0, 0))
        right_pane.rowconfigure(0, weight=1)
        right_pane.columnconfigure(0, weight=1)

        ticket_container = ttk.Frame(right_pane, bootstyle="light", padding=1)
        ticket_container.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        ticket_container.rowconfigure(0, weight=1)
        ticket_container.columnconfigure(0, weight=1)

        self.ticket_preview = tk.Text(ticket_container, wrap="none", font=("Consolas", 9), width=42, relief="flat")
        self.ticket_preview.grid(row=0, column=0, sticky="nsew")
        self.ticket_preview.config(state="disabled")
        
        # Configurar tags para estilos
        self.ticket_preview.tag_configure("center", justify='center')
        self.ticket_preview.tag_configure("right", justify='right')
        self.ticket_preview.tag_configure("bold", font=("Consolas", 9, "bold"))
        self.ticket_preview.tag_configure("inverse", background="black", foreground="white", font=("Consolas", 10, "bold"))
        self.ticket_preview.tag_configure("header", font=("Consolas", 9, "bold"))
        self.ticket_preview.tag_configure("large", font=("Consolas", 11, "bold"))

    # ===================================================================================
    # == A PARTIR DE AQUÍ, LA LÓGICA DE NEGOCIO SE MANTIENE IGUAL QUE EN EL ARCHIVO ORIGINAL ==
    # ===================================================================================

    def _on_focus_scroll(self, event):
        widget = event.widget
        # Calcular posición relativa del widget respecto al frame scrollable
        try:
            widget_y = widget.winfo_rooty() - self.scrollable_frame.winfo_rooty()
            widget_height = widget.winfo_height()
            
            canvas_height = self.canvas.winfo_height()
            scrollable_height = self.scrollable_frame.winfo_height()
            
            if scrollable_height <= canvas_height:
                return # No hay scroll necesario

            # Calcular la posición ideal (centrado o visible)
            # Queremos que el widget esté visible.
            # yview_moveto toma un valor entre 0.0 y 1.0
            
            # Posición actual del scroll (top)
            current_scroll_pos = self.canvas.yview()[0]
            
            # Posición relativa del widget en porcentaje (0.0 a 1.0)
            target_pos = widget_y / scrollable_height
            
            # Altura del widget en porcentaje
            widget_h_pct = widget_height / scrollable_height
            
            # Altura del canvas en porcentaje del total scrollable
            view_h_pct = canvas_height / scrollable_height
            
            # Si el widget está arriba de la vista actual
            if target_pos < current_scroll_pos:
                self.canvas.yview_moveto(target_pos)
            # Si el widget está abajo de la vista actual
            elif (target_pos + widget_h_pct) > (current_scroll_pos + view_h_pct):
                self.canvas.yview_moveto(target_pos + widget_h_pct - view_h_pct)
                
        except Exception:
            pass # Evitar errores si el widget no está listo o geometría falla

    def _trace_uppercase(self, string_var):
        def to_uppercase(*args):
            s = string_var.get()
            if s != s.upper():
                string_var.set(s.upper())
        string_var.trace_add('write', to_uppercase)

    def _text_to_uppercase(self, event):
        widget = event.widget
        content = widget.get("1.0", "end-1c")
        if content != content.upper():
            cursor_pos = widget.index(tk.INSERT)
            widget.delete("1.0", tk.END)
            widget.insert("1.0", content.upper())
            widget.mark_set(tk.INSERT, cursor_pos)

    def bind_events(self):
        # self.product_combo.bind("<Return>", self.filter_products) # Conflict with scan? No, different widget
        self.product_combo.bind("<Return>", self.filter_products)
        self.product_combo.bind("<KP_Enter>", self.filter_products)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)
        self.amount_paid_var.trace_add('write', self.calculate_change)
        self.amount_paid_var2.trace_add('write', self.calculate_change)
        self.issuer_combo.bind("<<ComboboxSelected>>", self.on_issuer_select)
        self.address_combo.bind("<<ComboboxSelected>>", self.on_address_select)
        self.customer_name_var.trace_add('write', lambda *args: self.update_ticket_preview())
        self.customer_doc_var.trace_add('write', lambda *args: self.update_ticket_preview())
        self.doc_type_combo.bind("<<ComboboxSelected>>", self.on_doc_type_select)
        self.customer_doc_entry.bind("<Return>", self.search_customer)
        self.customer_doc_entry.bind("<KP_Enter>", self.search_customer)
        self.unit_of_measure_combo.bind("<Return>", self.filter_um_combo)
        
        # Navigation Bindings
        self.quantity_entry.bind("<Return>", lambda e: self.price_entry.focus_set())
        self.price_entry.bind("<Return>", lambda e: self.unit_of_measure_combo.focus_set())
        self.price_entry.bind("<FocusIn>", lambda e: self.price_entry.select_range(0, 'end'))
        self.add_button.bind("<Return>", lambda e: (self.add_to_cart(), "break")[1])
    
        # Autosave Hooks
        for w in [self.customer_doc_entry, self.customer_name_combo, self.customer_address_entry, self.customer_phone_entry, self.doc_type_combo, self.payment_method_combo]:
            w.bind('<FocusOut>', self.save_state, add="+")
        self.issuer_combo.bind("<<ComboboxSelected>>", lambda e: self.save_state(), add="+")
        
    def _setup_placeholder(self, entry, placeholder_text):
        entry.insert(0, placeholder_text)
        entry.configure(foreground='grey')

        def on_focus_in(event):
            if entry.get() == placeholder_text:
                entry.delete(0, tk.END)
                entry.configure(foreground=COLOR_TEXT_LIGHT)

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder_text)
                entry.configure(foreground='grey')

        entry.bind("<FocusIn>", on_focus_in, add="+")
        entry.bind("<FocusOut>", on_focus_out, add="+")

    def handle_scan(self, event=None):
        code = self.scan_var.get().strip()
        if not code or code == self.scan_placeholder:
            return

        # Play sound? (Optional, requires simplified sound lib or similar, skip for now)
        
        # 1. Search Product
        product_name = self.product_code_map.get(code)
        
        if not product_name:
            # Try reloading products just in case? Or just fail
            # messagebox.showwarning("No encontrado", f"Producto con código '{code}' no encontrado.")
            # Beep or visual feedback
            self.scan_entry.delete(0, tk.END)
            # Flash background red?
            current_bg = self.scan_entry.cget('style') # Hard to flash style
            print(f"Code {code} not found")
            return

        # 2. Check if in Cart
        found_in_cart = False
        item_index = -1
        
        for idx, item in enumerate(self.cart):
            # item: {id, name, quantity, price, subtotal, unit_of_measure, original_price}
            if item['name'] == product_name:
                found_in_cart = True
                item_index = idx
                break
        
        if found_in_cart:
            # Increment Quantity
            item = self.cart[item_index]
            
            # Stock Check
            if product_name in self.products:
                 current_stock = self.products[product_name]['stock']
                 # For in-cart items, the 'stock' in self.products is already decremented by previous adds?
                 # Wait, how does add_to_cart handle stock?
                 # self.products[product_name]['stock'] -= quantity
                 # So self.products[product_name]['stock'] is the REMAINING stock.
                 
                 allow_negative = config_manager.load_setting('allow_negative_stock', 'No')
                 if allow_negative == "No" and current_stock < 1:
                     messagebox.showwarning("Stock Insuficiente", f"No hay suficiente stock para agregar otro '{product_name}'.")
                     self.scan_entry.delete(0, tk.END)
                     return

            new_qty = item['quantity'] + 1
            item['quantity'] = new_qty
            item['subtotal'] = item['price'] * new_qty
            
            # Update Treeview
            child_id = self.cart_tree.get_children()[item_index]
            self.cart_tree.item(child_id, values=(item['name'], f"{new_qty:.2f}", item['unit_of_measure'], f"{item['price']:.2f}", f"{item['subtotal']:.2f}"))
            
            # Update Stock Counter
            if product_name in self.products:
                self.products[product_name]['stock'] -= 1
                if self.product_var.get() == product_name:
                     self.stock_label.config(text=f"Stock: {self.products[product_name]['stock']:.2f}")

        else:
            # Add New Item
            # Populate form variables to reuse add_to_cart logic?
            # Or call add_to_cart with specific params?
            # add_to_cart currently pulls from UI variables.
            # Let's refactor add_to_cart or set UI variables and call it.
            # Setting UI variables is safer to reuse logic (stock checks, etc)
            
            self.product_var.set(product_name)
            self.on_product_select() # This updates price, stock label, etc.
            self.quantity_var.set(1.0)
            
            # Now call add_to_cart
            # NOTE: add_to_cart uses self.product_var.get()
            self.add_to_cart()
            
        # 3. Cleanup
        self.update_total()
        self.scan_entry.delete(0, tk.END)
        # Keep focus is automatic for Entry on Return usually, but let's ensure
        self.scan_entry.focus_set()

    def filter_um_combo(self, event):
        typed = self.unit_of_measure_combo.get()
        if not typed:
            self.unit_of_measure_combo['values'] = self.um_descriptions
            self.add_button.focus_set() # Move focus to Add button if empty/enter
        else:
            filtered = [item for item in self.um_descriptions if typed.lower() in item.lower()]
            self.unit_of_measure_combo['values'] = filtered
            if filtered:
                self.unit_of_measure_combo.event_generate('<Down>')
            else:
                 # If no matches or exact match, assume selection/entry and move focus
                 self.add_button.focus_set()

    def on_customer_name_type(self, event):
        if event.keysym in ['Return', 'Up', 'Down', 'Left', 'Right']:
            return

        search_term = self.customer_name_var.get().strip()
        if len(search_term) < 2:
            return

        # Buscar en DB
        results = database.search_customers_general(search_term)
        
        # Actualizar valores del combobox
        # Formato: "NOMBRE | DNI/RUC" para mostrar info relevante
        values = []
        self.customer_search_results = {} # Guardar referencia para recuperar datos al seleccionar
        
        for row in results:
            # row: id, type, doc_number, name, phone, address, alias
            display_text = f"{row[3]} | {row[2]}"
            if row[6]: # Si tiene alias
                display_text += f" ({row[6]})"
            
            values.append(display_text)
            self.customer_search_results[display_text] = row

        self.customer_name_combo['values'] = values
        
        # Abrir la lista si hay resultados
        if values:
            self.customer_name_combo.event_generate('<<ComboboxSelected>>') # Hack para actualizar visualmente a veces necesario
            # Ojo: abrir el dropdown programáticamente en tk es tricky, 
            # pero al escribir y tener valores, el usuario puede desplegarlo.
            # ttkbootstrap/tk no tiene un método 'open' directo fácil y fiable para todos los OS.
            # Dejamos que el usuario despliegue o si sigue escribiendo.
            pass

    def on_customer_name_select(self, event):
        selection = self.customer_name_combo.get()
        if selection in self.customer_search_results:
            data = self.customer_search_results[selection]
            # data: id, type, doc_number, name, phone, address, alias
            # Mapear a lo que espera populate_customer_data o setear directo
            # populate espera: id, doc, name, phone, address... (indices varian segun query original)
            # En database.search_customers_general: SELECT * FROM customers
            # customers table structure: id, doc_number, name, phone, address, type, alias
            # indices: 0, 1, 2, 3, 4, 5, 6
            
            self.customer_doc_var.set(data[1])
            self.customer_name_var.set(data[2])
            self.customer_phone_var.set(data[3])
            self.customer_address_var.set(data[4])
            
            # Focus al producto o donde prefiera el usuario, 
            # en este caso como ya seleccionó el cliente, tiene sentido ir al producto o quedarse ahí.
            # El requerimiento de focus era para la busqueda por DNI.
            self.customer_name_combo.focus_set()
            self.customer_name_combo.select_range(0, 'end')

    def search_customer(self, event=None):
        search_term = self.customer_doc_var.get().strip()
        if not search_term:
            return

        if search_term.isdigit():
            if len(search_term) not in [8, 11]:
                messagebox.showerror("Error de Validación", "Por favor, ingrese un DNI (8 dígitos) o RUC (11 dígitos) válido.", parent=self.winfo_toplevel())
                return
            thread = threading.Thread(target=self.fetch_customer_data, args=(search_term,))
            thread.daemon = True
            thread.start()
        else:
            # Ya no buscamos por alias aquí
            messagebox.showinfo("Información", "Para buscar por Nombre o Alias, utilice el campo 'Nombre'.", parent=self.winfo_toplevel())

    def show_customer_selection_popup(self, customers):
        popup = tk.Toplevel(self)
        popup.title("Seleccionar Cliente")
        popup.geometry("400x300")

        listbox = tk.Listbox(popup)
        listbox.pack(expand=True, fill="both")

        for customer in customers:
            listbox.insert(tk.END, f"{customer[2]} ({customer[1]})")

        def on_select():
            selected_index = listbox.curselection()
            if selected_index:
                self.populate_customer_data(customers[selected_index[0]])
                popup.destroy()

        select_button = ttk.Button(popup, text="Seleccionar", command=on_select)
        select_button.pack(pady=5)

    def populate_customer_data(self, customer_data):
        self.customer_doc_var.set(customer_data[1])
        self.customer_name_var.set(customer_data[2])
        self.customer_phone_var.set(customer_data[3])
        self.customer_address_var.set(customer_data[4])
        self.customer_doc_entry.focus_set()
        self.customer_doc_entry.select_range(0, 'end')
        self.save_state()

    def fetch_customer_data(self, doc):
        # Usar el nuevo cliente de API
        import api_client
        
        try:
            self.after(0, lambda: self.customer_name_var.set("Buscando..."))
            
            # Ejecutar búsqueda (esto ya corre en un thread separado desde search_customer)
            result = api_client.get_person_data(doc)
            
            if result and result.get("success"):
                data = result.get("data", {})
                
                # Nombre / Razón Social
                full_name = ""
                if len(doc) == 8:
                     # Para DNI, forzar formato: Nombres ApellidoP ApellidoM
                     nombres = data.get('nombre', '')
                     ap_paterno = data.get('apellido_paterno', '')
                     ap_materno = data.get('apellido_materno', '')
                     full_name = f"{nombres} {ap_paterno} {ap_materno}".strip()
                
                if not full_name:
                    full_name = data.get("nombre", "")
                    if not full_name:
                        full_name = f"{data.get('nombres', '')} {data.get('apellido_paterno', '')} {data.get('apellido_materno', '')}".strip()
                
                self.after(0, lambda: self.customer_name_var.set(full_name))

                address = data.get("domicilio", {}).get("direccion", "")
                self.after(0, lambda: self.customer_address_var.set(address))
                
                def set_focus_doc():
                    self.customer_doc_entry.focus_set()
                    self.customer_doc_entry.select_range(0, 'end')
                self.after(0, set_focus_doc)
            else:
                self.after(0, lambda: self.customer_name_var.set(""))
                msg = result.get("message", "No se encontraron datos.") if result else "Error desconocido."
                self.after(0, lambda: messagebox.showwarning("Búsqueda sin resultados", msg, parent=self.winfo_toplevel()))

        except Exception as e:
            self.after(0, lambda: self.customer_name_var.set(""))
            self.after(0, lambda: messagebox.showerror("Error Inesperado", f"Ocurrió un error: {e}", parent=self.winfo_toplevel()))

    def on_issuer_select(self, event=None):
        issuer_name = self.issuer_var.get()
        if issuer_name in self.issuers:
            addresses = [issuer['address'] for issuer in self.issuers[issuer_name]]
            self.address_combo['values'] = addresses
            if addresses:
                self.address_var.set(addresses[0])
                self.on_address_select()
            else:
                # If no addresses (shouldn't happen for valid issuer), clear products or load global?
                # Let's assume we load products for this issuer with no specific address (or all addresses)
                # But logic says we select first address.
                self.load_products_from_db(issuer_name, None)
        else:
            self.address_combo['values'] = []
            self.address_var.set("")
            self.load_products_from_db(None, None) # Load all or clear? Let's load all or empty.
            # If no issuer selected, maybe clear products?
            # For now, let's keep behavior of showing everything or nothing.
            # If we want to filter strictly, we should pass None, None which returns ALL products (global + assigned)
            # Or maybe we want to show NO products if no issuer selected?
            # Let's stick to: No issuer -> All products (or empty?)
            # The previous behavior was "All products".
            # But the user wants filtering.
            # If no issuer is selected, we probably shouldn't be selling.
            pass

    def on_address_select(self, event=None):
        self.update_ticket_preview()
        self.on_doc_type_select()
        
        # Reload products for this specific branch
        issuer_name = self.issuer_var.get()
        issuer_address = self.address_var.get()
        self.load_products_from_db(issuer_name, issuer_address)
        
        # Guardar persistencia por CAJA
        if issuer_name and issuer_address:
            # Buscar ID del emisor
            issuer_id = None
            if issuer_name in self.issuers:
                for i_data in self.issuers[issuer_name]:
                    if i_data['address'] == issuer_address:
                        issuer_id = i_data['id']
                        break
            
            if issuer_id:
                config_manager.save_caja_setting(self.caja_id, 'last_issuer_id', issuer_id)
                config_manager.save_caja_setting(self.caja_id, 'last_address', issuer_address)

    def on_doc_type_select(self, event=None):
        doc_type_full = self.doc_type_var.get()
        issuer_name = self.issuer_var.get()
        selected_address = self.address_var.get()
        if not issuer_name or not selected_address:
            self.doc_series_var.set("")
            self.doc_number_var.set("")
            return
        issuer_id = None
        if issuer_name in self.issuers:
            for issuer_data in self.issuers[issuer_name]:
                if issuer_data['address'] == selected_address:
                    issuer_id = issuer_data['id']
                    break
        if not issuer_id:
            self.doc_series_var.set("")
            self.doc_number_var.set("")
            return
        doc_type_mapping = {
            "NOTA DE VENTA": "NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA": "BOLETA", "FACTURA ELECTRÓNICA": "FACTURA",
            "NOTA DE CRÉDITO (BOLETA)": "NOTA_CREDITO_BOLETA", "NOTA DE CRÉDITO (FACTURA)": "NOTA_CREDITO_FACTURA",
            "GUÍA DE REMISIÓN ELECTRÓNICA": "GUIA_REMISION"
        }
        internal_doc_type = doc_type_mapping.get(doc_type_full, "UNKNOWN")
        series, number = database.get_correlative(issuer_id, internal_doc_type)
        
        # Fallback para Nota de Venta si no hay serie configurada
        if internal_doc_type == "NOTA DE VENTA" and not series:
            series = "NV01"
            
        self.doc_series_var.set(series if series else "")
        self.doc_number_var.set(number + 1 if number is not None else 1)

    def load_issuers_from_db(self):
        all_issuers = database.get_all_issuers()
        self.issuers = {}
        for issuer_id, name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers in all_issuers:
            if name not in self.issuers:
                self.issuers[name] = []
            self.issuers[name].append({
                'id': issuer_id, 'name': name, 'ruc': ruc, 'address': address,
                'commercial_name': commercial_name, 'logo': logo,
                'bank_accounts': bank_accounts, 'initial_greeting': initial_greeting,
                'final_greeting': final_greeting,
                'district': district, 'province': province,
                'department': department, 'ubigeo': ubigeo,
                'sol_user': sol_user, 'sol_pass': sol_pass, 'certificate': certificate,
                'fe_url': fe_url, 're_url': re_url,
                'guia_url_envio': guia_url_envio, 'guia_url_consultar': guia_url_consultar,
                'client_id': client_id, 'client_secret': client_secret,
                'validez_user': validez_user, 'validez_pass': validez_pass,
                'email': email, 'phone': phone,
                'default_operation_type': default_operation_type,
                'establishment_code': establishment_code,
                'cert_password': cert_password
            })
        self.issuer_combo['values'] = list(self.issuers.keys())
        
        if self.issuer_combo['values']:
            # Intentar cargar el último emisor seleccionado para esta CAJA
            last_issuer_id = config_manager.load_caja_setting(self.caja_id, 'last_issuer_id')
            last_address = config_manager.load_caja_setting(self.caja_id, 'last_address')
            
            selected_issuer_name = None
            
            if last_issuer_id:
                # Buscar el nombre del emisor que corresponde al ID guardado
                for name, issuer_list in self.issuers.items():
                    for issuer_data in issuer_list:
                        if issuer_data['id'] == last_issuer_id:
                            selected_issuer_name = name
                            break
                    if selected_issuer_name:
                        break
            
            if selected_issuer_name and selected_issuer_name in self.issuer_combo['values']:
                self.issuer_var.set(selected_issuer_name)
                # Si tenemos dirección guardada, intentamos establecerla
                if last_address:
                     # Actualizar combo de direcciones primero
                    self.on_issuer_select() 
                    if last_address in self.address_combo['values']:
                        self.address_var.set(last_address)
                        self.on_address_select()
                    else:
                        # Si la dirección guardada no existe, on_issuer_select ya seleccionó la primera
                        pass
                else:
                    self.on_issuer_select()
            else:
                self.issuer_var.set(self.issuer_combo['values'][0])
                self.on_issuer_select()

    def _number_to_text(self, amount):
        """Convierte un número a texto en formato moneda (Soles)."""
        def numero_a_letras(n):
            unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
            decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
            diez_y = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
            veinte_y = ["VEINTE", "VEINTIUN", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
            centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

            n = int(n)
            if n == 0: return "CERO"
            if n == 100: return "CIEN"
            
            text = ""
            if n >= 1000:
                mil = n // 1000
                if mil == 1: text += "MIL "
                else: text += numero_a_letras(mil) + " MIL "
                n %= 1000
            
            if n >= 100:
                text += centenas[n // 100] + " "
                n %= 100
            
            if n >= 30:
                text += decenas[n // 10]
                if n % 10 != 0: text += " Y " + unidades[n % 10]
            elif n >= 20:
                text += veinte_y[n - 20]
            elif n >= 10:
                text += diez_y[n - 10]
            elif n > 0:
                text += unidades[n]
                
            return text.strip()

        entero = int(amount)
        decimal = int(round((amount - entero) * 100))
        
        letras = numero_a_letras(entero)
        if letras == "UN": letras = "UN" # Ajuste para moneda
        
        return f"{letras} CON {decimal:02d}/100 SOLES"

    def update_ticket_preview(self, *args):
        self.ticket_preview.config(state="normal")
        self.ticket_preview.delete("1.0", tk.END)
        
        import textwrap
        
        issuer_name = self.issuer_var.get()
        selected_address = self.address_var.get()
        
        issuer_data = None
        if issuer_name in self.issuers:
            for issuer in self.issuers[issuer_name]:
                if issuer['address'] == selected_address:
                    issuer_data = issuer
                    break
        
        is_proforma = self.doc_type_var.get() == "NOTA DE VENTA"
        
        # --- HEADER ---
        if issuer_data:
            # Commercial Name
            commercial_name = issuer_data.get('commercial_name') or ''
            if commercial_name:
                self.ticket_preview.insert(tk.END, commercial_name + "\n", ("center", "bold"))
            
            # RUC
            ruc = issuer_data.get('ruc') or ''
            self.ticket_preview.insert(tk.END, f"RUC: {ruc}\n", "center")
            
            # Name
            name = issuer_data.get('name') or ''
            self.ticket_preview.insert(tk.END, name + "\n", "center")
            
            # Address
            address_parts = [issuer_data.get('address') or '']
            district = issuer_data.get('district')
            province = issuer_data.get('province')
            department = issuer_data.get('department')
            
            if district: address_parts.append(district)
            if province: address_parts.append(province)
            if department: address_parts.append(department)
            
            full_address = " ".join([p for p in address_parts if p])
            address_lines = textwrap.wrap(full_address, width=42)
            for line in address_lines:
                self.ticket_preview.insert(tk.END, line + "\n", "center")
                
            # Initial Greeting
            initial_greeting = issuer_data.get('initial_greeting')
            if initial_greeting:
                greeting_lines = textwrap.wrap(initial_greeting, width=42)
                for line in greeting_lines:
                    self.ticket_preview.insert(tk.END, line + "\n", "center")

        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")

        # --- DOCUMENT INFO ---
        doc_type = self.doc_type_var.get()
        self.ticket_preview.insert(tk.END, doc_type + "\n", ("center", "bold"))
        
        series = self.doc_series_var.get()
        number = self.doc_number_var.get()
        if series and number:
            self.ticket_preview.insert(tk.END, f"{series}-{number}\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
            
        # --- EMISSION INFO ---
        self.ticket_preview.insert(tk.END, f"EMISIÓN: {self.datetime_var.get()}\n", "center")
        
        doc_num = self.customer_doc_var.get()
        if doc_num:
            label = "RUC" if len(doc_num) == 11 else "DNI"
            self.ticket_preview.insert(tk.END, f"{label}: {doc_num}\n", "center")
            
        customer_name = self.customer_name_var.get()
        if customer_name:
            self.ticket_preview.insert(tk.END, f"CLIENTE: {customer_name}\n", "center")
            
        customer_address = self.customer_address_var.get()
        if customer_address:
            # Wrap address if long
            addr_str = f"DIRECCIÓN: {customer_address}"
            addr_lines = textwrap.wrap(addr_str, width=42)
            for line in addr_lines:
                self.ticket_preview.insert(tk.END, line + "\n", "center")
            
        if not is_proforma:
            self.ticket_preview.insert(tk.END, "MONEDA: SOL(PEN)\n", "center")
            self.ticket_preview.insert(tk.END, "FORMA DE PAGO: CONTADO\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # --- ITEMS ---
        header = "PRODUCTO      PESO    P.UNIT   P.TOTAL"
        self.ticket_preview.insert(tk.END, header + "\n", ("center", "bold"))
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        for item in self.cart:
            # Line 1: Description (Left Aligned with indent to match header)
            desc = item['name']
            desc_lines = textwrap.wrap(desc, width=40)
            for line in desc_lines:
                self.ticket_preview.insert(tk.END, "  " + line + "\n", "left")
            
            # Line 2: Qty+UM (PESO) Price Subtotal (Centered)
            qty_um = f"{item['quantity']:.2f} {item['unit_of_measure'][:3]}"
            price = f"{item['price']:.2f}"
            subtotal = f"{item['subtotal']:.2f}"
            
            line2 = f"{qty_um}".center(16) + f"{price}".rjust(10) + f"{subtotal}".rjust(16)
            self.ticket_preview.insert(tk.END, line2 + "\n", "center")
            self.ticket_preview.insert(tk.END, "." * 42 + "\n", "center")
            
        # --- TOTALS ---
        if not is_proforma:
            total = self.total
            subtotal = total / 1.18
            igv = total - subtotal
            
            self.ticket_preview.insert(tk.END, f"Total Op.Gravadas: S/ {subtotal:.2f}\n", "center")
            self.ticket_preview.insert(tk.END, f"Total I.G.V 18%:   S/ {igv:.2f}\n", "center")
            
        # TOTAL A PAGAR (Inverse + Centered + Larger)
        total_str = f"TOTAL A PAGAR: S/ {self.total:,.2f}"
        self.ticket_preview.insert(tk.END, total_str.center(42) + "\n", ("center", "inverse", "large"))
        
        # Amount in letters
        total_letras = self._number_to_text(self.total)
        letras_lines = textwrap.wrap(total_letras, width=42)
        for line in letras_lines:
            self.ticket_preview.insert(tk.END, line + "\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # --- FOOTER ---
        if not is_proforma:
            self.ticket_preview.insert(tk.END, f"Representación Impresa de la\n", "center")
            self.ticket_preview.insert(tk.END, f"{doc_type}.\n", "center")
            self.ticket_preview.insert(tk.END, "Consultar su validez en https://shorturl.at/WoJnM\n", "center")
            
            if issuer_data:
                self.ticket_preview.insert(tk.END, "\n[CÓDIGO QR]\n", "center")
                self.ticket_preview.insert(tk.END, f"Resumen: HASH_DUMMY_VALUE\n", "center")
                

        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")

        # Bank Accounts (Larger Font)
        # Bank Accounts (Larger Font)
        if issuer_data:
            bank_accounts = issuer_data.get('bank_accounts')
            if bank_accounts:
                self.ticket_preview.insert(tk.END, "\n", "center")
                # Wrap bank accounts
                ba_lines = textwrap.wrap(bank_accounts, width=25)
                for line in ba_lines:
                    self.ticket_preview.insert(tk.END, line + "\n", ("center", "large"))
            
            # Final Greeting
            final_greeting = issuer_data.get('final_greeting')
            if final_greeting:
                self.ticket_preview.insert(tk.END, "\n", "center")
                greeting_lines = textwrap.wrap(final_greeting, width=35)
                for line in greeting_lines:
                    self.ticket_preview.insert(tk.END, line + "\n", "center")

        self.ticket_preview.config(state="disabled")

    def _get_escpos_image_bytes(self, image_data, max_width=384):
        """
        Convierte una imagen (bytes o PIL Image) a comandos ESC/POS raster bit image (GS v 0).
        max_width: Ancho máximo en puntos (default 384 para 58mm, usar 512 o 576 para 80mm).
        """
        try:
            if isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, Image.Image):
                img = image_data
            else:
                return b""

            # Convertir a blanco y negro (1-bit)
            if img.mode != '1':
                img = img.convert('RGB')
                # Resize manteniendo aspecto si es muy grande
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Dithering para mejor calidad en logos complejos
                img = img.convert('1')

            width, height = img.size
            
            # Ancho en bytes (debe ser múltiplo de 8)
            x_bytes = (width + 7) // 8
            
            # Header ESC/POS: GS v 0 m xL xH yL yH
            # m=0 (normal), xL, xH = width bytes, yL, yH = height dots
            header = b'\x1dv0\x00' + \
                     x_bytes.to_bytes(2, 'little') + \
                     height.to_bytes(2, 'little')
            
            # Raster data
            raster_data = bytearray()
            for y in range(height):
                row_bytes = 0
                for x_byte in range(x_bytes):
                    byte_val = 0
                    for bit in range(8):
                        x = x_byte * 8 + bit
                        if x < width:
                            # 0 = blanco, 1 = negro en PIL '1' mode?
                            # En ESC/POS: 1 = print dot (negro), 0 = no print (blanco)
                            # PIL '1': 0=black, 255=white usually, but let's check getpixel
                            pixel = img.getpixel((x, y))
                            # Si pixel es 0 (negro), ponemos 1 bit. Si pixel > 0 (blanco), ponemos 0 bit.
                            if pixel == 0: 
                                byte_val |= (1 << (7 - bit))
                    raster_data.append(byte_val)
            
            return header + raster_data + b'\n' # Salto de línea después de imagen
        except Exception as e:
            print(f"Error procesando imagen ESC/POS: {e}")
            return b""

    def _generate_escpos_ticket(self):
        """Genera el contenido del ticket en comandos ESC/POS."""
        # Constantes ESC/POS
        INIT = b'\x1b@'
        CODEPAGE_850 = b'\x1bt\x02' # PC850 Multilingual
        
        ALIGN_LEFT = b'\x1ba\x00'
        ALIGN_CENTER = b'\x1ba\x01'
        ALIGN_RIGHT = b'\x1ba\x02'
        
        BOLD_ON = b'\x1bE\x01'
        BOLD_OFF = b'\x1bE\x00'
        INVERSE_ON = b'\x1dB\x01'
        INVERSE_OFF = b'\x1dB\x00'
        
        # Tamaños de fuente (GS ! n)
        # n = 0-255. Bits 0-3 width, 4-7 height.
        # 0x00 = Normal
        # 0x10 = Double Height (16 decimal)
        # 0x01 = Double Width
        # 0x11 = Double Width & Height (17 decimal)
        SIZE_NORMAL = b'\x1d!\x00'
        SIZE_2H = b'\x1d!\x10' # Doble Alto
        SIZE_2W = b'\x1d!\x01' # Doble Ancho
        SIZE_2X = b'\x1d!\x11' # Doble Alto y Ancho
        
        CUT = b'\x1dV\x41\x00'
        
        # Helper para codificar texto
        def text(s):
            return s.encode('cp850', errors='replace')
            
        buffer = bytearray()
        buffer.extend(INIT)
        buffer.extend(CODEPAGE_850)
        
        issuer_name = self.issuer_var.get()
        selected_address = self.address_var.get()
        
        issuer_data = None
        if issuer_name in self.issuers:
            for issuer in self.issuers[issuer_name]:
                if issuer['address'] == selected_address:
                    issuer_data = issuer
                    break
        


        # --- NUMIER FORMAT CHECK ---
        import textwrap
        current_doc_type = getattr(self, 'last_doc_type', self.doc_type_var.get())
        if not current_doc_type: current_doc_type = ""
        is_proforma = "NOTA DE VENTA" in current_doc_type.upper()
        
        # Fallback using document number prefix
        if not is_proforma and hasattr(self, 'last_sale_document_number') and self.last_sale_document_number:
            if self.last_sale_document_number.startswith("NV"):
                is_proforma = True
        print_format_nv = config_manager.load_setting('print_format_nv', 'APISUNAT')
        
        if is_proforma and print_format_nv == "NUMIER":
             # ==========================================
             #              NUMIER FORMAT
             # ==========================================
             
             # --- HEADER ---
             buffer.extend(ALIGN_CENTER)
             
             # Commercial Name (***NOMBRE***)
             if issuer_data:
                 commercial_name = issuer_data.get('commercial_name') or ''
                 if commercial_name:
                     buffer.extend(BOLD_ON + text(f"***{commercial_name}***\n") + BOLD_OFF)
                 
                 # Address
                 address = issuer_data.get('address') or ''
                 district = issuer_data.get('district') or ''
                 
                 full_address_parts = [address]
                 if district: full_address_parts.append(district)
                 full_address = " ".join([p for p in full_address_parts if p])
                 
                 if full_address:
                     # Wrap address
                     addr_lines = textwrap.wrap(full_address, width=42)
                     for line in addr_lines:
                         buffer.extend(text(line + "\n"))
             
             # DATE AND TIME
             now = datetime.now()
             date_str = now.strftime('%d-%m-%Y')
             time_str = now.strftime('%H:%M:%S')
             
             buffer.extend(text(f"FECHA:{date_str}\n"))
             
             # USER AND TIME
             current_user = "ADMIN"
             try:
                 current_user = self.master.master.master.username.upper() 
             except:
                 pass
             
             buffer.extend(text(f"USUARIO: {current_user} HORA:{time_str}\n"))
             
             # DOC NUMBER
             # Prefer the just-generated number if available (e.g. from auto-print)
             if hasattr(self, 'last_sale_document_number') and self.last_sale_document_number:
                 buffer.extend(text(f"N.DOC: {self.last_sale_document_number}\n"))
             else:
                 series = self.doc_series_var.get()
                 number = self.doc_number_var.get()
                 if series and number:
                     buffer.extend(text(f"N.DOC: {series}-{number}\n"))
                 
             # DOCUMENT TITLE
             buffer.extend(BOLD_ON + text("NOTA DE VENTA\n") + BOLD_OFF)
             
             # ITEMS HEADER
             # 42 chars:
             # PROD (20) | UND (3) | PRC (8) | TOT (9)
             # "12345678901234567890 123 12345.78 123456.89"
             # "PRODUCTO             UND   PRECIO   IMPORTE"
             header = "PRODUCTO             UND   PRECIO   IMPORTE"
             buffer.extend(text(header + "\n"))
             buffer.extend(text("-" * 42 + "\n"))
             
             # ITEMS
             for item in self.cart:
                 # Single Line Format
                 # Name: Truncate to 20 chars
                 name = item['name'][:20].ljust(20)
                 
                 # Qty (if integer show int, else float)
                 # Wait, user said "und", usually implies Unit of Measure or Quantity?
                 # Standard Numier request says "und". I will assume Quantity.
                 # If space is tight, maybe just Qty?
                 qty_val = item['quantity']
                 qty_str = f"{qty_val:.0f}" if float(qty_val).is_integer() else f"{qty_val:.1f}"
                 # Limit quantity string to 4 chars
                 qty_str = qty_str[:3].center(3)
                 
                 price_val = item['price']
                 price_str = f"{price_val:.2f}".rjust(8)
                 
                 subtotal_val = item['subtotal']
                 subtotal_str = f"{subtotal_val:.2f}".rjust(9)

                 # Layout: Name(20) Space(1) Qty(3) Space(1) Price(8) Space(0) Subtotal(9)
                 # Total: 20+1+3+1+8+0+9 = 42
                 
                 line = f"{name} {qty_str} {price_str}{subtotal_str}"
                 buffer.extend(text(line + "\n"))
                 
             buffer.extend(text("-" * 42 + "\n"))
             
             # TOTAL
             total_label = "TOTAL     S/"
             total_val = f"{self.total:.2f}"
             total_line = total_label.rjust(25) + total_val.rjust(16)
             buffer.extend(BOLD_ON + text(total_line + "\n") + BOLD_OFF)
             
             buffer.extend(text("-" * 42 + "\n"))
             
             # INFO: PAYMENT & DISCOUNT
             # Retrieve stored last payment info
             payment_method = getattr(self, 'last_payment_method', 'EFECTIVO')
             amount_received = getattr(self, 'last_amount_received', self.total)
             change = getattr(self, 'last_change', 0.0)
             discount_text = getattr(self, 'last_discount_text', '')
             
             if discount_text:
                 buffer.extend(ALIGN_LEFT)
                 buffer.extend(text(f"{discount_text}\n"))
             
             buffer.extend(ALIGN_LEFT)
             buffer.extend(text(f"PAGO: {payment_method}\n"))
             buffer.extend(text(f"RECIBIDO: S/ {amount_received:.2f}\n"))
             buffer.extend(text(f"VUELTO:   S/ {change:.2f}\n"))
             
             # FOOTER MESSAGE
             buffer.extend(ALIGN_CENTER)
             buffer.extend(text("NOTA DE VENTA CANJEAR POR BOLETA/FACTURA\n"))
             
             buffer.extend(CUT)
             return buffer
             
        # ==========================================
        #              END NUMIER FORMAT
        # ==========================================

        import textwrap

        # --- HEADER ---
        buffer.extend(ALIGN_CENTER)

        if issuer_data:
            # LOGO
            logo_data = issuer_data.get('logo')
            if logo_data:
                logo_bytes = self._get_escpos_image_bytes(logo_data, max_width=384)
                buffer.extend(logo_bytes)
            
            # Nombre Comercial
            commercial_name = issuer_data.get('commercial_name') or ''
            if commercial_name:
                buffer.extend(BOLD_ON + text(commercial_name + "\n") + BOLD_OFF)
            
            # RUC
            ruc = issuer_data.get('ruc') or ''
            buffer.extend(text(f"RUC: {ruc}\n"))
            
            # Razón Social
            name = issuer_data.get('name') or ''
            buffer.extend(text(name + "\n"))
            
            # Dirección
            address_parts = [issuer_data.get('address') or '']
            district = issuer_data.get('district')
            province = issuer_data.get('province')
            department = issuer_data.get('department')
            
            if district: address_parts.append(district)
            if province: address_parts.append(province)
            if department: address_parts.append(department)
            
            full_address = " ".join([p for p in address_parts if p])
            address_lines = textwrap.wrap(full_address, width=42)
            for line in address_lines:
                buffer.extend(text(line + "\n"))
                
            # Saludo Inicial
            initial_greeting = issuer_data.get('initial_greeting')
            if initial_greeting:
                greeting_lines = textwrap.wrap(initial_greeting, width=42)
                for line in greeting_lines:
                    buffer.extend(text(line + "\n"))

        buffer.extend(text("-" * 42 + "\n"))

        # --- DOCUMENT INFO ---
        if hasattr(self, 'last_doc_type') and self.last_doc_type:
             doc_type = self.last_doc_type
        else:
             doc_type = self.doc_type_var.get()
        
        buffer.extend(BOLD_ON + text(doc_type + "\n") + BOLD_OFF)
        
        if hasattr(self, 'last_sale_document_number') and self.last_sale_document_number:
            buffer.extend(text(f"{self.last_sale_document_number}\n"))
        else:
            series = self.doc_series_var.get()
            number = self.doc_number_var.get()
            if series and number:
                buffer.extend(text(f"{series}-{number}\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
            
        # --- EMISSION INFO ---
        buffer.extend(text(f"EMISIÓN: {self.datetime_var.get()}\n"))
        
        doc_num = self.customer_doc_var.get()
        if doc_num:
            label = "RUC" if len(doc_num) == 11 else "DNI"
            buffer.extend(text(f"{label}: {doc_num}\n"))
            
        customer_name = self.customer_name_var.get()
        if customer_name:
            buffer.extend(text(f"CLIENTE: {customer_name}\n"))
            
        customer_address = self.customer_address_var.get()
        if customer_address:
            addr_str = f"DIRECCIÓN: {customer_address}"
            addr_lines = textwrap.wrap(addr_str, width=42)
            for line in addr_lines:
                buffer.extend(text(line + "\n"))
            
        if not is_proforma:
            buffer.extend(text("MONEDA: SOL(PEN)\n"))
            buffer.extend(text("FORMA DE PAGO: CONTADO\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS ---
        # User requested centering for items
        buffer.extend(ALIGN_CENTER)
        header = "PRODUCTO      PESO    P.UNIT   P.TOTAL"
        buffer.extend(BOLD_ON + text(header + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        for item in self.cart:
            # Line 1: Description (Left Aligned with indent)
            buffer.extend(ALIGN_LEFT)
            desc = item['name']
            # Indent 2 spaces, wrap width reduced
            desc_lines = textwrap.wrap(desc, width=40)
            for line in desc_lines:
                buffer.extend(text("      " + line + "\n"))
            
            # Line 2: Qty+UM (PESO) Price Subtotal (Centered)
            buffer.extend(ALIGN_CENTER)
            qty_um = f"{item['quantity']:.2f} {item['unit_of_measure'][:3]}"
            price = f"{item['price']:.2f}"
            subtotal = f"{item['subtotal']:.2f}"
            
            line2 = f"{qty_um}".center(16) + f"{price}".rjust(10) + f"{subtotal}".rjust(16)
            buffer.extend(text(line2 + "\n"))
            buffer.extend(text("." * 42 + "\n"))
            
        # --- TOTALS ---
        buffer.extend(ALIGN_CENTER)
        if not is_proforma:
            total = self.total
            subtotal = total / 1.18
            igv = total - subtotal
            
            buffer.extend(text(f"Total Op.Gravadas: S/ {subtotal:.2f}\n"))
            buffer.extend(text(f"Total I.G.V 18%:   S/ {igv:.2f}\n"))
            
        # TOTAL A PAGAR (Inverse + Centered + Larger)
        total_str = f"TOTAL A PAGAR: S/ {self.total:,.2f}"
        # Usar SIZE_2X para el total
        buffer.extend(SIZE_2X + INVERSE_ON + text(total_str.center(21) + "\n") + INVERSE_OFF + SIZE_NORMAL)
        # Nota: center(21) porque al ser doble ancho, caben la mitad de caracteres (42/2 = 21)
        
        # Amount in letters
        total_letras = self._number_to_text(self.total)
        letras_lines = textwrap.wrap(total_letras, width=42)
        for line in letras_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- FOOTER ---
        if not is_proforma:
            buffer.extend(text(f"Representación Impresa de la\n"))
            buffer.extend(text(f"{doc_type}.\n"))
            buffer.extend(text("Consultar su validez en https://shorturl.at/WoJnM\n"))
            
            if issuer_data:
                ruc_emisor = issuer_data.get('ruc', '')
                tipo_cpe = "01" if "FACTURA" in doc_type else "03" if "BOLETA" in doc_type else "00"
                serie = self.doc_series_var.get()
                numero = self.doc_number_var.get()
                fecha = datetime.now().strftime('%Y-%m-%d')
                total_qr = f"{self.total:.2f}"
                igv_qr = f"{(self.total - (self.total/1.18)):.2f}"
                
                qr_content = f"{ruc_emisor}|{tipo_cpe}|{serie}|{numero}|{igv_qr}|{total_qr}|{fecha}|6|{doc_num}|HASH_DUMMY|"
                
                # Generar QR Real
                try:
                    # Usar box_size mayor y dejar que _get_escpos_image_bytes haga resize
                    qr = qrcode.QRCode(version=1, box_size=10, border=1)
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Imprimir QR
                    buffer.extend(text("\n")) # Espacio antes del QR
                    qr_bytes = self._get_escpos_image_bytes(qr_img, max_width=250)
                    buffer.extend(qr_bytes)
                except Exception as e:
                    print(f"Error generando QR: {e}")
                    buffer.extend(text("[ERROR QR]\n"))

                buffer.extend(text(f"Resumen: HASH_DUMMY_VALUE\n"))
                

        buffer.extend(text("-" * 42 + "\n"))

        # Bank Accounts (Larger Font)
        if issuer_data:
            bank_accounts = issuer_data.get('bank_accounts')
            if bank_accounts:
                # Usar SIZE_2H (Doble Alto) para cuentas bancarias
                # Wrap manually to avoid printer cutting words
                ba_lines = textwrap.wrap(bank_accounts, width=25)
                for line in ba_lines:
                    buffer.extend(SIZE_2H + text(line + "\n") + SIZE_NORMAL)
                
            # Final Greeting
            final_greeting = issuer_data.get('final_greeting')
            if final_greeting:
                buffer.extend(text("\n"))
                greeting_lines = textwrap.wrap(final_greeting, width=45)
                for line in greeting_lines:
                    buffer.extend(text(line + "\n"))
                
        buffer.extend(CUT)
        return buffer

    def print_ticket(self):
        if win32print is None:
            messagebox.showerror("Error de Impresión", "El módulo 'pywin32' es necesario para imprimir. Por favor, instálelo.", parent=self.winfo_toplevel())
            return
        printer_name = config_manager.load_setting('default_printer')
        if not printer_name:
            messagebox.showwarning("Impresora no Configurada", "Por favor, seleccione una impresora por defecto en el módulo de Configuración.", parent=self.winfo_toplevel())
            return
        
        # --- Verificación para impresoras PDF ---
        if "MICROSOFT PRINT TO PDF" in printer_name.upper():
            messagebox.showerror(
                "Impresora no Compatible",
                "La impresora 'Microsoft Print to PDF' no es compatible con la impresión de tickets en formato RAW.\n"
                "Por favor, seleccione una impresora térmica real para imprimir tickets.",
                parent=self.winfo_toplevel()
            )
            return
        
        try:
            data_to_send = self._generate_escpos_ticket()
            
            h_printer = win32print.OpenPrinter(printer_name)
            try:
                h_job = win32print.StartDocPrinter(h_printer, 1, ("Ticket de Venta", None, "RAW"))
                try:
                    win32print.StartPagePrinter(h_printer)
                    win32print.WritePrinter(h_printer, data_to_send)
                    win32print.EndPagePrinter(h_printer)
                finally:
                    win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
            # messagebox.showinfo("Impresión", "El ticket ha sido enviado a la impresora.", parent=self.winfo_toplevel()) # REMOVED PER USER REQUEST
        except Exception as e:
            messagebox.showerror("Error de Impresión", f"No se pudo imprimir el ticket.\nError: {e}", parent=self.winfo_toplevel())

    def update_total(self):
        self.total = sum(item['subtotal'] for item in self.cart)
        self.total_label.config(text=f"Total: S/ {self.total:.2f}")
        
        # --- Calculate Breakdown for Footer ---
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        difference = self.total - base_total
        
        # Update Footer Labels
        if difference > 0.001: # Surcharge
            self.footer_surcharge_value.config(text=f"S/ {difference:.2f}")
            self.frame_surcharge.pack(side="left", padx=10, after=self.frame_items) # Ensure order
            self.frame_discount.pack_forget()
        elif difference < -0.001: # Discount
            self.footer_discount_value.config(text=f"S/ {abs(difference):.2f}")
            self.frame_discount.pack(side="left", padx=10, after=self.frame_items) # Ensure order
            self.frame_surcharge.pack_forget()
            self.frame_surcharge.pack_forget()
            self.frame_discount.pack_forget()
            
        self.footer_total_value.config(text=f"S/ {self.total:.2f}")
        
        # Update Items Count
        total_qty = sum(item['quantity'] for item in self.cart)
        if total_qty.is_integer():
             self.footer_items_value.config(text=f"{int(total_qty)}")
        else:
             self.footer_items_value.config(text=f"{total_qty:.2f}")

        self.calculate_change()
        self.update_ticket_preview()
        self.save_state()

    def update_datetime(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.datetime_var.set(now)
        self.after(1000, self.update_datetime)

    def calculate_change(self, *args):
        try:
            paid1 = float(self.amount_paid_var.get() or 0.0)
            paid2 = float(self.amount_paid_var2.get() or 0.0)
            anulado = getattr(self, 'current_anulado', 0.0)
            
            # Logic: Anulado compensa la falta de pago o cancela la deuda.
            # Según usuario: "Vuelto: S/ 0.00 ya que se estaría compensando" (Si anualdo = Total).
            # Entonces, Anulado se suma a lo Pagado para calcular si se cubre el Total.
            # Change = (Pagado + Anulado) - TotalExpected
            
            total_paid = paid1 + paid2 + anulado
            change = total_paid - self.total
            
            anulado_msg = f" (Anulado: S/ {anulado:.2f})" if anulado > 0 else ""
            
            if change >= 0:
                self.change_label.config(text=f"Vuelto: S/ {change:.2f}{anulado_msg}", bootstyle="success")
            else:
                self.change_label.config(text=f"Faltante: S/ {abs(change):.2f}{anulado_msg}", bootstyle="danger")
        except tk.TclError:
            self.change_label.config(text="Vuelto: S/ 0.00", bootstyle="success")

    def open_anulado_dialog(self):
        issuer_id = config_manager.load_caja_setting(self.caja_id, 'last_issuer_id')
        address = config_manager.load_caja_setting(self.caja_id, 'last_address')
        
        if not issuer_id or not address:
            # Try from UI
            issuer_name = self.issuer_var.get()
            address_val = self.address_var.get()
            if issuer_name and address_val:
                 # Find ID
                 if issuer_name in self.issuers:
                    for i_data in self.issuers[issuer_name]:
                        if i_data['address'] == address_val:
                            issuer_id = i_data['id']
                            break

        if not issuer_id or not address:
             messagebox.showerror("Error", "Seleccione Emisor y Dirección primero", parent=self)
             return

        from movements_touch_dialog import TouchMovementDialog
        TouchMovementDialog(self, "ANULADO", issuer_id, address, on_complete=self.on_anulado_complete)

    def on_anulado_complete(self, amount):
        print(f"DEBUG: on_anulado_complete triggered with amount: {amount}")
        try:
            if not hasattr(self, 'current_anulado'): self.current_anulado = 0.0
            self.current_anulado += amount
            
            # Verificar si existe la etiqueta antes de configurar
            if hasattr(self, 'anulado_label') and self.anulado_label.winfo_exists():
                self.anulado_label.config(text=f"Anulado: S/ {self.current_anulado:.2f}")
            else:
                print("DEBUG: anulado_label does not exist or is destroyed.")
                
            self.calculate_change() 
        except Exception as e:
            print(f"Error updating anulado: {e}")

    def process_sale(self):
        doc_type_full = self.doc_type_var.get()
        doc_type_mapping = {
            "NOTA DE VENTA": "NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA": "BOLETA", "FACTURA ELECTRÓNICA": "FACTURA",
            "NOTA DE CRÉDITO (BOLETA)": "NOTA_CREDITO_BOLETA", "NOTA DE CRÉDITO (FACTURA)": "NOTA_CREDITO_FACTURA",
            "GUÍA DE REMISIÓN ELECTRÓNICA": "GUIA_REMISION"
        }
        internal_doc_type = doc_type_mapping.get(doc_type_full, "UNKNOWN")
        issuer_name = self.issuer_var.get()
        selected_address = self.address_var.get()
        if not issuer_name or not selected_address:
            messagebox.showerror("Error", "Debe seleccionar un emisor y una dirección.", parent=self.winfo_toplevel())
            return
        if not self.cart:
            messagebox.showinfo("Información", "El carrito está vacío.", parent=self.winfo_toplevel())
            return
        if internal_doc_type == "FACTURA" and (not self.customer_doc_var.get() or len(self.customer_doc_var.get()) != 11):
             messagebox.showerror("Error de Validación", "Para FACTURA, el cliente debe tener un RUC de 11 dígitos.", parent=self.winfo_toplevel())
             return
        issuer_id = None
        if issuer_name in self.issuers:
            for issuer_data in self.issuers[issuer_name]:
                if issuer_data['address'] == selected_address:
                    issuer_id = issuer_data['id']
                    break
        if not issuer_id:
            messagebox.showerror("Error Crítico", "El emisor seleccionado ya no es válido.", parent=self.winfo_toplevel())
            return
        # Use get_correlative (PEEK) instead of get_next_correlative (INCREMENT)
        series, current_number = database.get_correlative(issuer_id, internal_doc_type)
        if not series:
             if internal_doc_type == "NOTA DE VENTA": series = "NV01"
             
        next_preview_number = current_number + 1
        
        # ... (rest of validation) ...
        
        customer_name = self.customer_name_var.get().strip()
        customer_phone = self.customer_phone_var.get().strip()
        customer_address = self.customer_address_var.get().strip()
        observations = self.observations_text.get("1.0", tk.END).strip()
        customer_doc = self.customer_doc_var.get().strip()
        
        # --- Validaciones de Monto ---
        # 1. Ventas > 700 Soles
        if self.total > 700:
            if not customer_doc or not customer_name:
                messagebox.showerror("Error de Validación", "Para ventas mayores a S/ 700, el DNI/RUC y Nombre son obligatorios.", parent=self.winfo_toplevel())
                return
            if len(customer_doc) == 11 and not customer_address:
                 messagebox.showerror("Error de Validación", "Para ventas con RUC mayores a S/ 700, la dirección es obligatoria.", parent=self.winfo_toplevel())
                 return

        # 2. Ventas > 2000 Soles (Bancarización)
        if self.total > 2000 and internal_doc_type in ["BOLETA", "FACTURA"]:
             if not messagebox.askyesno("Advertencia de Bancarización", "Esta seguro de emitir el comprobante electrónico ya que supera los 2000 soles y necesita ser bancarizado?", parent=self.winfo_toplevel()):
                 return
        customer_id = database.get_or_create_customer(customer_doc, customer_name, customer_phone, customer_address)
        sale_date = self.datetime_var.get()
        
        # PREVIEW Number for Prompt
        sale_document_number_preview = f"{series}-{next_preview_number}"
        
        payment_method = self.payment_method_var.get()
        amount_paid = self.amount_paid_var.get()
        payment_method2 = self.payment_method_var2.get()
        amount_paid2 = self.amount_paid_var2.get()
        payment_destination = self.payment_method_combo.get() # Assuming the combobox value is the destination
        
        # --- Store Payment Info for Printing ---
        self.last_payment_method = payment_method
        if amount_paid2 > 0:
             self.last_payment_method += f" + {payment_method2}"
        self.last_amount_received = amount_paid + amount_paid2
        self.last_change = self.last_amount_received - self.total if self.last_amount_received >= self.total else 0.0
        
        # --- Store Document Number (Temporary Preview) ---
        self.last_sale_document_number = sale_document_number_preview
        self.last_doc_type = doc_type_full 
        
        # --- Store Discount/Adic ---
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        difference = self.total - base_total
        self.last_discount_text = ""
        if difference > 0.001:
            self.last_discount_text = f"ADIC.: S/ {difference:.2f}"
        elif difference < -0.001:
            self.last_discount_text = f"DSCTO.: S/ {abs(difference):.2f}"
        
        if messagebox.askyesno("Confirmar Venta", f"Se generará el documento '{sale_document_number_preview}' por un total de S/ {self.total:.2f}. ¿Desea continuar?", parent=self.winfo_toplevel()):
            try:
                # NOW Increment the counter Transactionally
                final_series, final_number = database.get_next_correlative(issuer_id, internal_doc_type)
                
                # Use the actual reserved number
                sale_document_number = f"{final_series}-{final_number}"
                
                # Update stored doc number for printing with the REAL one
                self.last_sale_document_number = sale_document_number
                
                # Determine Document Type for Database Storage
                db_doc_type = internal_doc_type
                if internal_doc_type == "NOTA DE VENTA" and doc_type_full == "NOTA DE VENTA":
                    db_doc_type = "NOTA DE VENTA"

                database.record_sale(issuer_id, customer_id, self.total, self.cart, sale_date, observations, db_doc_type, sale_document_number, payment_method, amount_paid, payment_method2, amount_paid2, payment_destination, customer_address)
                if internal_doc_type in ["BOLETA", "FACTURA", "NOTA DE VENTA"]:
                    for item in self.cart: database.decrease_product_stock(item['id'], item['quantity'])
                elif internal_doc_type in ["NOTA_CREDITO_BOLETA", "NOTA_CREDITO_FACTURA"]:
                    for item in self.cart: database.increase_product_stock(item['id'], item['quantity'])
                config_manager.save_setting('last_issuer_id', issuer_id)
                # messagebox.showinfo("Éxito", f"{doc_type_full} generada con el número {sale_document_number}.", parent=self.winfo_toplevel()) # Removed or keep? User might want confirmation
                # Just show message, then print, then reset.
                messagebox.showinfo("Éxito", f"{doc_type_full} generada con el número {sale_document_number}.", parent=self.winfo_toplevel())
                
                # --- AUTO PRINT ---
                # self.print_ticket()
                
                self.reset_system()
                self.load_products_from_db()
            except Exception as e:
                messagebox.showerror("Error Crítico", f"Ocurrió un error al procesar la venta.\n{e}", parent=self.winfo_toplevel())

    def clear_inputs(self, clear_customer=False):
        self.product_var.set("")
        self.quantity_var.set(1.0)
        self.price_var.set(0.0)
        self.unit_of_measure_var.set("")
        self.stock_label.config(text="Stock: -")
        if clear_customer:
            self.amount_paid_var.set(0.0)
            self.payment_method_var2.set("NINGUNO")
            self.amount_paid_var2.set(0.0)
            self.customer_doc_var.set("")
            self.customer_name_var.set("")
            self.customer_phone_var.set("")
            self.customer_address_var.set("")
            self.observations_text.delete("1.0", tk.END)
            self.doc_type_var.set("NOTA DE VENTA")
            self.on_doc_type_select()
        self.product_combo.focus()

    def load_products_from_db(self, issuer_name=None, issuer_address=None):
        all_products_rows = database.get_all_products(issuer_name, issuer_address)
        self.products = {row[1]: {'id': row[0], 'price': row[2], 'stock': row[3], 'code': row[4], 'unit_of_measure': row[5]} for row in all_products_rows}
        if hasattr(self, 'product_combo'):
             self.product_combo['values'] = list(self.products.keys())
             self.product_var.set("") # Clear selection when reloading
             self.stock_label.config(text="Stock: -")
             self.price_var.set(0.0)
             self.quantity_var.set(1.0)
             self.unit_of_measure_var.set("")
        
        # --- Create Code Map for Scanning ---
        self.product_code_map = {}
        for name, data in self.products.items():
            code = data.get('code')
            if code:
                # Normalize code to string and strip just in case
                code_str = str(code).strip()
                if code_str:
                     self.product_code_map[code_str] = name

    def on_product_select(self, event=None):
        product_name = self.product_var.get()
        if product_name in self.products:
            product_data = self.products[product_name]
            self.stock_label.config(text=f"Stock: {product_data['stock']:.2f}")
            self.price_var.set(f"{product_data['price']:.2f}")
            
            # Map Code -> Description for the Combobox
            um_code = product_data['unit_of_measure']
            um_desc = self.um_code_to_description.get(um_code, um_code) # Fallback to code if not found
            self.unit_of_measure_var.set(um_desc)
            
            self.quantity_entry.focus_set() # Move focus to quantity
            self.quantity_entry.select_range(0, 'end')

    def add_to_cart(self, product=None):
        # --- TRACK OPENING TIME ---
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_opening = config_manager.load_setting("daily_opening_time", "")
        
        # Format: YYYY-MM-DD HH:MM:SS
        update_time = False
        if not last_opening:
            update_time = True
        else:
            try:
                last_date = last_opening.split(" ")[0]
                if last_date != today_str:
                    update_time = True
            except:
                update_time = True
        
        if update_time:
            now_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config_manager.save_setting("daily_opening_time", now_full)
        # ---------------------------

        product_name = self.product_var.get().strip()
        if not product_name:
            messagebox.showerror("Error", "El nombre del producto no puede estar vacío.", parent=self.winfo_toplevel())
            return
            
        unit_of_measure_desc = self.unit_of_measure_var.get().strip()
        if not unit_of_measure_desc:
             messagebox.showerror("Error", "La Unidad de Medida es obligatoria.", parent=self.winfo_toplevel())
             return

        try:
            quantity = self.quantity_var.get()
            price = self.price_var.get()
        except tk.TclError:
            messagebox.showerror("Error", "La cantidad y el precio deben ser números válidos.", parent=self.winfo_toplevel())
            return
            
        if quantity <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0.", parent=self.winfo_toplevel())
            return
            
        if price <= 0:
             messagebox.showerror("Error", "El precio debe ser mayor a 0.", parent=self.winfo_toplevel())
             return

        # Check for Stock Control
        if product_name in self.products:
            allow_negative_stock = config_manager.load_setting('allow_negative_stock', 'No')
            current_stock = self.products[product_name]['stock']
            
            # Si se está editando, debemos sumar la cantidad original al stock disponible para validar correctamente
            if self.editing_item_index is not None:
                # Recuperar cantidad original del item en edición
                original_qty = self.cart[self.editing_item_index]['quantity']
                effective_stock = current_stock + original_qty
            else:
                effective_stock = current_stock

            if allow_negative_stock == "No" and quantity > effective_stock:
                messagebox.showerror("Stock Insuficiente", f"No hay suficiente stock para '{product_name}'.\nStock actual: {effective_stock:.2f}\nSolicitado: {quantity:.2f}", parent=self.winfo_toplevel())
                return

        if product_name not in self.products:
            if messagebox.askyesno("Producto Nuevo", f"El producto '{product_name}' no existe. ¿Desea crearlo?", parent=self.winfo_toplevel()):
                try:
                    # Map Description -> Code for new product
                    um_desc = self.unit_of_measure_var.get()
                    unit_of_measure_code = self.um_description_to_code.get(um_desc, um_desc)
                    
                    # Get Default Operation Type from selected issuer
                    issuer_name = self.issuer_var.get()
                    selected_address = self.address_var.get()
                    default_op_type = "Gravada" # Default fallback
                    
                    if issuer_name in self.issuers:
                        for issuer in self.issuers[issuer_name]:
                            if issuer['address'] == selected_address:
                                default_op_type = issuer.get('default_operation_type', "Gravada")
                                break

                    database.add_product(name=product_name, price=price, stock=0, code="", unit_of_measure=unit_of_measure_code, operation_type=default_op_type, issuer_name=issuer_name, issuer_address=selected_address)
                    self.load_products_from_db(issuer_name, selected_address)
                    messagebox.showinfo("Éxito", f"Producto '{product_name}' creado con Tipo de Operación: {default_op_type}.", parent=self.winfo_toplevel())
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo crear el producto.\n{e}", parent=self.winfo_toplevel())
                    return
            else:
                return
        subtotal = price * quantity
        product_id = self.products[product_name]['id']
        
        # Map Description -> Code for the Cart/Ticket
        # um_desc = self.unit_of_measure_var.get() # Don't re-read, it might be cleared by load_products_from_db
        um_desc = unit_of_measure_desc # Use the one captured at start of function
        unit_of_measure_code = self.um_description_to_code.get(um_desc, um_desc) # Fallback to desc if not found (shouldn't happen if readonly)

        # Capture original price for tracking
        original_price = self.products[product_name]['price']

        if self.editing_item_index is not None:
            self.cart[self.editing_item_index] = {"id": product_id, "name": product_name, "quantity": quantity, "price": price, "subtotal": subtotal, "unit_of_measure": unit_of_measure_code, "original_price": original_price}
            selected_item_id = self.cart_tree.get_children()[self.editing_item_index]
            self.cart_tree.item(selected_item_id, values=(product_name, f"{quantity:.2f}", unit_of_measure_code, f"{price:.2f}", f"{subtotal:.2f}"))
            self.editing_item_index = None
            self.add_button.config(text="✚ Añadir al Carrito")
        else:
            self.cart.append({"id": product_id, "name": product_name, "quantity": quantity, "price": price, "subtotal": subtotal, "unit_of_measure": unit_of_measure_code, "original_price": original_price})
            self.cart_tree.insert("", tk.END, values=(product_name, f"{quantity:.2f}", unit_of_measure_code, f"{price:.2f}", f"{subtotal:.2f}"))
        self.update_total()
        self.clear_inputs(clear_customer=False)
        self.update_total()
        self.clear_inputs(clear_customer=False)
        self.update_ticket_preview()
        
        # --- Update Stock UI ---
        if product_name in self.products:
            self.products[product_name]['stock'] -= quantity
            # If the product is currently selected in the combobox, update the label
            if self.product_var.get() == product_name:
                 self.stock_label.config(text=f"Stock: {self.products[product_name]['stock']:.2f}")

    def remove_from_cart(self):
        selected_item = self.cart_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sin Selección", "Seleccione un producto del carrito para eliminar.", parent=self.winfo_toplevel())
            return
        try:
            item_index = self.cart_tree.index(selected_item)
            item_data = self.cart[item_index]
            
            # --- Update Stock UI ---
            product_name = item_data['name']
            quantity = item_data['quantity']
            if product_name in self.products:
                self.products[product_name]['stock'] += quantity
                # If currently selected
                if self.product_var.get() == product_name:
                    self.stock_label.config(text=f"Stock: {self.products[product_name]['stock']:.2f}")
            
            del self.cart[item_index]
            self.cart_tree.delete(selected_item)
            self.update_total()
            self.update_ticket_preview()
            self.clear_inputs(clear_customer=False)
            self.add_button.config(text="✚ Añadir al Carrito")
            self.editing_item_index = None

        except IndexError:
            messagebox.showerror("Error", "Hubo un error al eliminar el producto.", parent=self.winfo_toplevel())

    def modify_cart_item(self):
        selected_item = self.cart_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sin Selección", "Seleccione un producto del carrito para modificar.", parent=self.winfo_toplevel())
            return
        try:
            item_index = self.cart_tree.index(selected_item)
            item_data = self.cart[item_index]
            self.product_var.set(item_data['name'])
            self.quantity_var.set(item_data['quantity'])
            self.price_var.set(item_data['price'])
            
            # Map Code -> Description for editing
            um_code = item_data['unit_of_measure']
            um_desc = self.um_code_to_description.get(um_code, um_code)
            self.unit_of_measure_var.set(um_desc)
            
            self.editing_item_index = item_index
            self.add_button.config(text="✓ Actualizar Fila")
        except IndexError:
            messagebox.showerror("Error", "Hubo un error al modificar el producto.", parent=self.winfo_toplevel())

    def reset_system(self):
        # Restore Stock UI
        for item in self.cart:
            product_name = item['name']
            quantity = item['quantity']
            if product_name in self.products:
                self.products[product_name]['stock'] += quantity
                # If currently selected
                if self.product_var.get() == product_name:
                    self.stock_label.config(text=f"Stock: {self.products[product_name]['stock']:.2f}")

        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        self.cart = []
        self.total = 0.0
        self.current_anulado = 0.0
        self.update_total()
        self.clear_inputs(clear_customer=True)
        self.update_ticket_preview()

    def filter_products(self, event):
        typed = self.product_combo.get()
        all_product_names = list(self.products.keys())
        if not typed:
            self.product_combo['values'] = all_product_names
            if event.keysym == 'Down':
                self.product_combo.event_generate('<Down>')
        else:
            # Search by Name OR Code
            filtered_list = []
            for name, data in self.products.items():
                code = data.get('code', '')
                if code is None: code = ""
                
                if typed.lower() in name.lower() or typed.lower() in str(code).lower():
                    filtered_list.append(name)
            
            self.product_combo['values'] = filtered_list
            if filtered_list:
                self.product_combo.event_generate('<Down>')

    def open_cash_count(self):
        # Check permissions
        app = self.winfo_toplevel()
        permissions = getattr(app, 'permissions', [])
        
        if "admin" not in permissions and "Arqueo de Caja" not in permissions:
             import custom_messagebox as messagebox
             messagebox.showwarning("Acceso Denegado", "No tiene permiso para acceder a este módulo.", parent=self)
             return

        import cash_count_view
        cash_count_view.CashCountWindow(self, self.caja_id)

    def save_state(self, event=None):
        try:
            cart_data = []
            for item in self.cart:
                cart_data.append(item)
            
            data = {
                "cart": cart_data,
                "total": self.total,
                "doc_type": self.doc_type_var.get(),
                "payment_method": self.payment_method_var.get(),
                "amount_paid": self.amount_paid_var.get(),
                "payment_method2": self.payment_method_var2.get(),
                "amount_paid2": self.amount_paid_var2.get(),
                "customer": {
                    "doc": self.customer_doc_var.get(),
                    "name": self.customer_name_var.get(),
                    "address": self.customer_address_var.get(),
                    "phone": self.customer_phone_var.get()
                },
                "issuer": self.issuer_var.get(),
                "address": self.address_var.get()
            }
            state_manager.save_box_state(self.caja_id, data)
        except Exception as e:
            print(f"Error saving state: {e}")

    def load_state(self):
        try:
            states = state_manager.load_all_states()
            if str(self.caja_id) in states:
                data = states[str(self.caja_id)]
                
                self.doc_type_var.set(data.get("doc_type", "NOTA DE VENTA"))
                self.payment_method_var.set(data.get("payment_method", "EFECTIVO"))
                self.amount_paid_var.set(data.get("amount_paid", 0.0))
                self.payment_method_var2.set(data.get("payment_method2", "NINGUNO"))
                self.amount_paid_var2.set(data.get("amount_paid2", 0.0))
                self.issuer_var.set(data.get("issuer", ""))
                self.address_var.set(data.get("address", ""))
                
                cust = data.get("customer", {})
                self.customer_doc_var.set(cust.get("doc", ""))
                self.customer_name_var.set(cust.get("name", ""))
                self.customer_address_var.set(cust.get("address", ""))
                self.customer_phone_var.set(cust.get("phone", ""))
                
                self.cart = data.get("cart", [])
                
                for item in self.cart_tree.get_children():
                    self.cart_tree.delete(item)
                    
                for item in self.cart:
                    name = item.get('name', '')
                    qty = item.get('quantity', 0)
                    um = item.get('unit_of_measure', 'NIU')
                    price = item.get('price', 0.0)
                    sub = item.get('subtotal', 0.0)
                    self.cart_tree.insert("", "end", values=(name, f"{qty:.2f}", um, f"{price:.2f}", f"{sub:.2f}"))
                
                self.update_total()
        except Exception as e:
            print(f"Error loading state: {e}")

class SalesWindow(ttk.Toplevel):
    """Ventana para alojar las pestañas de vistas de ventas."""
    def __init__(self, master):
        super().__init__(master)
        self.permissions = getattr(master, 'permissions', [])
        
        # Import colors for styling
        from theme_manager import POS_PRIMARY_DARK, POS_PRIMARY_LIGHT, POS_BG_MAIN, POS_BG_WHITE
        
        self.title("Realizar Venta - TPV Moderno")
        self.state('zoomed')
        self.configure(background=POS_PRIMARY_DARK) # Dark background for the window
        
        # --- Custom Tab Style ---
        style = ttk.Style.get_instance()
        
        # Notebook Style
        style.configure('Sales.TNotebook', background=POS_PRIMARY_DARK, borderwidth=0)
        style.configure('Sales.TNotebook.Tab', 
                        padding=[20, 10], 
                        font=(FONT_FAMILY, 12, 'bold'),
                        background='#0a2240', # Navy (Unselected)
                        foreground='white',
                        borderwidth=0,
                        focuscolor=POS_PRIMARY_DARK) # Remove focus ring
        
        # Adjust map to ensure no white flash on active
        style.map('Sales.TNotebook.Tab',
                  background=[('selected', 'white'), ('active', '#0a2240')], 
                  foreground=[('selected', '#0a2240'), ('active', 'white')],
                  bordercolor=[('selected', '#0a2240'), ('active', '#0a2240')], # Try to force border color if supported
                  lightcolor=[('selected', '#0a2240'), ('active', '#0a2240')], # Remove 3D light effect
                  darkcolor=[('selected', '#0a2240'), ('active', '#0a2240')]) # Remove 3D dark effect

        notebook = ttk.Notebook(self, style='Sales.TNotebook') # Use custom style
        notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Bind tab change event
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        # Determine System Mode
        system_mode = config_manager.load_setting('sales_system_mode', 'Modo teclado')
        
        # Local import to avoid circular dependency
        if system_mode == "Modo táctil":
            try:
                from sales_touch_view import SalesTouchView
                ViewClass = SalesTouchView
            except ImportError as e:
                print(f"Error importing SalesTouchView: {e}")
                ViewClass = SalesView
        else:
            ViewClass = SalesView
        
        self.sales_tabs = []
        try:
            for i in range(5):
                # El tema se hereda a los frames hijos, pero el frame background debe coincidir con el tab active (white) o el POS BG
                # SalesTouchView uses POS_BG_MAIN.
                tab_frame = ttk.Frame(notebook, padding=0) 
                # Note: notebook tab contents usually have a background. 
                # If active tab is white, content should blend?
                
                notebook.add(tab_frame, text=f"  Caja {i+1}  ")
                sales_view_instance = ViewClass(tab_frame, caja_id=str(i+1))
                sales_view_instance.pack(expand=True, fill="both")
                self.sales_tabs.append(sales_view_instance)
        except Exception as e:
            print(f"Error creating sales tabs: {e}")
            import traceback
            messagebox.showerror("Error Crítico al Abrir Ventas", f"No se pudo inicializar la ventana de ventas.\n\nError: {e}\n\n{traceback.format_exc()}")
            self.destroy()

    def on_tab_change(self, event):
        notebook = event.widget
        selected_tab_index = notebook.index(notebook.select())
        
        if 0 <= selected_tab_index < len(self.sales_tabs):
            current_view = self.sales_tabs[selected_tab_index]
            
            # Check if the view has the refresh method (SalesTouchView)
            if hasattr(current_view, 'refresh_group_order_if_needed'):
                current_view.refresh_group_order_if_needed()