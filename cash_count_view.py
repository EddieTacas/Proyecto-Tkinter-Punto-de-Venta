import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import database
from datetime import datetime
import config_manager
import json
try:
    import win32print
except ImportError:
    win32print = None

class CashCountWindow(ttk.Toplevel):
    def __init__(self, master, caja_id):
        super().__init__(master)
        self.title("Arqueo de Caja")
        self.state('zoomed') # Maximized
        self.caja_id = caja_id
        
        # Center window
        self.place_window_center()
        
        # Determine Start Time and Correlative
        self.last_closure = database.get_last_closure(self.caja_id)
        # last_closure row: id, caja_id, start_time, end_time, user_id, system_cash, counted_cash, difference, correlative
        
        if self.last_closure:
            # Start time is the end time of the last closure
            self.start_time = self.last_closure[3] # end_time
            
            # Parse correlative
            last_corr = self.last_closure[8]
            try:
                prefix, num = last_corr.split('-')
                self.next_correlative = f"Cierre-{int(num) + 1}"
            except:
                self.next_correlative = "Cierre-1"
        else:
            # Default start time: Today 00:00:00
            self.start_time = datetime.now().strftime("%Y-%m-%d 00:00:00")
            self.next_correlative = "Cierre-1"
            
        # Variables
        self.denominations = [
            {"value": 200.00, "type": "bill", "label": "S/ 200.00"},
            {"value": 100.00, "type": "bill", "label": "S/ 100.00"},
            {"value": 50.00, "type": "bill", "label": "S/ 50.00"},
            {"value": 20.00, "type": "bill", "label": "S/ 20.00"},
            {"value": 10.00, "type": "bill", "label": "S/ 10.00"},
            {"value": 5.00, "type": "coin", "label": "S/ 5.00"},
            {"value": 2.00, "type": "coin", "label": "S/ 2.00"},
            {"value": 1.00, "type": "coin", "label": "S/ 1.00"},
            {"value": 0.50, "type": "coin", "label": "S/ 0.50"},
            {"value": 0.20, "type": "coin", "label": "S/ 0.20"},
            {"value": 0.10, "type": "coin", "label": "S/ 10 céntimos"}, # Fixed label from 0.10
        ]
        
        # Grid 1: Dinero en Caja
        self.qty_vars = {}
        self.subtotal_vars = {}
        
        # Grid 2: Cambio Siguiente Día (Might be removed or integrated into Retiro?)
        # User says "Retiro de Efectivo" is an input field.
        # "Dinero Acumulado Actual" is the result.
        # So maybe Grid 2 is no longer needed? Check req text.
        # "Dinero acumulado actual (Resta del dinero fisico - el retiro de efectivo)".
        # So "Retiro" is a manual entry.
        # I will keep grid placeholders just in case they want a grid for the *Retiro* breakdown?
        # But for now, simple vars.
        
        # Variables for New Structure
        self.opening_time_var = tk.StringVar()
        self.closing_time_var = tk.StringVar()
        
        # Ingresos
        self.last_accumulated_var = tk.DoubleVar(value=0.00) # Saldo anterior
        self.sales_cash_var = tk.DoubleVar(value=0.00)
        self.income_additional_var = tk.DoubleVar(value=0.00)
        self.total_income_var = tk.DoubleVar(value=0.00)
        
        # Egresos
        self.purchases_var = tk.DoubleVar(value=0.00)
        self.expenses_var = tk.DoubleVar(value=0.00)
        self.anulados_var = tk.DoubleVar(value=0.00)
        self.returns_var = tk.DoubleVar(value=0.00)
        self.discounts_var = tk.DoubleVar(value=0.00)
        self.total_expenses_var = tk.DoubleVar(value=0.00)
        
        # Resultados
        self.system_balance_var = tk.DoubleVar(value=0.00) # Dinero en Caja (Sistema)
        self.physical_cash_var = tk.DoubleVar(value=0.00)  # Dinero físico en caja (Sum of Denoms)
        self.difference_var = tk.DoubleVar(value=0.00)     # Faltante/Sobrante
        self.withdrawal_var = tk.DoubleVar(value=0.00)     # Retiro de Efectivo (Input)
        self.current_accumulated_var = tk.DoubleVar(value=0.00) # Dinero Acumulado Actual
        
        self.stock_value_var = tk.DoubleVar(value=0.00)    # Valor del Stock
        self.cards_var = tk.DoubleVar(value=0.00)          # Tarjetas (Non-Cash)
        
        # Stock Flow Vars
        self.stock_initial_var = tk.DoubleVar(value=0.00)
        self.ingreso_merc_var = tk.DoubleVar(value=0.00)
        self.salida_merc_var = tk.DoubleVar(value=0.00)
        self.anulado_merc_var = tk.DoubleVar(value=0.00)
        self.total_ventas_merc_var = tk.DoubleVar(value=0.00) # Same as sales_cash_var but labeled explicitly for this flow
        
        self.ui_setup_complete = False
        try:
            self.setup_ui()
        except Exception as e:
            import traceback
            messagebox.showerror("Error UI", f"Error al inicializar interfaz:\n{e}\n{traceback.format_exc()}")
            
        self.load_system_data()
        
        # Bind click outside to close
        # We bind to the master (root) to detect clicks outside THIS window
        # But wait, Toplevel is a separate window. 
        # The user request: "si se da un click fuera de la ventana de 'ARQUEO DE CAJA' quiero que la ventana se cierre"
        # This usually implies a "light dismiss" behavior.
        # We can achieve this by binding <Button-1> to the master and checking coordinates, 
        # OR by grabbing focus and detecting focus loss? Focus loss is tricky.
        # A common way is to bind to the root window.
        
        self.transient(master)
        self.focus_set()
        
        # Bind click outside to close
        # We use a delayed binding to avoid closing immediately if the click that opened it is detected
        self.after(100, self.bind_click_outside)
        
    def bind_click_outside(self):
        self.click_outside_id = self.master.bind("<Button-1>", self.check_click_outside, add="+")
        
    def check_click_outside(self, event):
        try:
            # Get click coordinates relative to screen
            x = event.x_root
            y = event.y_root
            
            # Get window geometry
            wx = self.winfo_rootx()
            wy = self.winfo_rooty()
            ww = self.winfo_width()
            wh = self.winfo_height()
            
            # Check if click is outside
            if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
                self.destroy()
        except Exception:
            pass

    def destroy(self):
        # Unbind event
        if hasattr(self, 'click_outside_id'):
            try:
                self.master.unbind("<Button-1>", self.click_outside_id)
            except:
                pass
        super().destroy()
        
    def place_window_center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def setup_ui(self):
        # Header
        header_frame = ttk.Frame(self, padding=5, bootstyle="primary")
        header_frame.pack(fill="x")
        
        # Top Header Info
        info_frame = ttk.Frame(header_frame, bootstyle="primary")
        info_frame.pack(fill="x", padx=10)
        
        ttk.Label(info_frame, text=f"ARQUEO DE CAJA - {self.next_correlative}", font=("Segoe UI", 16, "bold"), bootstyle="inverse-primary").pack(side="left")
        
        # Right Side Info: Apertura/Cierre
        times_frame = ttk.Frame(info_frame, bootstyle="primary")
        times_frame.pack(side="right")
        
        ttk.Label(times_frame, text="Apertura: ", font=("Segoe UI", 10, "bold"), bootstyle="inverse-primary").pack(side="left")
        ttk.Label(times_frame, textvariable=self.opening_time_var, font=("Segoe UI", 10), bootstyle="inverse-primary").pack(side="left", padx=(0, 15))
        
        # New Cierre Inicial (using self.start_time which comes from last closure)
        # We need a var for it to display cleanly or just strict string
        self.cierre_inicial_str_var = tk.StringVar(value=self.start_time)
        ttk.Label(times_frame, text="Cierre Inicial: ", font=("Segoe UI", 10, "bold"), bootstyle="inverse-primary").pack(side="left")
        ttk.Label(times_frame, textvariable=self.cierre_inicial_str_var, font=("Segoe UI", 10), bootstyle="inverse-primary").pack(side="left", padx=(0, 15))

        ttk.Label(times_frame, text="Cierre Final: ", font=("Segoe UI", 10, "bold"), bootstyle="inverse-primary").pack(side="left")
        ttk.Label(times_frame, textvariable=self.closing_time_var, font=("Segoe UI", 10), bootstyle="inverse-primary").pack(side="left")

        # Scrollable Container
        canvas_container = ttk.Frame(self)
        canvas_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        
        main_container = ttk.Frame(canvas, padding=5)
        
        main_container.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=main_container, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # --- Left Side: History ---
        history_frame = ttk.Labelframe(main_container, text="Historial de Cierres", padding=5)
        history_frame.pack(side="left", fill="y", padx=(0, 5), anchor="n") 
        
        # Treeview
        columns = ("id", "fecha", "usuario", "correlativo")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", bootstyle="info", height=25, displaycolumns=("fecha", "usuario", "correlativo"))
        
        self.history_tree.heading("fecha", text="Fecha")
        self.history_tree.heading("usuario", text="Usuario")
        self.history_tree.heading("correlativo", text="Cierre")
        
        self.history_tree.column("fecha", width=120)
        self.history_tree.column("usuario", width=80)
        self.history_tree.column("correlativo", width=70, anchor="center")
        
        self.history_tree.pack(fill="both", expand=True)

        # Print Button (History)
        ttk.Button(history_frame, text="IMPRIMIR SELECCIONADO", command=self.print_history_selected, bootstyle="info").pack(fill="x", pady=10)

        self.load_history()
        
        # --- Right Side: Dashboard ---
        dashboard_frame = ttk.Frame(main_container)
        dashboard_frame.pack(side="left", fill="both", expand=True)
        
        # Row 1: Ingresos | Egresos
        balance_row = ttk.Frame(dashboard_frame)
        balance_row.pack(fill="x", pady=(0, 10))
        
        # Ingresos Frame
        ing_frame = ttk.Labelframe(balance_row, text="Ingresos en Efectivo", padding=10)
        ing_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self._build_row_label_val(ing_frame, 0, "Efectivo Acumulado Anterior:", self.last_accumulated_var)
        self._build_row_label_val(ing_frame, 1, "Total Ventas:", self.sales_cash_var)
        ttk.Separator(ing_frame, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        self._build_row_label_val(ing_frame, 4, "Total de Ingresos:", self.total_income_var, bold=True)
        
        # Egresos Frame
        egr_frame = ttk.Labelframe(balance_row, text="Egresos en Efectivo", padding=10)
        egr_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        # self._build_row_label_val(egr_frame, 0, "Compras:", self.purchases_var) # Removed per user request
        
        # Custom Gastos Row with Button
        font = ("Segoe UI", 10)
        ttk.Label(egr_frame, text="Gastos:", font=font).grid(row=1, column=0, sticky="w", pady=2)
        
        g_frame = ttk.Frame(egr_frame)
        g_frame.grid(row=1, column=1, sticky="e", pady=2, padx=5)
        
        ttk.Button(g_frame, text="+", command=self.open_expenses_window, bootstyle="success-outline", width=4).pack(side="left", padx=(0, 5))
        ttk.Label(g_frame, textvariable=self.expenses_var, font=("Segoe UI", 10)).pack(side="left")
        
        self._build_row_label_val(egr_frame, 2, "Tarjetas:", self.cards_var)
        self._build_row_label_val(egr_frame, 3, "Anulados:", self.anulados_var)
        self._build_row_label_val(egr_frame, 4, "Devoluciones:", self.returns_var)
        self._build_row_label_val(egr_frame, 5, "Descuentos:", self.discounts_var)
        ttk.Separator(egr_frame, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
        self._build_row_label_val(egr_frame, 7, "Total Egresos:", self.total_expenses_var, bold=True)
        
        # Row 2: Conteo | Resultados
        mid_row = ttk.Frame(dashboard_frame)
        mid_row.pack(fill="x", pady=10)
        
        # Conteo Grid REMOVED per user request
        # count_frame = ttk.Labelframe(mid_row, text="Dinero Físico en Caja", padding=10)
        # count_frame.pack(side="left", fill="y", padx=(0, 5))

        # Resultados Frame
        res_frame = ttk.Labelframe(mid_row, text="Resultados", padding=10)
        res_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        self._build_row_label_val(res_frame, 0, "Dinero Acumulado Actual:", self.system_balance_var, bold=True, color="success")
        
        # Removed Physical, Difference, and Duplicate Accumulated per request
        # self._build_row_label_val(res_frame, 1, "Dinero físico en caja:", self.physical_cash_var, bold=True)
        # self.difference_lbl = self._build_row_label_val(res_frame, 2, "Faltante/Sobrante:", self.difference_var, bold=True, color="danger")
        
        ttk.Separator(res_frame, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Stock Flow
        # Order from bottom up as requested:
        # Stock Final (was Valor del Stock)
        # Ingreso de Mercadería (above Stock Initial... wait user said:)
        # "arriba de Ingreso: Stock Inicial"
        # "arriba de salida: Ingreso"
        # "arriba de anulado: Salida"
        # "arriba de Total Venta: Anulado"
        # "arriba de Valor Stock: Total Venta"
        
        # Re-reading order to get row indices right (Top to Bottom):
        # 1. Stock Inicial
        # 2. Ingreso de Mercadería
        # 3. Salida de Mercadería
        # 4. Anulado
        # 5. Total Venta
        # 6. Stock Final (Renamed from Valor del Stock)

        self._build_row_label_val(res_frame, 5, "Stock Inicial:", self.stock_initial_var)
        self._build_row_label_val(res_frame, 6, "Ingreso de Mercadería:", self.ingreso_merc_var)
        self._build_row_label_val(res_frame, 7, "Salida de Mercadería:", self.salida_merc_var)
        self._build_row_label_val(res_frame, 8, "Anulado:", self.anulado_merc_var)
        self._build_row_label_val(res_frame, 9, "Total Venta:", self.total_ventas_merc_var)
        
        self._build_row_label_val(res_frame, 10, "Stock Final:", self.stock_value_var, bold=True, color="info")

        # Buttons
        btn_frame = ttk.Frame(dashboard_frame)
        btn_frame.pack(fill="x", pady=20)
        
        ttk.Button(btn_frame, text="IMPRIMIR REPORTE", command=self.save_and_close, bootstyle="info-outline", width=25).pack(side="right", padx=5)
        
    def _build_row_label_val(self, parent, row, label, var, bold=False, color=None):
        font = ("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10)
        style = f"{color}" if color else None # Not exact mapping but close
        
        lbl = ttk.Label(parent, text=label, font=font)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        
        val_lbl = ttk.Label(parent, textvariable=var, font=font, bootstyle=style if style else "default")
        val_lbl.grid(row=row, column=1, sticky="e", pady=2, padx=5)
        return val_lbl
        # Close Buttons Frame from setup_ui
        
    def load_system_data(self):
        # 1. Opening/Closing Time
        opening = config_manager.load_setting("daily_opening_time", "No Registrado")
        self.opening_time_var.set(opening)
        
        closing = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.closing_time_var.set(closing)
        
        # 2. Last Accumulated (Efectivo Acumulado Anterior)
        conn = database.create_connection()
        cur = conn.cursor()
        try:
             # Check if column exists first as fail-safe or rely on try-except
             cur.execute("SELECT accumulated_cash FROM cash_counts WHERE caja_id = ? ORDER BY id DESC LIMIT 1", (self.caja_id,))
             row = cur.fetchone()
             last_acc = row[0] if row else 0.0
             self.last_accumulated_var.set(last_acc)
        except:
             self.last_accumulated_var.set(0.0)
        
        # 3. Stock Value
        try:
             cur.execute("SELECT SUM(price * stock) FROM products")
             s_val = cur.fetchone()[0] or 0.0
             self.stock_value_var.set(s_val)
        except:
             self.stock_value_var.set(0.0)
        conn.close()
        
        # 4. Analytics
        stats = self._get_period_analytics(self.start_time, closing)
        
        # Add Temp Expenses
        temp_exps = database.get_temp_expenses(self.caja_id)
        temp_total = sum(e[3] for e in temp_exps)

        self.sales_cash_var.set(stats['total_gross_sales']) # Total Sales (Gross)
        self.income_additional_var.set(stats['income_additional'])
        self.purchases_var.set(stats['purchases'])
        self.expenses_var.set(stats['expenses'] + temp_total)
        self.anulados_var.set(stats['anulados'])
        self.returns_var.set(stats['returns'])
        self.discounts_var.set(stats['discounts'])
        self.cards_var.set(stats['non_cash_sales']) # Tarjetas deduction
        
        # Stock Flow Data
        # 1. Stock Inicial (From Last Closure "Stock Final")
        # last_closure is loaded in __init__: self.last_closure
        # Row index 17 should be stock_value if schema matches, but safer to use fetch
        # In setup_database: _add_column_if_not_exists(conn, "cash_counts", "stock_value", "REAL DEFAULT 0.0")
        # Ideally we fetch it from self.last_closure if index covers it.
        # But get_last_closure performs "SELECT *".
        # Let's assume self.last_closure is valid.
        stock_init = 0.0
        if self.last_closure and len(self.last_closure) > 17:
             # Just guessing index or fetch explicitly
             # To be safe, let's fetch 'stock_value' of last closure specifically
             pass
        
        # Fetch explicit check for last stock value
        try:
             conn = database.create_connection()
             cur = conn.cursor()
             # Get last stock_value from last closure of THIS caja
             cur.execute("SELECT stock_value FROM cash_counts WHERE caja_id = ? ORDER BY id DESC LIMIT 1", (self.caja_id,))
             row = cur.fetchone()
             if row: stock_init = row[0]
             conn.close()
        except: pass
        self.stock_initial_var.set(stock_init)
        
        # 2. Movement Totals (Ingreso, Salida, Anulado)
        # Using new DB function
        try:
             mov_totals = database.get_movement_totals_by_type_in_range(self.start_time, closing)
             self.ingreso_merc_var.set(mov_totals.get('INGRESO', 0.0))
             self.salida_merc_var.set(mov_totals.get('SALIDA', 0.0))
             # "Anulado" from movements (if exists as type)
             self.anulado_merc_var.set(mov_totals.get('ANULADO', 0.0))
        except Exception as e:
             print(f"Error fetching mov totals: {e}")
             
        # 3. Info consistency
        self.total_ventas_merc_var.set(self.sales_cash_var.get()) # Total Venta (Gross)
        
        self.calculate_total()
        
    def _get_period_analytics(self, start, end):
        # Fetch Sales and Movements
        conn = database.create_connection()
        cur = conn.cursor()
        
        # 1. SALES
        # Fetch ID, payment methods, amounts, date
        query_sales = """
            SELECT id, payment_method, amount_paid, payment_method2, amount_paid2, sale_date
            FROM sales 
        """
        cur.execute(query_sales)
        sales_rows = cur.fetchall()
        
        total_gross_sales = 0.0
        total_discounts = 0.0
        total_non_cash = 0.0
        
        # Helper to parse multiple date formats
        def parse_date(date_str):
            if not date_str: return None
            formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"]
            for fmt in formats:
                try: return datetime.strptime(str(date_str), fmt)
                except ValueError: continue
            return None

        start_dt = parse_date(start)
        end_dt = parse_date(end)
        
        if start_dt and end_dt:
             for r in sales_rows:
                 # r: id, pm1, amt1, pm2, amt2, date
                 s_dt = parse_date(r[5])
                 if s_dt and start_dt <= s_dt <= end_dt:
                     sale_id = r[0]
                     pm1 = r[1]
                     amt1 = r[2] or 0.0
                     pm2 = r[3]
                     amt2 = r[4] or 0.0
                     
                     # 1. Non-Cash Calculation
                     non_cash = 0.0
                     if pm1 != 'EFECTIVO': non_cash += amt1
                     if pm2 != 'EFECTIVO': non_cash += amt2
                     total_non_cash += non_cash
                     
                     # 2. Gross and Discount Calculation (All Sales)
                     cur.execute("SELECT quantity_sold, price_per_unit, original_price FROM sale_details WHERE sale_id=?", (sale_id,))
                     details = cur.fetchall()
                     
                     sale_gross = 0.0
                     sale_discount = 0.0
                     
                     for d in details:
                         qty = d[0] or 0
                         price = d[1] or 0.0
                         orig = d[2] or price # default to price if None
                         if orig < price: orig = price # sanity check
                         
                         line_gross = qty * orig
                         line_price = qty * price
                         line_disc = line_gross - line_price
                         
                         sale_gross += line_gross
                         sale_discount += line_disc
                         
                     total_gross_sales += sale_gross
                     total_discounts += sale_discount


        # 2. MOVEMENTS
        query_movs = "SELECT movement_type, total_amount, date_time FROM inventory_movements"
        cur.execute(query_movs)
        mov_rows = cur.fetchall()
        
        income_add = 0.0
        purchases = 0.0
        expenses = 0.0
        anulados = 0.0
        returns = 0.0
        
        if start_dt and end_dt:
            for type_, total, m_date_str in mov_rows:
                m_dt = parse_date(m_date_str)
                if m_dt and start_dt <= m_dt <= end_dt:
                    type_upper = type_.upper()
                    if type_upper == 'INGRESO':
                        income_add += total
                    elif type_upper == 'COMPRA':
                        purchases += total
                    elif type_upper in ['GASTO', 'SALIDA']:
                        expenses += total
                    elif type_upper == 'ANULADO':
                        anulados += total
                    elif type_upper in ['DEVOLUCION', 'DEVOLUCIÓN']:
                        returns += total

        conn.close()
        
        return {
            'total_gross_sales': total_gross_sales,
            'non_cash_sales': total_non_cash,
            'discounts': total_discounts,
            'income_additional': income_add,
            'purchases': purchases,
            'expenses': expenses,
            'anulados': anulados,
            'returns': returns
        }



    def calculate_total(self, *args):
        try:
            # 1. Physical Cash
            total_physical = 0.0
            for val, var in self.qty_vars.items():
                try:
                    qty = int(var.get() or 0)
                    total_physical += qty * float(val)
                except: pass
            self.physical_cash_var.set(total_physical)
            
            # 2. System Cash
            ingresos = self.last_accumulated_var.get() + self.sales_cash_var.get()
            self.total_income_var.set(ingresos)
            
            egresos = self.purchases_var.get() + self.expenses_var.get() + self.anulados_var.get() + self.returns_var.get() + self.discounts_var.get() + self.cards_var.get()
            self.total_expenses_var.set(egresos)
            
            # System Balance = Ingresos - Egresos
            system_cash = ingresos - egresos
            self.system_balance_var.set(system_cash)
            
            # 3. Difference
            diff = total_physical - system_cash
            self.difference_var.set(diff)
            
            # Style update based on difference
            if hasattr(self, 'difference_lbl'):
                if diff > 0:
                    self.difference_lbl.configure(bootstyle="success")
                else:
                    self.difference_lbl.configure(bootstyle="danger")
            
        # 4. Current Accumulated (Equals Physical Cash since Withdrawal is removed)
            accumulated = total_physical
            self.current_accumulated_var.set(accumulated)
            
            # 5. Stock Final Calculation
            # Stock Final = Stock Init + Ingreso - Salida + Anulado - Total Ventas
            s_init = self.stock_initial_var.get()
            s_in = self.ingreso_merc_var.get()
            s_out = self.salida_merc_var.get()
            s_anulado = self.anulado_merc_var.get()
            s_sales = self.total_ventas_merc_var.get()
            
            stock_final = s_init + s_in - s_out + s_anulado - s_sales
            self.stock_value_var.set(stock_final)
            
        except Exception as e:
            print(f"Error in calculate_total: {e}")

    print_history_selected = lambda self: self.print_cash_count(history_mode=True)





    def load_history(self):
        try:
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
                
            rows = database.get_cash_counts_history(self.caja_id)
            for row in rows:
                # row: id, end_time, user_id, correlative, difference
                # Remove difference (last element)
                self.history_tree.insert("", "end", values=row[:-1])
        except Exception as e:
            print(f"Error loading history: {e}")


    def _generate_whatsapp_text(self, data):
        """Generates the text for WhatsApp/Email with specific alignment."""
        context = data
        details_raw = context.get('details_json', '{}')
        if isinstance(details_raw, str):
            import json
            try:
                details = json.loads(details_raw)
            except:
                details = {}
        else:
            details = details_raw or {}
        
        # Formatting Helpers
        def fmt(val):
            val = float(val or 0)
            return "{:,.2f}".format(val)
            
        def align_line(label, value, is_money=True, label_width=29, val_width=13):
            # Label width adjusted to force alignment
            # Amount width 13 approx 'S/ 00,000.00'
            label_part = f"{label:<{label_width}}"
            if is_money:
                val_part = f"S/ {fmt(value):>{val_width}}"
                return f"{label_part} : {val_part}\n"
            else:
                val_part = f"{str(value):>{val_width+3}}" # +3 to cover 'S/ ' space roughly
                return f"{label_part} : {val_part}\n"
                
        def sep():
            return "-" * 57 + "\n"

        # Data Extraction
        # Access self vars safely for Stock Flow (Current Session)
        st_init = self.stock_initial_var.get()
        st_in = self.ingreso_merc_var.get()
        st_out = self.salida_merc_var.get()
        st_anul = self.anulado_merc_var.get()
        st_sales = self.total_ventas_merc_var.get()
        st_final = self.stock_value_var.get()
        
        sales_cash = context.get('sales_cash', 0.0)
        
        # Discounts
        discounts_data = details.get('discounts_details', [])
        total_desc = sum([float(d[1] or 0) * float(d[2] or 0) for d in discounts_data]) if discounts_data else 0.0
        
        # Expenses
        expenses_list = details.get('expenses_list', [])
        total_expenses = sum([float(x['amount']) for x in expenses_list]) if expenses_list else 0.0
        
        # Money Calculation
        # prev_cash: Should be 'initial_balance' (Saldo Anterior) NOT 'income_additional'
        prev_cash = float(context.get('initial_balance', 0) or 0) 
        
        # current_cash: Should be 'accumulated_cash' (System Balance) NOT calculated manually here
        # to ensure it matches the screen/database exactly.
        current_cash = float(context.get('accumulated_cash', 0) or 0)
        
        # Cards & Anulados for Notification
        cards_val = float(context.get('cards_deduction', 0) or 0)
        anulado_val = float(context.get('anulados', 0) or 0)
        
        # Total Balance Calculation (Matches Ticket Logic)
        # Ticket: calc_total = total_venta - total_desc - tarjetas - anulado
        total_balance = float(sales_cash) - total_desc - cards_val - anulado_val
        
        # Dates
        start_t = context.get('start_time', 'N/A')
        end_t = context.get('end_time', 'N/A')
        
        # --- BUILD TEXT ---
        txt = ""
        # Header
        txt += f"*{data.get('commercial_name', 'EMPRESA')}*\n"
        txt += f"_{data.get('issuer_address', '')}_\n"
        txt += f"*CIERRE DE CAJA - Arqueo*\n"
        txt += sep()
        
        txt += align_line("🔢 Nro Cierre", data.get('correlative', 'Sin Codigo'), is_money=False)
        txt += align_line("📅 Apertura", start_t, is_money=False)
        txt += align_line("📅 Cierre Inicial", start_t, is_money=False) 
        txt += align_line("📅 Cierre Final", end_t, is_money=False)
        txt += align_line("👤 Usuario", data.get('user_name', 'Admin'), is_money=False)
        txt += sep()
        
        # Balance Money
        # Balance Money
        txt += f"*BALANCE DE CAJA*\n"
        txt += align_line("Total Venta", sales_cash)
        txt += align_line("Descuentos", total_desc)
        txt += align_line("Tarjetas", cards_val)
        txt += align_line("Anulado", anulado_val)
        # Total logic: 
        # For notification, total_balance was sales_cash. 
        # If we list deductions, 'Total' usually serves as Net.
        # But 'Dinero Acumulado Actual' (current_cash) handles the math: prev + sale - exp.
        # Does current_cash account for cards/anulados?
        # prev_cash + total_balance (sales) - total_expenses.
        # If sales includes cards, cash is less.
        # But current_cash is usually "Effective Cash". So it should subtract cards?
        # Code above: current_cash = prev_cash + total_balance - total_expenses
        # If total_balance is gross sales, we might need to adjust.
        # But for now I'm just changing the DISPLAY layout.
        txt += f"*{align_line('Total', total_balance).strip()}*\n"
        txt += sep()
        
        txt += align_line("Efectivo Acumulado Anterior", prev_cash)
        txt += sep()
        
        # Expenses
        txt += f"*DESGLOSE DE GASTOS*\n"
        if expenses_list:
             for ex in expenses_list:
                 d1 = ex.get('detail', '')
                 d2 = ex.get('detail_2', '')
                 full_desc = f"{d1} {d2}".strip()
                 txt += f"{full_desc} : S/ {fmt(ex['amount'])}\n"
        else:
             txt += "(Sin gastos registrados)\n"
        
        txt += f"*{align_line('Total Gastos', total_expenses).strip()}*\n"
        txt += sep()
        
        txt += f"*{align_line('Dinero Acumulado Actual', current_cash).strip()}*\n"
        txt += sep()
        
        # Stock
        txt += f"*STOCK DE PRODUCTOS*\n"
        # txt += sep() # Removed separator per request
        # txt += f"*BALANCE DE CAJA*\n" # Removed redundant header
        txt += align_line("STOCK INICIAL", st_init)
        txt += align_line("Ingreso mercadería", st_in)
        txt += align_line("Salida mercadería", st_out)
        txt += align_line("Anulado", st_anul)
        txt += align_line("Total Venta", st_sales)
        txt += align_line("STOCK FINAL", st_final)
        txt += sep()
        
        # Ranking
        txt += f"*RANKING DE PRODUCTOS*\n"
        ranking = details.get('ranking', [])
        if ranking:
             for i, r in enumerate(ranking, 1):
                 txt += f"{i}. {r[0]} (Cant: {int(r[1])})\n"
        else:
             txt += "(Sin ventas registradas)\n"
        txt += sep()
        
        # Discounts Detail
        txt += f"*DESGLOSE DE DESCUENTOS*\n"
        txt += "DESC. | CANT. | UNIT. | SUBT.\n"
        if discounts_data:
             for d in discounts_data:
                 u_desc = float(d[1] or 0)
                 qty = float(d[2] or 0)
                 u_price = float(d[3] or 0)
                 subt = float(d[4] or 0)
                 txt += f"{d[0]}\n"
                 # Custom simpler alignment for table row
                 txt += f" {fmt(u_desc)} | {int(qty)} | {fmt(u_price)} | {fmt(subt)}\n"
             txt += align_line("Total", total_desc)
        else:
             txt += "(No hubieron descuentos)\n"
             txt += align_line("Total", 0.00)
        txt += sep()
        
        # Documents
        txt += f"*DOCUMENTOS EMITIDOS*\n"
        docs = details.get('docs_summary', [])
        total_docs_sum = 0.0
        if docs:
             for doc in docs:
                 dtype = doc[0] or "Venta"
                 dcount = int(doc[1] or 0)
                 dsum = float(doc[2] or 0)
                 total_docs_sum += dsum
                 # align_line-ish
                 lbl = f"{dtype}"
                 val_str = f"{dcount} (S/ {fmt(dsum)})"
                 txt += f"{lbl:<19} : {val_str:>20}\n"
        else:
             txt += "(Sin documentos)\n"
        
        txt += f"*{align_line('Total', total_docs_sum).strip()}*\n"
        
        return txt

    def _send_whatsapp_notification(self, data):
        try:
            import database
            import whatsapp_manager
            
            if not whatsapp_manager.baileys_manager.is_running():
                print("WhatsApp service not running.")
                return

            # 1. Get Issuer Config
            issuers = database.get_all_issuers()
            if not issuers: return
            issuer = issuers[0]
            
            # Fetch receivers
            conn = database.create_connection()
            cur = conn.cursor()
            cur.execute("SELECT whatsapp_receivers, name, commercial_name, address FROM issuers WHERE id = ?", (issuer[0],))
            res = cur.fetchone()
            conn.close()
            
            if not res or not res[0]: return
            
            receivers_str = res[0]
            receivers_list = []
            for r in receivers_str.split(","):
                clean_r = r.strip()
                if clean_r.lower().startswith("id:"):
                    clean_r = clean_r[3:].strip()
                elif clean_r.lower().startswith("id"):
                    clean_r = clean_r[2:].strip()
                    
                if clean_r:
                    receivers_list.append(clean_r)
            
            if not receivers_list: return
            
            # 2. Inject Branding
            data['commercial_name'] = res[2] or res[1] or "EMPRESA"
            data['issuer_address'] = res[3] or ""
            
            # 3. Generate Text
            msg_text = self._generate_whatsapp_text(data)
            
            # 4. Send WhatsApp
            for number in receivers_list:
                try:
                    print(f"Sending WA to {number}")
                    whatsapp_manager.baileys_manager.send_message(number, msg_text)
                except Exception as e:
                    print(f"Error sending WA to {number}: {e}")
                   
            # 5. Send Email if configured
            try:
                import gmail_manager
                # Re-open Conn for email config
                conn_email = database.create_connection()
                cur_email = conn_email.cursor()
                cur_email.execute("SELECT gmail_sender, gmail_receivers, gmail_password FROM issuers WHERE id = ?", (issuer[0],))
                res_email = cur_email.fetchone()
                conn_email.close()
                
                if res_email:
                    g_sender = res_email[0]
                    g_receivers_str = res_email[1]
                    g_password = res_email[2]
                    
                    if g_sender and g_password and g_receivers_str:
                        g_receivers = [r.strip() for r in g_receivers_str.split(",") if r.strip()]
                        if g_receivers:
                             # Formato: ***(nombre comercial)*** (fecha de cierre) Cierre
                             c_date = data.get('end_time', 'NOW').split()[0]
                             c_name = data.get('commercial_name', 'EMPRESA')
                             subject = f"***{c_name}*** ({c_date}) Cierre"
                             
                             gmail_manager.send_email(g_sender, g_password, g_receivers, subject, msg_text)
            except Exception as e:
                print(f"Error triggering email: {e}")
                
        except Exception as e:
            print(f"Error in notification system: {e}")
    def print_cash_count(self, history_mode=False):
        data_to_print = {}
        
        # 1. Get Branding
        issuers = database.get_all_issuers()
        issuer = issuers[0] if issuers else None
        
        branding = {
            'commercial_name': issuer[4] if issuer and len(issuer)>4 else "EMPRESA",
            'issuer_address': issuer[3] if issuer and len(issuer)>3 else "",
        }
        
        if history_mode:
            selected = self.history_tree.selection()
            if not selected: 
                import custom_messagebox as messagebox
                messagebox.showwarning("Selección", "Seleccione un cierre.")
                return
            
            vals = self.history_tree.item(selected, 'values')
            cid = vals[0]
            row = database.get_cash_count_by_id(cid) # Returns dict-like Row
            if not row: return
            
            data_to_print = dict(row)
            data_to_print['user_name'] = row['user_id']
            data_to_print['closure_id'] = row['correlative']
            
        else:
             # Current Mode
             import json
             now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             
             # Fetch extra data for ticket
             tmps = database.get_temp_expenses(self.caja_id)
             expenses_list = [{'date':x[1], 'detail':x[2], 'amount':x[3], 'detail_2': (x[4] if len(x)>4 else "")} for x in tmps]
             
             discounts = database.get_discount_details_in_range(self.start_time, now_str)
             docs = database.get_documents_summary_in_range(self.start_time, now_str)
             
             data_to_print = {
                 'caja_id': self.caja_id,
                 'start_time': self.start_time,
                 'end_time': now_str,
                 'user_id': "Admin",
                 'user_name': "Admin",
                 
                 'system_cash': self.system_balance_var.get(), 
                 'counted_cash': self.physical_cash_var.get(),
                 'difference': self.difference_var.get(),
                 'correlative': self.next_correlative,
                 'closure_id': self.next_correlative,
                 
                 'opening_time': self.opening_time_var.get(),
                  'opening_time': self.opening_time_var.get(),
                  'accumulated_cash': self.system_balance_var.get(), # Synced with System Balance
                 
                 # Stock & Flows
                 'stock_value': self.stock_value_var.get(), # Stock Final
                 'sales_cash': self.sales_cash_var.get(),
                 'income_additional': self.income_additional_var.get(),
                 'purchases': self.purchases_var.get(),
                 'anulados': self.anulados_var.get(),
                 'returns': self.returns_var.get(),
                 'withdrawal': self.withdrawal_var.get(),
                 
                 'initial_balance': self.last_accumulated_var.get(),
                 'expenses': self.expenses_var.get(),
                 'cards_deduction': self.cards_var.get(),
                 'collected_total': self.total_income_var.get(),
                 
                 # Specific Stock Vars for Ticket
                 'stock_initial': self.stock_initial_var.get(),
                 'ingreso_merc': self.ingreso_merc_var.get(),
                 'salida_merc': self.salida_merc_var.get(),
                 'anulado_merc': self.anulado_merc_var.get(),
                 'total_ventas_merc': self.total_ventas_merc_var.get(), # Same as sales_cash usually
                 
                 'details_json': json.dumps({
                     'grid_denominations': {k: v.get() for k,v in self.qty_vars.items()},
                     'expenses_list': expenses_list,
                     'discounts_list': discounts,
                     'documents_list': docs
                 })
             }

        data_to_print.update(branding)
        
        # Print
        printer = config_manager.load_setting('default_printer')
        if printer:
             try:
                 raw = self._generate_cash_count_ticket(data_to_print)
                 import win32print
                 hPrinter = win32print.OpenPrinter(printer)
                 try:
                     hJob = win32print.StartDocPrinter(hPrinter, 1, ("Arqueo", None, "RAW"))
                     try:
                         win32print.StartPagePrinter(hPrinter)
                         win32print.WritePrinter(hPrinter, raw)
                         win32print.EndPagePrinter(hPrinter)
                     finally:
                         win32print.EndDocPrinter(hPrinter)
                 finally:
                     win32print.ClosePrinter(hPrinter)
             except Exception as e:
                 import custom_messagebox as messagebox
                 messagebox.showerror("Error", f"Error de impresión: {e}")
        else:
             import custom_messagebox as messagebox
             messagebox.showwarning("Impresora", "No hay impresora configurada.")

    def _generate_cash_count_ticket(self, context):
        ESC = b'\x1b'; GS = b'\x1d'
        BOLD_ON = ESC + b'E\x01'; BOLD_OFF = ESC + b'E\x00'
        ALIGN_CENTER = ESC + b'a\x01'; ALIGN_LEFT = ESC + b'a\x00'
        CUT = GS + b'V\x41\x00'
        
        def text(s): return s.encode('latin-1', 'replace')
        def fmt(v): return f"{float(v or 0.0):,.2f}"
        
        # Helper for right-aligned value rows (Label .... Value)
        def row(k, v, prefix="S/ "): 
             s_v = fmt(v)
             total_len = len(k) + len(prefix) + len(s_v)
             sp_len = 42 - total_len - 1
             if sp_len < 1: sp_len = 1
             return k + (" " * sp_len) + prefix + s_v + "\n"

        # Helper for 3 column row (Label ... Col2 ... Col3)
        def row3(c1, c2, c3, w1=20, w2=8, w3=12):
            # C1 aligns Left, C2 Center, C3 Right
            s1 = str(c1)[:w1].ljust(w1)
            s2 = str(c2)[:w2].center(w2)
            s3 = str(c3)[:w3].rjust(w3)
            return s1 + s2 + s3 + "\n"

        buf = bytearray()
        buf.extend(ESC + b'@') # Reset
        buf.extend(ALIGN_CENTER)
        buf.extend(BOLD_ON)
        buf.extend(text(context.get('commercial_name', 'EMPRESA') + "\n"))
        buf.extend(BOLD_OFF)
        buf.extend(text(context.get('issuer_address', '') + "\n"))
        buf.extend(BOLD_ON + text("CIERRE DE CAJA - Arqueo\n") + BOLD_OFF)
        buf.extend(text("-" * 42 + "\n"))
        
        buf.extend(ALIGN_LEFT)
        buf.extend(text(f"Nro Cierre : {context.get('correlative', context.get('closure_id', 'N/A'))}\n"))
        
        # CIERRE INICIAL (Start Time)
        start_ts = context.get('start_time', '')
        # Format if possible
        try:
             s_ts = datetime.strptime(str(start_ts), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
        except: s_ts = str(start_ts)
        buf.extend(text(f"APERTURA      : {s_ts}\n"))
        buf.extend(text(f"CIERRE INICIAL: {s_ts}\n"))
        
        # CIERRE FINAL (Current/End Time) used to be Fecha
        end_ts = context.get('end_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        try:
             e_ts = datetime.strptime(str(end_ts), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
        except: e_ts = str(end_ts)
        buf.extend(text(f"Cierre Final  : {e_ts}\n"))
        
        buf.extend(text(f"Usuario       : {context.get('user_id', 'Admin')}\n"))
        buf.extend(text("-" * 42 + "\n"))
        
        # BALANCE DE CAJA
        # APERTURA, TOTAL VENTA, DESCUENTOS, TARJETAS, ANULADO, TOTAL
        # *Dinero Acumulado Actual
        
        buf.extend(ALIGN_CENTER + BOLD_ON + text("BALANCE DE CAJA\n") + BOLD_OFF + ALIGN_LEFT)
        
        # 1. Total Venta (Was 2.)
        total_venta = float(context.get('sales_cash', 0) or 0) # Assuming this is the main sales figure
        buf.extend(text(row("Total Venta", total_venta)))
        
        # 3. Descuentos (Need calculate)
        # We need to sum discounts from details or get from context if available
        # logic from below (lines 1202) - let's reuse or recalc
        # context['details_json'] usually has 'discounts_list'
        total_desc = 0.0
        try:
            d_list = details.get('discounts_list', [])
            for d in d_list:
                # name, unit_desc, qty, price, subtotal
                u_d = float(d[1] or 0)
                qty = float(d[2] or 0)
                total_desc += (u_d * qty)
        except: pass
        buf.extend(text(row("Descuentos:", total_desc)))
        
        # 4. Tarjetas
        tarjetas = float(context.get('cards_deduction', 0) or 0)
        buf.extend(text(row("Tarjetas:", tarjetas)))
        
        # 5. Anulado
        anulado = float(context.get('anulados', 0) or 0)
        buf.extend(text(row("Anulado:", anulado)))
        
        # 6. TOTAL (Calculated Balance)
        # "Total" usually means the cash balance or the net sales?
        # Given "Dinero Acumulado Actual" is separate, maybe Total = Venta Neta?
        # Let's assume User wants the arithmetic result of above lines:
        # Apertura + Venta - Descuentos - Tarjetas - Anulado? 
        # Wait, usually Sales includes or excludes discounts/anualdos depending on logic.
        # Assuming Sales is Gross.
        # Let's trust 'accumulated_cash' (system_balance) as the true calculated balance?
        # Or calculate explicitly?
        # User said: "BALANCE DE CAJA... TOTAL... *Dinero Acumulado Actual"
        # "Dinero Acumulado Actual" might be the System Balance.
        # "TOTAL" might be the sum of the list?
        
        # Let's use logic:
        # Balance = Apertura + Ventas - Gastos - Tarjetas...
        # But Gastos is not listed in this specific section request?
        # Wait, usually Balance = Apertura + Incomes - Outcomes.
        
        # Let's calculate 'Total' as the sum of flows listed:
        # Apertura (REMOVED FROM HERE) + Venta - Descuentos - Tarjetas - Anulados
        # Note: If Apertura is removed from visual list, should it be removed from TOTAL?
        # A "Balance de Caja" usually implies closing balance match.
        # If we remove Apertura, the "Total" is just NET MOVEMENT.
        # User asked for "EFECTIVO ACUMULADO ANTERIOR" below total.
        # This implies:
        # Balance del Periodo (Ventas - Descuentos...) -> TOTAL
        # + Efectivo Anterior
        # = Dinero Actual?
        
        # Let's assume TOTAL here means "TOTAL MOVIMIENTOS DEL TURNO".
        # So exclude apertura from calc_total.
        apertura = float(context.get('initial_balance', 0) or 0)
        calc_total = total_venta - total_desc - tarjetas - anulado
        buf.extend(text(row("Total", calc_total)))
        
        buf.extend(text("-" * 42 + "\n"))
        
        # EFECTIVO ACUMULADO ANTERIOR (Moved here)
        buf.extend(text(row("EFECTIVO ACUMULADO ANTERIOR", apertura)))
        buf.extend(text("-" * 42 + "\n"))
        
        # *Dinero Acumulado Actual
        acc_cash = float(context.get('accumulated_cash', 0) or 0)
        buf.extend(text(row("*Dinero Acumulado Actual", acc_cash)))
        buf.extend(text("-" * 42 + "\n"))

        # Parse Details
        import json
        details_raw = context.get('details_json', '{}')
        details = json.loads(details_raw) if isinstance(details_raw, str) else (details_raw or {})
        
        # 1. DESGLOSE DE GASTOS
        expenses = details.get('expenses_list', [])
        if expenses:
            buf.extend(ALIGN_CENTER + BOLD_ON + text("DESGLOSE DE GASTOS\n") + BOLD_OFF + ALIGN_LEFT)
            total_exp = 0.0
            for exp in expenses:
                # Detail 1 + Detail 2
                d1 = exp.get('detail', '')
                d2 = exp.get('detail_2', '')
                amt = float(exp.get('amount', 0.0))
                total_exp += amt
                
                full_desc = f"{d1} {d2}".strip()
                # If desc is too long, wrap or truncate?
                # Using standard row format
                buf.extend(text(row(full_desc[:30], amt)))
            
            buf.extend(ALIGN_CENTER + text(f"Total Gastos: S/ {fmt(total_exp)}\n") + ALIGN_LEFT)
            buf.extend(text("-" * 42 + "\n"))
            
        # 2. Dinero Acumulado Actual (MOVED UP)
        # Removing redundancy if user only wants it in Balance section.
        # But keeping it if it provides context or separator.
        # User list: "BALANCE DE CAJA, ..., *Dinero Acumulado Actual"
        # Since I added it above, I will comment this out or remove to avoid duplication.
        # buf.extend(text(row("Dinero Acumulado Actual", acc_cash)))
        # buf.extend(text("-" * 42 + "\n"))
        
        # 3. STOCK DE PRODUCTOS
        buf.extend(ALIGN_CENTER + BOLD_ON + text("STOCK DE PRODUCTOS\n") + BOLD_OFF + ALIGN_LEFT)
        
        # Parse Dates for concat
        start_t = context.get('start_time', '')
        end_t = context.get('end_time', '')
        # Defend against None
        if not start_t: start_t = datetime.now().strftime("%Y-%m-%d")
        if not end_t: end_t = datetime.now().strftime("%Y-%m-%d")
        
        try:
            d_start = datetime.strptime(str(start_t).split()[0], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: d_start = ""
        
        try:
             d_end = datetime.strptime(str(end_t).split()[0], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: d_end = ""
        
        s_init = float(context.get('stock_initial', 0) or 0)
        s_in = float(context.get('ingreso_merc', 0) or 0)
        s_out = float(context.get('salida_merc', 0) or 0)
        s_anulado = float(context.get('anulado_merc', 0) or 0)
        s_sales = float(context.get('total_ventas_merc', 0) or 0)
        s_final = float(context.get('stock_value', 0) or 0) # Stock Final
        
        buf.extend(text(row(f"Stock Inicial {d_start}", s_init)))
        buf.extend(text(row("Ingreso de Mercaderia", s_in)))
        buf.extend(text(row("Salida de Mercaderia", s_out)))
        buf.extend(text(row("Anulado", s_anulado)))
        buf.extend(text(row("Total de Venta", s_sales)))
        buf.extend(text(row(f"Stock final {d_end}", s_final)))
        buf.extend(text("-" * 42 + "\n"))
        
        # 4. DESGLOSE DE DESCUENTOS
        discounts = details.get('discounts_list', [])
        if discounts:
            buf.extend(ALIGN_CENTER + BOLD_ON + text("DESGLOSE DE DESCUENTOS\n") + BOLD_OFF + ALIGN_LEFT)
            # Headers: DESC., CANT., UNIT., SUBT.
            # Widths: Desc(8), Cant(6), Unit(9), Subt(10) -> 33 + spaces
            header = f"{'DESC.':<8} {'CANT.':^6} {'UNIT.':^9} {'SUBT.':>10}"
            buf.extend(text(header + "\n"))
            
            total_desc_sum = 0.0
            for d in discounts:
                # d: name, unit_desc, qty, price, subtotal
                # Note: database returns (name, unit_discount, qty, price, subtotal)
                # But subtotal is sale subtotal.
                # User wants "Total Descuento" which is sum of "SUBT." column?
                # Usually "SUBT." in discount table implies "Total DISCOUNT Amount" for that line.
                # Let's check logic. 
                # unit_desc = orig - price.
                # total_line_desc = unit_desc * qty.
                # Is 'subtotal' passed from DB the sales subtotal or discount subtotal?
                # DB Query: `SELECT ..., subtotal FROM sale_details`. This is Sales Subtotal.
                # We need Discount Subtotal.
                # Calculate it: unit_desc * qty.
                
                name = d[0]
                u_desc = float(d[1] or 0)
                qty = float(d[2] or 0)
                # price = d[3]
                
                line_desc_total = u_desc * qty
                total_desc_sum += line_desc_total
                
                buf.extend(text(f"{name[:42]}\n"))
                # Row values
                line = f"{fmt(u_desc):<8} {int(qty) if qty.is_integer() else fmt(qty):^6} {fmt(float(d[3])):^9} {fmt(line_desc_total):>10}"
                buf.extend(text(line + "\n"))
            
            buf.extend(ALIGN_CENTER + text(f"Total Descuento: S/ {fmt(total_desc_sum)}\n") + ALIGN_LEFT)
            buf.extend(text("-" * 42 + "\n"))
            
        # 5. DOCUMENTOS EMITIDOS
        docs = details.get('documents_list', [])
        if docs:
            buf.extend(ALIGN_CENTER + BOLD_ON + text("DOCUMENTOS EMITIDOS\n") + BOLD_OFF + ALIGN_LEFT)
            
            total_docs_amount = 0.0
            # Sort by type length for nicer look?
            for doc in docs:
                # doc: type, count, total
                dtype = doc[0] # BOLETA, FACTURA...
                count = doc[1]
                amt = float(doc[2] or 0)
                total_docs_amount += amt
                
                # Format: Type (Left) ... Qty (Center) ... Total (Right)
                # Remove "ELECTRÓNICA" to save space
                dtype_short = dtype.replace(" ELECTRÓNICA", "").replace(" DE VENTA", "")
                
                s_type = dtype_short[:18].ljust(18)
                s_qty = str(count).center(6)
                s_amt = fmt(amt).rjust(12)
                buf.extend(text(f"{s_type} {s_qty} {s_amt}\n"))
                
            buf.extend(ALIGN_CENTER + text(f"total: S/ {fmt(total_docs_amount)}\n") + ALIGN_LEFT)
        
        buf.extend(CUT)
        return buf

    def open_expenses_window(self):
        def update_total(new_total):
            self.expenses_var.set(new_total)
            self.calculate_total()
            
        ExpensesDetailsWindow(self, self.caja_id, update_total)

    def save_and_close(self):
        try:
             # Prepare Data
             # Fetch temp expenses sum to include in total expenses? 
             # Or assume they are added to expenses_var manually? 
             # The expenses_var is bound to the Entry. If open_expenses_window updates it, the value is in the var.
             
             
             # Capture closing time
             now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             self.closing_time_var.set(now_str)
             
             data = {
                 'caja_id': self.caja_id,
                 'start_time': self.start_time,
                 'end_time': now_str,
                 'user_id': "Admin",
                 
                 'system_cash': self.system_balance_var.get(), 
                 'counted_cash': self.physical_cash_var.get(),
                 'difference': self.difference_var.get(),
                 'correlative': self.next_correlative,
                 
                 'opening_time': self.opening_time_var.get(),
                 'accumulated_cash': self.system_balance_var.get(),
                 'stock_value': self.stock_value_var.get(),
                 'sales_cash': self.sales_cash_var.get(),
                 'income_additional': self.income_additional_var.get(),
                 'purchases': self.purchases_var.get(),
                 'anulados': self.anulados_var.get(),
                 'returns': self.returns_var.get(),
                 'withdrawal': self.withdrawal_var.get(),
                 
                 'initial_balance': self.last_accumulated_var.get(),
                 'expenses': self.expenses_var.get(),
                 'cards_deduction': self.cards_var.get(),
                 'change_next_day': self.system_balance_var.get(),
                 'collected_total': self.total_income_var.get(),
             }
             
             # Details JSON
             # Get temp expenses list
             tmps = database.get_temp_expenses(self.caja_id)
             expenses_list = [{'date':x[1], 'detail':x[2], 'amount':x[3], 'detail_2': (x[4] if len(x)>4 else "")} for x in tmps]
             
             # Fetch advanced analytics
             ranking_data = database.get_product_ranking_in_range(self.start_time, now_str)
             discounts_data = database.get_discount_details_in_range(self.start_time, now_str)
             docs_data = database.get_documents_summary_in_range(self.start_time, now_str)
             
             details = {
                 'grid_denominations': {k: v.get() for k,v in self.qty_vars.items()},
                 'petty_cash': self.petty_cash_var.get() if hasattr(self, 'petty_cash_var') else 0.0,
                 'expenses_list': expenses_list,
                 'ranking': ranking_data,
                 'discounts_details': discounts_data,
                 'docs_summary': docs_data
             }
             
             data['details_json'] = json.dumps(details)
             
             idx = database.save_cash_count(data)
             
             if idx:
                 database.clear_temp_expenses(self.caja_id)
                 
                 # Send Whatsapp
                 import threading
                 def _send_whatsapp_task():
                     try:
                         conn = database.create_connection() # Fresh conn for thread
                         # Need valid context. simple dict is valid.
                         self._send_whatsapp_notification(data) 
                         conn.close()
                     except: pass
                 threading.Thread(target=_send_whatsapp_task, daemon=True).start()
                 
                 messagebox.showinfo("Éxito", "Cierre guardado correctamente.")
                 self.print_cash_count()
                 self.destroy()
             else:
                 messagebox.showerror("Error", "Error al guardar en BD.")
                 
        except Exception as e:
            messagebox.showerror("Error", f"{e}")


class ExpensesDetailsWindow(ttk.Toplevel):
    def __init__(self, master, caja_id, callback_update_total):
        super().__init__(master)
        self.title("Detalles de Gastos")
        self.state('zoomed') # Maximized per request
        self.caja_id = caja_id
        self.callback_update = callback_update_total
        
        # Determine Start Time (Today 00:00:00 for implied date)
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        
        self.setup_ui()
        self.load_expenses()
        self.load_history()

    def setup_ui(self):
        # Two pane layout: Left (Registration/Current), Right (History)
        main_pane = ttk.Panedwindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- LEFT PANE ---
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        # Form
        form_frame = ttk.Labelframe(left_frame, text="Nuevo Gasto", padding=10)
        form_frame.pack(fill="x", pady=(0, 10))
        
        # Order: Monto, Detalle, Detalle 2, Agregar
        
        # Row 1: Monto
        ttk.Label(form_frame, text="Monto (S/):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.amount_var = tk.DoubleVar(value="") # Empty default visually if possible, or 0.0
        self.amount_entry = ttk.Entry(form_frame, textvariable=self.amount_var, width=15)
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Row 2: Detalle 1 (Combobox with Unique Values)
        ttk.Label(form_frame, text="Detalle 1:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Load unique details
        unique_details = database.get_unique_expense_details()
        self.detail_var = tk.StringVar()
        self.d1_combo = ttk.Combobox(form_frame, textvariable=self.detail_var, width=28, values=unique_details)
        self.d1_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # "+" Button: Clears selection/focus for new entry - REMOVED per user request
        # ttk.Button(form_frame, text="+", bootstyle="info-outline", command=self.clear_detail_for_new, width=3).grid(row=1, column=2, padx=5)

        # Row 3: Detalle 2
        ttk.Label(form_frame, text="Detalle 2:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.detail_2_var = tk.StringVar()
        self.detail_2_entry = ttk.Entry(form_frame, textvariable=self.detail_2_var, width=30)
        self.detail_2_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Add Button
        ttk.Button(form_frame, text="AGREGAR GASTO", command=self.add_expense, bootstyle="success", width=25).grid(row=3, column=0, columnspan=3, pady=15)
        
        # Current Session List
        current_list_frame = ttk.Labelframe(left_frame, text="Gastos Sesión Actual", padding=10)
        current_list_frame.pack(fill="both", expand=True)
        
        # Columns: Add 'fecha' content (hidden or visible? User said "que refleje en la tabla", so visible)
        cols_curr = ("id", "fecha", "detalle", "detalle2", "monto")
        self.tree = ttk.Treeview(current_list_frame, columns=cols_curr, show="headings")
        
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("detalle", text="Detalle 1")
        self.tree.heading("detalle2", text="Detalle 2")
        self.tree.heading("monto", text="Monto")
        
        self.tree.column("id", width=0, stretch=False)
        self.tree.column("fecha", width=90, anchor="center")
        self.tree.column("detalle", width=150, anchor="w")
        self.tree.column("detalle2", width=150, anchor="w")
        self.tree.column("monto", width=80, anchor="e")
        
        # Removed Scrollbar as requested
        # curr_scroll = ttk.Scrollbar(current_list_frame, orient="vertical", command=self.tree.yview)
        # self.tree.configure(yscrollcommand=curr_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        # curr_scroll.pack(side="right", fill="y")
        
        
        # Adjust dimensions (Smart stretch)
        # Fixed width for date and amount, expand details
        self.tree.column("fecha", width=90, anchor="center", stretch=False)
        self.tree.column("detalle", width=200, anchor="w", stretch=True)
        self.tree.column("detalle2", width=150, anchor="w", stretch=True)
        self.tree.column("monto", width=80, anchor="e", stretch=False)


        # --- RIGHT PANE ---
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=2)
        
        hist_frame = ttk.Labelframe(right_frame, text="Histórico de Gastos", padding=10)
        hist_frame.pack(fill="both", expand=True)
        
        # Filter
        filter_frame = ttk.Frame(hist_frame)
        filter_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(filter_frame, text="Buscar:").pack(side="left", padx=(0,5))
        
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *a: self.load_history())
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        filter_entry.pack(side="left", fill="x", expand=True)
        # Default placeholder logic could be added if needed
        
        # History Table
        cols_hist = ("fecha", "detalle", "detalle2", "monto")
        self.hist_tree = ttk.Treeview(hist_frame, columns=cols_hist, show="headings")
        
        self.hist_tree.heading("fecha", text="Fecha")
        self.hist_tree.heading("detalle", text="Detalle 1")
        self.hist_tree.heading("detalle2", text="Detalle 2")
        self.hist_tree.heading("monto", text="Monto")
        
        self.hist_tree.column("fecha", width=100, anchor="center")
        self.hist_tree.column("detalle", width=200, anchor="w")
        self.hist_tree.column("detalle2", width=150, anchor="w")
        self.hist_tree.column("monto", width=80, anchor="e")
        
        hist_scroll = ttk.Scrollbar(hist_frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hist_scroll.set)
        
        self.hist_tree.pack(side="left", fill="both", expand=True)
        hist_scroll.pack(side="right", fill="y")

        # Bottom Actions Frame
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(side="bottom", fill="x") # Pack at bottom of window
        
        # Delete Button (Left)
        ttk.Button(action_frame, text="Eliminar Seleccionado", command=self.delete_expense, bootstyle="danger-outline").pack(side="left")
        
        # Accept Button (Right)
        ttk.Button(action_frame, text="ACEPTAR", command=self.close_window, bootstyle="primary", width=20).pack(side="right")

    def load_expenses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        items = database.get_temp_expenses(self.caja_id)
        total = 0.0
        for item in items:
            # item: id, date, detail, amount, detail_2
            i_id = item[0]
            d_date = item[1] # Now we show it
            d1 = item[2]
            amt = item[3]
            d2 = item[4] if len(item) > 4 else ""
            
            self.tree.insert("", "end", values=(i_id, d_date, d1, d2, f"{amt:.2f}"))
            total += amt
            
        return total

    def clear_detail_for_new(self):
        self.detail_var.set("")
        self.d1_combo.focus()

    def load_history(self):
        try:
            for item in self.hist_tree.get_children():
                self.hist_tree.delete(item)
                
            f_text = self.filter_var.get()
            rows = database.get_expenses_history(f_text)
            
            for r in rows:
                # r: date, detail, detail2, amount
                self.hist_tree.insert("", "end", values=(r[0], r[1], r[2], f"{r[3]:.2f}"))
        except Exception as e:
            print(f"Error loading history: {e}")
            # Optionally show message or just log, better not to annoy user if it's transient


    def add_expense(self):
        detail = self.detail_var.get().strip()
        detail_2 = self.detail_2_var.get().strip()
        try:
            amount = float(self.amount_var.get())
        except:
            messagebox.showerror("Error", "Monto inválido")
            return
            
        if not detail:
            messagebox.showwarning("Aviso", "Ingrese al menos el Detalle 1")
            return
            
        if amount <= 0:
            messagebox.showwarning("Aviso", "El monto debe ser mayor a 0")
            return
            
        # Add with today's date
        database.add_temp_expense(self.caja_id, self.today_str, detail, amount, detail_2)
        
        self.load_expenses()
        
        # Clear fields
        self.detail_var.set("")
        self.detail_2_var.set("")
        self.amount_var.set("")
        self.amount_entry.focus()

    def delete_expense(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = self.tree.item(selected[0], 'values')[0]
        database.delete_temp_expense(item_id)
        self.load_expenses()

    def close_window(self):
        total = self.load_expenses()
        if self.callback_update:
            self.callback_update(total)
        self.destroy()
        

