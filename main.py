import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import database
from inventory_view import InventoryView
from sales_view import SalesWindow
from reports_view import ReportsView
from config_view import ConfigView
from movements_view import MovementsView
from customers_suppliers_view import CustomersSuppliersView # Importar la nueva vista

from login_view import LoginView
import whatsapp_manager
import config_manager
import theme_manager # Import entire module or specific function
import cpe_retry_service
import os

class MainWindow(ttk.Window):
    def __init__(self, user_data=None):
        # Inicializar la ventana con un tema de ttkbootstrap
        theme_name = config_manager.load_setting("system_theme", "Dark")
        boot_theme = "darkly" if theme_name == "Dark" else "litera" # Litera has rounded borders (Cosmo is square)
        super().__init__(themename=boot_theme)
        
        self.current_user = user_data 
        
        # Apply Custom Styles (including Header)
        theme_manager.apply_theme_styles(self.style)
        
        # self.withdraw() # Hide initially - REMOVED to show background
        
        self.title("Sistema de Gestión - Panel Principal")
        self.state('zoomed')
        self.sales_window = None
        
        self.user_data = None
        self.username = ""
        self.permissions = []

        self._bind_global_events()
        
        # Show login dialog
        # self.show_login()
        
        # --- BYPASS LOGIN (DEV MODE) ---
        self.user_data = (1, "admin", "admin") # ID, Username, Permissions
        self.username = "admin"
        self.permissions = ["admin"]
        self.setup_ui()
        self.deiconify()
        # -------------------------------

    def setup_ui(self):
        self.title(f"Sistema de Gestión - Panel Principal - Usuario: {self.username}")
        
        # --- Header ---
        # Refactored to use Canvas for Gradient Background
        header_height = 80
        header_canvas = tk.Canvas(self, height=header_height, highlightthickness=0, background=theme_manager.COLOR_HEADER_BG)
        header_canvas.pack(fill="x", side="top")
        
        # Initial Gradient Binding
        def update_header_gradient(event):
            w = event.width
            h = event.height
            if w < 10: return
            
            # Get Gradient Image
            grad_img = theme_manager.get_header_gradient(width=w, height=h)
            
            # Update Canvas Image
            # Check if image item exists
            if hasattr(header_canvas, 'gradient_id'):
                 header_canvas.itemconfigure(header_canvas.gradient_id, image=grad_img)
            else:
                 header_canvas.gradient_id = header_canvas.create_image(0, 0, image=grad_img, anchor="nw")
                 header_canvas.lower(header_canvas.gradient_id) # Send to back
            
            # Keep reference
            header_canvas.image = grad_img
            
             # Reposition user button
            header_canvas.coords(btn_window, w - 120, 40)

        header_canvas.bind("<Configure>", update_header_gradient)

        # Title Text on Canvas (White for contrast)
        header_canvas.create_text(
            20, 40, 
            text="SISTEMA DE VENTAS Y GESTIÓN", 
            font=("Segoe UI", 18, "bold"), 
            fill="#FFFFFF",
            anchor="w"
        )
        
        # User Button
        user_button = ttk.Button(
            header_canvas,
            text=f"👤 {self.username}",
            bootstyle="primary",
            command=lambda: messagebox.showinfo("Usuario", f"Sesión iniciada como: {self.username}")
        )
        
        # Place User Button on Canvas
        btn_window = header_canvas.create_window(1000, 40, window=user_button, anchor="center") # Initial pos, updated in Configure

        # --- Panel de Módulos ---
        modules_frame = ttk.Frame(self, padding=40)
        modules_frame.pack(expand=True, fill="both")

        # --- Iconos para los módulos ---
        # (Icono Emoji, Título, Comando, Permiso Requerido)
        # "admin" permission grants access to everything
        all_modules = [
            ("🛒", "Realizar Venta", self.open_sales, "Realizar Venta"),
            ("📊", "Ventas Realizadas", self.open_reports, "Ventas Realizadas"),
            ("🏭", "Almacén", self.open_inventory, "Almacén"),
            ("👥", "Clientes y\nProveedores", self.open_customers_suppliers, "Clientes y Proveedores"),
            ("📋", "Ingresos y\nSalidas", self.open_movements, "Ingresos y Salidas"),
            ("🚛", "Guías de\nRemisión", self.coming_soon, "Guías de Remisión"),
            ("📈", "Reportes\nAvanzados", self.coming_soon, "Reportes Avanzados"),
            ("⚙️", "Configuración", self.open_config, "Configuración"),
            ("🧾", "SIRE\n(SUNAT)", self.coming_soon, "SIRE")
        ]

        # Filter modules based on permissions
        visible_modules = []
        is_admin = "admin" in self.permissions
        
        for icon, title, command, perm in all_modules:
            if is_admin or perm in self.permissions:
                visible_modules.append((icon, title, command))

        # Configurar la grid para que los botones se expandan
        modules_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")
        # Estimate rows needed
        import math
        rows_needed = math.ceil(len(visible_modules) / 3)
        for r in range(rows_needed):
            modules_frame.grid_rowconfigure(r, weight=1, uniform="group1")

        row, col = 0, 0
        for icon, title, command in visible_modules:
            self.create_dashboard_tile(modules_frame, icon, title, command, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def create_dashboard_tile(self, parent, icon, title, command, row, col):
        # Frame contenedor (Tile) - Default Style: Dashboard (Standard)
        tile = ttk.Frame(parent, style="Dashboard.TFrame", padding=10, cursor="hand2")
        tile.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
        
        # --- Gradient Background Image (Hidden by default) ---
        # Generate or get gradient image (Large enough to cover tile)
        # Note: In a real app we might resize on configure, but for now fixed large size is fine.
        gradient_img = theme_manager.get_dashboard_gradient(width=600, height=400) 
        
        bg_label = ttk.Label(tile, image=gradient_img, borderwidth=0)
        # We don't pack/grid distinctively yet, we will place it on hover or strictly keep it behind.
        # Better: Place it to cover everything, but put it "bottom".
        # However, if we place it at bottom, other widgets (icon/text) need to have transparent backgrounds.
        # ttk widgets (Label) usually take background from style.
        # If we change style to "DashboardPrimary", it has solid background.
        # To show IMAGE gradient, widgets must be transparent or share the background.
        # Tkinter transparency is tricky.
        # WORKAROUND:
        # On Hover:
        # 1. Show bg_label via place(relwidth=1, relheight=1).
        # 2. Lift bg_label? No, lower it.
        # 3. Ensure Icon/Title labels have transparent background?
        #    ttk.Label background is handled by style. We need a style with "transparent" or matching background?
        #    We can't easily match a gradient.
        #    ACTUALLY: The user's image shows solid gradient background with text on top.
        #    If I put a Label with image, and the text Labels have a "Background" color... they will block the gradient.
        #    Unless I can make them transparent.
        #    Standard trick: Label background = Tile background? No, Tile has gradient.
        #    If I cannot make Labels transparent (which is hard in standard tkinter without canvas),
        #    I might have to stick to "Option A" (Solid Color) internally or use Canvas.
        #    BUT wait, I can simulate transparency by taking a snapshot? No.
        #    Let's try to set the Label background to a color close to the gradient average? No, looks bad.
        #    
        #    Recalculating:
        #    User REALLY wants the gradient.
        #    If I use a Canvas for the Tile, I can draw the image and text on top transparently.
        #    Let's try switching `tile` to a Canvas?
        #    Or just use the SOLID color `DashboardPrimary` (which is what I implemented before) 
        #    and tell the user "Sorry, gradient requires image background which conflicts with text labels in this framework, I enabled the "Highlight" solid color option which is very similar".
        #    
        #    Wait, look at `theme_manager.py`: `GRADIENT_START/END` were added.
        #    Create a style for "DashboardGradient"?
        #    No, ttk styles don't support gradients.
        #    
        #    Let's try the canvas approach for `create_dashboard_tile`.
        #    It gives me full control.
        #    
        #    New Plan for `create_dashboard_tile`:
        #    1. Create a `tk.Canvas` (not ttk.Frame).
        #    2. Draw the Gradient Image on the Canvas (hidden or shown).
        #    3. Create Text/Icon objects on the Canvas (create_text).
        #     This supports "transparency" naturally.
        
        # Re-implementation using Canvas
        tile_canvas = tk.Canvas(parent, background=theme_manager.COLOR_CARD_BG, highlightthickness=0, cursor="hand2")
        tile_canvas.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
        
        # Center reference
        # We need to bind configure to center text? Or just use width/2, height/2.
        
        # Persistent Ref to Image to prevent GC
        tile_canvas.image = gradient_img 
        
        # Add Gradient (Hidden initially)
        # Create it but set state='hidden'
        gradient_id = tile_canvas.create_image(0, 0, image=gradient_img, anchor="nw", state="hidden")
        
        # We need to update image position/size/center?
        # Just anchor "nw" is fine if image is huge.
        
        # Text/Icon
        # Need coordinates. Canvas doesn't use pack/grid.
        # This makes layout harder (responsiveness).
        # The tiles are grid cells.
        # I can use `place` to put a Transparent Frame on top?
        # Tkinter Frames are not transparent.
        
        # HYBRID APPROACH:
        # Use a Canvas as the background container.
        # Place the Gradient Image on the Canvas.
        # Place the Icon/Text as `create_text` items on the Canvas (ensures transparency).
        # Handle layout by binding `<Configure>` to update text positions to width/2, height/2.
        
        # Let's do this.
        
        # Bind Resize to update center
        def on_resize(e):
            w, h = e.width, e.height
            cx, cy = w / 2, h / 2
            # Update Text Positions
            tile_canvas.coords(icon_id, cx, cy - 30)
            tile_canvas.coords(title_id, cx, cy + 30)
            # Update Gradient? If image is big enough (600x400), and tile < 600x400, no need to move it, just anchor nw.
            
        tile_canvas.bind("<Configure>", on_resize)
        
        # Create Items
        # Icon
        icon_id = tile_canvas.create_text(
            150, 100, # Initial dummy
            text=icon, 
            font=("Segoe UI Emoji", 48), 
            fill=theme_manager.COLOR_CARD_FG,
            anchor="center"
        )
        
        # Title
        title_id = tile_canvas.create_text(
            150, 160, # Initial dummy
            text=title, 
            font=("Segoe UI", 14, "bold"), 
            fill=theme_manager.COLOR_CARD_FG,
            anchor="center",
            justify="center"
        )
        
        # Events
        def on_click(e):
            command()
            
        def on_enter(e):
            tile_canvas.itemconfigure(gradient_id, state="normal")
            tile_canvas.itemconfigure(icon_id, fill=theme_manager.COLOR_CARD_PRIMARY_FG)
            tile_canvas.itemconfigure(title_id, fill=theme_manager.COLOR_CARD_PRIMARY_FG)
            self.config(cursor="hand2")
            
        def on_leave(e):
            tile_canvas.itemconfigure(gradient_id, state="hidden")
            tile_canvas.itemconfigure(icon_id, fill=theme_manager.COLOR_CARD_FG)
            tile_canvas.itemconfigure(title_id, fill=theme_manager.COLOR_CARD_FG)
            self.config(cursor="")
            
        tile_canvas.bind("<Button-1>", on_click)
        tile_canvas.bind("<Enter>", on_enter)
        tile_canvas.bind("<Leave>", on_leave)
        
        # Propagate click to items? Canvas binds apply to the widget.
        # We don't need tag_bind unless we want specific item clicks. 
        # Binding on Canvas widget catches all clicks on it.
        
        # Add a border?
        # Canvas has no 'border' style like ttk.
        # We can draw a rectangle?
        # Or just rely on background color separation.
        # Adding a subtle border rect is nice.
        
        # border_id = tile_canvas.create_rectangle(0, 0, 1, 1, outline=theme_manager.COLOR_ACCENT, width=1)
        # Update in resize?
        
        # Let's keep it clean without border first, or add a simple one.
        # User is using Light theme, cards usually have shadow/border.
        # I'll rely on the background color contrast (White vs Gray).
        return tile_canvas

    def _bind_global_events(self):
        def select_all(event):
            widget = event.widget
            # Check if widget is capable of selection and not disabled
            try:
                if widget.cget('state') == 'disabled':
                    return
                # For Comboboxes, readonly state allows selection but not editing text.
                # User wants to select text to potentially replace it (if editable) or just see it selected.
                
                widget.select_range(0, 'end')
                widget.icursor('end') # Optional: move cursor to end
            except tk.TclError:
                pass # Widget might not support selection or other error

        self.bind_class("TEntry", "<FocusIn>", select_all, add="+")
        self.bind_class("TCombobox", "<FocusIn>", select_all, add="+")

    def _set_proportional_geometry(self, window, width_ratio=0.9, height_ratio=0.9):
        """Calcula y centra la geometría de una ventana Toplevel."""
        # No es necesario para la ventana principal maximizada, pero útil para las hijas
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        width = int(screen_width * width_ratio)
        height = int(screen_height * height_ratio)
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        try:
            window.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            # Puede fallar si la ventana ya está destruida
            pass

    def open_sales(self):
        if not self.verify_identity("Realizar Venta"): return
        
        # --- Check Daily Opening Time ---
        import config_manager
        from datetime import datetime
        
        current_opening = config_manager.load_setting("daily_opening_time")
        now = datetime.now()
        
        # Check if opening time is from today
        is_today = False
        if current_opening:
            try:
                # Try to parse it
                # Assuming format "YYYY-MM-DD HH:MM:SS"
                op_date_str = current_opening.split()[0]
                today_str = now.strftime("%Y-%m-%d")
                if op_date_str == today_str:
                    is_today = True
            except:
                pass
        
        if not is_today:
            # First access of the day (or first time setting it)
            new_opening = now.strftime("%Y-%m-%d %H:%M:%S")
            config_manager.save_setting("daily_opening_time", new_opening)
            print(f"Apertura del día registrada: {new_opening}")
            
        if self.sales_window is None or not self.sales_window.winfo_exists():
            self.sales_window = SalesWindow(self)
            # SalesWindow ya se maximiza por sí misma
        else:
            self.sales_window.deiconify()
        self.sales_window.lift()
        self.sales_window.focus_force()

    def open_inventory(self):
        if not self.verify_identity("Almacén"): return
        # En lugar de Toplevel, usamos ttk.Toplevel para heredar el tema
        win = InventoryView(self) 
        self._set_proportional_geometry(win, 0.8, 0.7)
        win.grab_set()
        self.wait_window(win)
        # Recargar productos en la vista de ventas si está abierta
        if self.sales_window and self.sales_window.winfo_exists():
            for tab in self.sales_window.sales_tabs:
                tab.load_products_from_db()
        
    def open_reports(self):
        if not self.verify_identity("Ventas Realizadas"): return
        win = ReportsView(self)
        self._set_proportional_geometry(win, 0.85, 0.8)
        win.grab_set()

    def open_config(self):
        if not self.verify_identity("Configuración"): return
        win = ConfigView(self)
        self._set_proportional_geometry(win, 0.7, 0.6)
        win.grab_set()
        self.wait_window(win)
        # Recargar emisores en la vista de ventas si está abierta
        if self.sales_window and self.sales_window.winfo_exists():
            for tab in self.sales_window.sales_tabs:
                tab.load_issuers_from_db()

    def verify_identity(self, permission=None):
        """
        Verifica si el módulo está protegido (tiene usuarios asignados).
        - Si NO tiene usuarios: Acceso Libre.
        - Si TIENE usuarios: Requiere que el usuario actual (self.current_user) tenga ese permiso Y se autentique.
        """
        if not permission: return True # No specific protection requested? Default allow.

        # 1. Check if Module is Protected (Has assigned users)
        assigned_users = database.get_users_by_permission(permission)
        if not assigned_users:
            # No users assigned to this module -> Free Access
            return True
            
        # 2. Module IS Protected.
        # We need a valid current_user session.
        if not self.current_user:
            messagebox.showwarning("Acceso Restringido", f"El módulo '{permission}' está protegido. Debe iniciar sesión.", parent=self)
            # Potentially trigger login, but main window usually handles global login.
            # Returning False blocks access.
            return False
            
        user_id = self.current_user[0]
        user_perms_str = self.current_user[2]
        user_perms = user_perms_str.split(",") if user_perms_str else []
        
        # 3. Check if CURRENT user is authorized for this module
        # Allow if:
        # - Has 'admin' permission
        # - Has specific module permission
        # - Username is 'admin' (Failsafe)
        
        is_admin_perm = "admin" in user_perms
        has_module_perm = permission in user_perms
        is_admin_user = (self.current_user[1].lower() == 'admin') # Case insensitive
        
        print(f"DEBUG: verify_identity: User='{self.current_user[1]}', Perms={user_perms}, Target='{permission}'")
        print(f"DEBUG: Logic: AdminPerm={is_admin_perm}, ModulePerm={has_module_perm}, IsAdminName={is_admin_user}")
        
        if not is_admin_perm and not has_module_perm and not is_admin_user:
             messagebox.showerror("Acceso Denegado", f"Su usuario no tiene permiso para: {permission}", parent=self)
             return False
             
        # 4. Authenticate (Password Check)
        # Even if logged in, we verify password again for sensitive action?
        # User request: "antes de ingresar... aparezca la ventana loguin"
        # If I am already logged in globally, do I need to re-enter password?
        # "Modulos ... que si contengan usuarios ... aparezca la ventana loguin"
        # This implies re-verification or initial login.
        # Since this is a POS, re-verification is safer.
        
        if database.user_has_password(user_id):
            from tkinter import simpledialog
            password = simpledialog.askstring("Seguridad", f"Módulo Protegido: {permission}\nIngrese contraseña:", show='*', parent=self)
            if password is None: return False
            
            if database.check_user_password(user_id, password):
                return True
            else:
                messagebox.showerror("Error", "Contraseña incorrecta.", parent=self)
                return False
                
        return True

    def open_movements(self):
        # Security Check
        if not self.verify_identity("Ingresos y Salidas"):
            return
            
        win = MovementsView(self)
        self._set_proportional_geometry(win, 0.9, 0.8)
        win.grab_set()
        self.wait_window(win)
        # Recargar productos en ventas y almacén si están abiertos
        if self.sales_window and self.sales_window.winfo_exists():
            for tab in self.sales_window.sales_tabs:
                tab.load_products_from_db()

    def open_customers_suppliers(self):
        if not self.verify_identity("Clientes y Proveedores"): return
        win = CustomersSuppliersView(self)
        self._set_proportional_geometry(win, 0.9, 0.8)
        win.grab_set()
        self.wait_window(win)

    def coming_soon(self):
        messagebox.showinfo("Próximamente", "Este módulo está en desarrollo y estará disponible en futuras actualizaciones.", parent=self)

def main():
    # Asegurarse de que la base de datos está lista
    database.setup_database()
    
    # Iniciar servicio WhatsApp en segundo plano
    print("Iniciando servicio de WhatsApp...")
    whatsapp_manager.baileys_manager.start_service()

    # Iniciar servicio de Reintento de CPE
    print("Iniciando servicio de Reintento de CPE...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    retry_service = cpe_retry_service.CPERetryService(base_dir)
    retry_service.start()

    retry_service = cpe_retry_service.CPERetryService(base_dir)
    retry_service.start()

    # 1. Initialize Main App (Hidden)
    # We pass None initially, then set it after login
    app = MainWindow(user_data=None)
    app.withdraw() # Hide main window
    
    # Check "Require Login" setting
    # Check "Require Login" setting
    # sys_config = config_manager.load_config().get("system", {}) # Safer loading
    # require_login_val = sys_config.get("require_login", "Si") # Logic matching config_view
    # Or rely on load_setting helper if updated. 
    # Current code uses: config_manager.load_setting('require_login', 'Si') which might fail if key is in 'system' sub-dict.
    # I will stick to what seems to be working or safer.
    
    # 0. Check for Zero Users (SuperAdmin Bypass)
    all_users = database.get_all_users()
    user_data = None
    
    if not all_users:
        print("DEBUG: No users found. Starting in SuperAdmin mode.")
        user_data = (0, "SuperAdmin", "admin") # Virtual admin
    else:
        # New Logic: "Ventana Principal" Protection
        vp_users = database.get_users_by_permission("Ventana Principal")
        if not vp_users:
             # No users assigned to Main Window -> Free Access
             print("DEBUG: 'Ventana Principal' is unprotected. Starting as Guest.")
             user_data = (0, "Guest", "") # Guest user
        else:
             # Protected -> Login Required
             print("DEBUG: 'Ventana Principal' is protected. Login required.")
             # user_data remains None, triggering login flow below
             pass
    
    if not user_data:
        # Show Login if required OR if auto-login failed
        from login_view import LoginView
        # LoginView is a Toplevel, master is app
        login = LoginView(app) 
        
        # Ensure login is visible
        login.deiconify()
        login.lift()
        login.focus_force()
        
        # Wait for login
        app.wait_window(login)
        
        # 3. Check Result
        user_data = getattr(login, 'user_data', None)
    
    if user_data:
        # Success: Update user and show main window
        app.current_user = user_data
        app.deiconify()
        app.state('zoomed') # Force maximize
        
        # Define closing behavior here or in __init__
        def on_closing():
            if messagebox.askokcancel("Salir", "¿Desea salir de la aplicación?"):
                print("Cerrando aplicación y deteniendo servicios...")
                whatsapp_manager.baileys_manager.stop_service()
                retry_service.running = False 
                app.destroy()
        
        app.protocol("WM_DELETE_WINDOW", on_closing)
        app.mainloop()
    else:
        # Failure: Destroy app
        print("Login cancelado o fallido.")
        whatsapp_manager.baileys_manager.stop_service()
        retry_service.running = False
        try:
            app.destroy()
        except:
             pass

if __name__ == "__main__":
    main()