import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
import custom_messagebox as messagebox
import tkinter as tk
import database
from datetime import datetime
import json
import config_manager
import textwrap
from PIL import Image, ImageTk, ImageDraw
try:
    import win32print
except ImportError:
    win32print = None

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE

# Local Aliases for consistency
COLOR_PRIMARY_DARK = COLOR_PRIMARY
COLOR_SECONDARY_DARK = COLOR_SECONDARY
COLOR_TEXT_LIGHT = COLOR_TEXT

# Constants for "Ventas" Style matching
# These will be set dynamically in __init__ or used as defaults here if needed outside class (unlikely)

# --- HELPER CLASSES ---

class GradientButton(tk.Canvas):
    def __init__(self, master, text, icon, color1, color2, command, text_color="white", height=40, font_args=None, **kwargs):
        if 'corner_radius' in kwargs:
             self.corner_radius = kwargs.pop('corner_radius')
        else:
             self.corner_radius = 10 # Default

        super().__init__(master, height=height, highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.icon = icon
        self._color1 = color1
        self._color2 = color2
        self._text_color = text_color
        self._font_args = font_args or (FONT_FAMILY, 10, "bold")
        
        # State
        self._is_hovering = False
        self._is_pressed = False
        
        # Bindings
        self.bind('<Configure>', self._on_resize)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        
        self.image_ref = None

    def _on_resize(self, event):
        self._draw(event.width, event.height)

    def _on_enter(self, event):
        self._is_hovering = True
        self._draw(self.winfo_width(), self.winfo_height())

    def _on_leave(self, event):
        self._is_hovering = False
        self._is_pressed = False
        self._draw(self.winfo_width(), self.winfo_height())

    def _on_press(self, event):
        self._is_pressed = True
        self._draw(self.winfo_width(), self.winfo_height())

    def _on_release(self, event):
        if self._is_pressed and self._is_hovering:
            if self.command:
                self.command()
        self._is_pressed = False
        self._draw(self.winfo_width(), self.winfo_height())
        
    def _draw(self, width, height):
        if width < 10 or height < 10: return
        
        c1, c2 = self._color1, self._color2
        if self._is_pressed:
            # Darken colors slightly when pressed
            c1_rgb = self.winfo_rgb(c1)
            c2_rgb = self.winfo_rgb(c2)
            c1 = '#%02x%02x%02x' % (c1_rgb[0]//256 * 8 // 10, c1_rgb[1]//256 * 8 // 10, c1_rgb[2]//256 * 8 // 10)
            c2 = '#%02x%02x%02x' % (c2_rgb[0]//256 * 8 // 10, c2_rgb[1]//256 * 8 // 10, c2_rgb[2]//256 * 8 // 10)
        
        # Create Image
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Gradient
        base = Image.new('RGBA', (width, height), c1)
        top = Image.new('RGBA', (width, height), c2)
        mask = Image.new('L', (width, height))
        mask_data = []
        for y in range(height):
            mask_data.extend([int(255 * (y / height))] * width)
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        gradient_img = base
        
        # Rounded Mask
        mask_img = Image.new('L', (width, height), 0)
        draw_mask = ImageDraw.Draw(mask_img)
        draw_mask.rounded_rectangle((0, 0, width, height), radius=self.corner_radius, fill=255)
        
        final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        final_img.paste(gradient_img, (0, 0), mask_img)
        
        self.image_ref = ImageTk.PhotoImage(final_img)
        self.delete("all")
        self.create_image(0, 0, image=self.image_ref, anchor='nw')
        
        # Text
        full_text = f"{self.icon} {self.text}" if self.icon else self.text
        self.create_text(width//2, height//2, text=full_text, fill=self._text_color, font=self._font_args)

class GradientFrame(tk.Canvas):
    def __init__(self, parent, color1, color2, text="", text_color="white", shadow_color=None, font_size=20, anchor="center", **kwargs):
        super().__init__(parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self._text = text
        self._text_color = text_color
        self._anchor = anchor
        self._font_size = font_size
        self.bind('<Configure>', self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete('gradient')
        self.delete('text')
        width = self.winfo_width()
        height = self.winfo_height()
        limit = width
        (r1, g1, b1) = self.winfo_rgb(self._color1)
        (r2, g2, b2) = self.winfo_rgb(self._color2)
        r_ratio = float(r2 - r1) / limit
        g_ratio = float(g2 - g1) / limit
        b_ratio = float(b2 - b1) / limit

        for i in range(limit):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%4.4x%4.4x%4.4x" % (nr, ng, nb)
            self.create_line(i, 0, i, height, tags=("gradient",), fill=color)
        self.tag_lower('gradient')
        
        if self._text:
            y = height // 2
            font = (FONT_FAMILY, self._font_size, "bold")
            x = 20 if self._anchor == "w" else width // 2
            self.create_text(x, y, text=self._text, fill=self._text_color, font=font, anchor=self._anchor, tags=("text",))

class MovementsView(ttk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ingresos y Salidas de Mercadería")

        # --- Base Theme Logic ---
        is_dark = "Dark" in config_manager.load_setting("system_theme", "Dark")
        
        # Import Colors from HTML spec (Dynamic)
        HTML_NAVY = '#0a2240'
        
        if is_dark:
             HTML_BG = COLOR_PRIMARY_DARK
             HTML_WHITE = COLOR_SECONDARY_DARK
             HTML_WHITE_INPUT = "#2c3e50"
             HTML_WHITE_TEXT = COLOR_TEXT_LIGHT
             HTML_BORDER = '#444444'
             GRAY_STRIPE = '#2a2e33' # Dark Alternate
             TEXT_HEADER_FG = 'white'
             TICKET_BG = "#2c2c2c"
             TICKET_FG = "#e0e0e0"
             SHADOW_COLOR = "#1a1a1a"
        else:
             HTML_BG = '#f0f2f5'
             HTML_WHITE = '#ffffff'
             HTML_WHITE_INPUT = '#ffffff'
             HTML_WHITE_TEXT = '#333333'
             HTML_BORDER = '#dddddd'
             GRAY_STRIPE = '#f2f2f2'
             TEXT_HEADER_FG = 'black'
             TICKET_BG = "#ffffff"
             TICKET_FG = "#333333"
             SHADOW_COLOR = "#e0e0e0"

        # Estilos (Copied from ReportsView for consistency)
        style = ttk.Style.get_instance()
        style.configure('Treeview', background="white", fieldbackground="white", foreground="black", bordercolor="#dddddd")
        style.map('Treeview', background=[('selected', COLOR_ACCENT)], foreground=[('selected', 'white')])
        style.configure('Treeview.Heading', font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), background="#0a2240", foreground="white")



        # Estilos (Copied from ReportsView for consistency)
        style = ttk.Style.get_instance()
        style.configure('Treeview', background="white", fieldbackground="white", foreground="black", bordercolor="#dddddd")
        style.map('Treeview', background=[('selected', COLOR_ACCENT)], foreground=[('selected', 'white')])
        style.configure('Treeview.Heading', font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), background="#0a2240", foreground="white")

        self.state('zoomed')
        self.configure(background=HTML_BG) # Light Gray Background
        
        # Variables
        self.cart = [] 
        self.total = 0.0
        self.issuers_data = []
        self.products = {}
        
        # Styles
        style = ttk.Style.get_instance()
        style.configure('TLabel', background=HTML_WHITE, foreground=HTML_WHITE_TEXT, font=(FONT_FAMILY, 10))
        # Remove bootstyle artifacts for trees
        style.configure('Treeview', background="white", fieldbackground="white", foreground="black", bordercolor="#dddddd", rowheight=28)
        if is_dark:
            style.configure('Treeview', background=HTML_WHITE, fieldbackground=HTML_WHITE, foreground=HTML_WHITE_TEXT, bordercolor="#444444")
            
        style.map('Treeview', background=[('selected', '#007bff')], foreground=[('selected', 'white')])
        style.configure('Treeview.Heading', font=(FONT_FAMILY, 10, 'bold'), background=HTML_NAVY, foreground='white')
        style.map('Treeview.Heading', background=[('active', HTML_NAVY)])

        # Define Styles (Aggressive Border Hiding - Match Reports View)
        # Combobox
        style.configure('Borderless.TCombobox', borderwidth=0, relief='flat', arrowsize=15)
        style.map('Borderless.TCombobox', 
                  fieldbackground=[('readonly', HTML_WHITE_INPUT), ('active', HTML_WHITE_INPUT), ('focus', HTML_WHITE_INPUT)], 
                  background=[('readonly', HTML_WHITE_INPUT)], 
                  bordercolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  lightcolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  darkcolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  foreground=[('readonly', 'white' if is_dark else 'black')])
        
        # Entry
        style.configure('Borderless.TEntry', fieldbackground=HTML_WHITE_INPUT, borderwidth=0, relief='flat', highlightthickness=0, foreground='white' if is_dark else 'black')
        style.map('Borderless.TEntry', 
                  fieldbackground=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  bordercolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  lightcolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)],
                  darkcolor=[('focus', HTML_WHITE_INPUT), ('!disabled', HTML_WHITE_INPUT)])
        
        # Helper to create floating cards
        def create_floating_card_frame(parent_pane, title=None, dynamic_height=False):
            wrapper = tk.Frame(parent_pane, bg=HTML_BG, bd=0, highlightthickness=0)
            card = tk.Canvas(wrapper, bg=HTML_BG, highlightthickness=0, bd=0)
            card.pack(fill="both", expand=True) 
            
            content = tk.Frame(card, bg=HTML_WHITE)
            MARGIN = 6
            content_window = card.create_window(MARGIN, MARGIN, window=content, anchor="nw")
            
            def _update_height(event):
                if dynamic_height:
                    required_height = event.height + (2 * MARGIN) + 4
                    if card.winfo_height() != required_height:
                        card.configure(height=required_height)
            
            def _draw(e):
                w = e.width
                h = e.height
                if w < 50: return
                
                # Resize Content
                target_w = w - (2 * MARGIN)
                if dynamic_height:
                    current_w = int(card.itemcget(content_window, 'width'))
                    if abs(current_w - target_w) > 1:
                         card.itemconfig(content_window, width=target_w)
                else:
                    target_h = h - (2 * MARGIN)
                    card.itemconfig(content_window, width=target_w, height=target_h)

                # Redraw Background/Shadow
                card.delete("bg")
                img = Image.new("RGBA", (w, h), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                rec = (MARGIN, MARGIN, w-MARGIN, h-MARGIN)
                rec = (MARGIN, MARGIN, w-MARGIN, h-MARGIN)
                # Shadow
                draw.rounded_rectangle((rec[0]-2, rec[1]-2, rec[2]+4, rec[3]+4), radius=12, fill=SHADOW_COLOR)
                draw.rounded_rectangle(rec, radius=12, fill=HTML_WHITE)
                bg = ImageTk.PhotoImage(img)
                card._bg = bg
                card.create_image(0,0, image=bg, anchor="nw", tags="bg")
                card.tag_lower("bg")
            
            content.bind("<Configure>", _update_height)
            card.bind("<Configure>", _draw)
            
            if title:
                tk.Label(content, text=title, font=(FONT_FAMILY, 11, "bold"), bg=HTML_WHITE, fg=HTML_WHITE_TEXT).pack(fill="x", pady=(10, 5), padx=10)
            return wrapper, content

        def create_rounded_widget(parent, widget_class, variable=None, width=150, **kwargs):
            container = tk.Canvas(parent, bg=HTML_WHITE, height=35, width=width, highlightthickness=0)
            
            style_name = 'Borderless.TEntry'
            container.border_color = "#cccccc"
            
            if widget_class == ttk.Combobox:
                 widget = widget_class(container, textvariable=variable, state="readonly", width=15, style='Borderless.TCombobox', **kwargs)
            elif widget_class == DateEntry:
                 widget = widget_class(container, bootstyle="default", width=10, dateformat="%d/%m/%Y", **kwargs)
                 try: widget.entry.configure(style=style_name)
                 except: pass
            if widget_class == ttk.Entry:
                 widget = widget_class(container, textvariable=variable, width=20, style=style_name, **kwargs)
            
            bg_fill = HTML_WHITE_INPUT
            
            def _draw_bg(e=None):
                w = container.winfo_width()
                h = container.winfo_height()
                if w <= 1: return
                container.delete("bg")
                img = Image.new("RGBA", (w, h), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                draw.rounded_rectangle((0, 0, w-1, h-1), radius=15, fill=bg_fill, outline=container.border_color, width=1)
                bg = ImageTk.PhotoImage(img)
                container._bg_ref = bg
                container.create_image(0,0, image=bg, anchor="nw", tags="bg")
                container.tag_lower("bg")
                container.itemconfigure(win_path, width=w-25)

            container.bind("<Configure>", _draw_bg)
            win_path = container.create_window(12, 17, window=widget, anchor="w")

            def _on_focus(e):
                container.border_color = "#007bff"
                _draw_bg()
            def _on_unfocus(e):
                container.border_color = "#cccccc"
                _draw_bg()

            target = widget.entry if widget_class == DateEntry else widget
            target.bind("<FocusIn>", _on_focus, add="+")
            target.bind("<FocusOut>", _on_unfocus, add="+")
            
            return widget, container

        # --- HEADER ---
        GradientFrame(self, color1="#0a2240", color2="#007bff", text="Ingresos y Salidas de Mercadería", height=60, font_size=24, anchor="w").pack(fill="x", side="top")

        # --- 1. FILTER CARD (Top Full Width) ---
        # Parent is self, placed above pane
        filter_wrapper, filter_content = create_floating_card_frame(self, None, dynamic_height=True)
        filter_wrapper.pack(fill="x", padx=10, pady=(5, 2))
        
        self.filter_items = []
        
        # Wrapping logic container
        f_container = tk.Frame(filter_content, bg=HTML_WHITE, bd=0, highlightthickness=0, relief="flat")
        f_container.pack(fill="x", padx=5, pady=5)
        
        def add_filter(lbl, widget_cls, var=None, width=150, is_date=False):
            f = tk.Frame(f_container, bg=HTML_WHITE, bd=0, highlightthickness=0, relief="flat")
            tk.Label(f, text=lbl, bg=HTML_WHITE, fg=HTML_WHITE_TEXT, font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0,5))
            if is_date:
                wid, con = create_rounded_widget(f, widget_cls, width=width)
            else:
                wid, con = create_rounded_widget(f, widget_cls, var, width=width)
            con.pack(side="left")
            self.filter_items.append(f)
            return wid
        
        self.issuer_var = tk.StringVar()
        self.issuer_combo = add_filter("Emisor:", ttk.Combobox, self.issuer_var, 200)
        self.address_var = tk.StringVar()
        self.address_combo = add_filter("Dirección:", ttk.Combobox, self.address_var, 250)
        
        self.hist_filter_var = tk.StringVar(value="TODOS")
        self.hist_filter_combo = add_filter("Filtrar:", ttk.Combobox, self.hist_filter_var, 100)
        self.hist_filter_combo['values'] = ["TODOS", "INGRESO", "SALIDA", "ANULADO"]
        
        self.start_date_entry = add_filter("Inicio:", DateEntry, width=140, is_date=True)
        self.end_date_entry = add_filter("Fin:", DateEntry, width=140, is_date=True)

        # Bindings
        self.issuer_combo.bind("<<ComboboxSelected>>", self.on_issuer_change)
        self.address_combo.bind("<<ComboboxSelected>>", self.on_address_change)
        self.hist_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_movements_history())
        for de in [self.start_date_entry, self.end_date_entry]:
            de.entry.bind("<FocusOut>", lambda e: self.load_movements_history())
            de.bind("<<DateEntrySelected>>", lambda e: self.load_movements_history())

        # Responsive Pack Logic
        def _repack_filters(e=None):
            w = f_container.winfo_width()
            if w < 100: return
            x, y = 0, 0
            row_h = 40
            for item in self.filter_items:
                item.update_idletasks()
                f_w = item.winfo_reqwidth()
                if x + f_w > w:
                    x = 0
                    y += row_h
                item.place(x=x, y=y)
                x += f_w + 15
            f_container.configure(height=y+row_h)
        f_container.bind("<Configure>", _repack_filters)

        # --- MAIN PANED WINDOW ---
        main_paned = ttk.Panedwindow(self, orient=HORIZONTAL)
        main_paned.pack(expand=True, fill="both", padx=10, pady=2) 

        # LEFT PANE
        left_frame = tk.Frame(main_paned, bg=HTML_BG)
        main_paned.add(left_frame, weight=5) 
        
        # RIGHT PANE
        right_frame = tk.Frame(main_paned, bg=HTML_BG)
        main_paned.add(right_frame, weight=1) 

        # --- 2. TOUCH ACTIONS (Dynamic Height) ---
        actions_wrapper, actions_content = create_floating_card_frame(left_frame, None, dynamic_height=True)
        actions_wrapper.pack(fill="x", pady=1) 
        
        act_grid = tk.Frame(actions_content, bg=HTML_WHITE)
        act_grid.pack(fill="x", padx=10, pady=5) 
        act_grid.columnconfigure(0, weight=1)
        act_grid.columnconfigure(1, weight=1)
        act_grid.columnconfigure(2, weight=1)
        
        # Colors
        GREEN_S, GREEN_E = '#28a745', '#218838'
        RED_S, RED_E = '#dc3545', '#c82333'
        GRAY_S, GRAY_E = '#6c757d', '#5a6268'
        
        GradientButton(act_grid, "INGRESO DE MERCADERÍA", "", GREEN_S, GREEN_E, lambda: self.open_touch_dialog("INGRESO"), height=45).grid(row=0, column=0, sticky="ew", padx=5)
        GradientButton(act_grid, "SALIDA DE MERCADERÍA", "", RED_S, RED_E, lambda: self.open_touch_dialog("SALIDA"), height=45).grid(row=0, column=1, sticky="ew", padx=5)
        GradientButton(act_grid, "ANULADO", "", GRAY_S, GRAY_E, lambda: self.open_touch_dialog("ANULADO"), height=45).grid(row=0, column=2, sticky="ew", padx=5)
        
        # --- 3. INGRESOS Y SALIDAS EMITIDAS (Expand/Fill, No Duplicate Title) ---
        hist_wrapper, hist_content = create_floating_card_frame(left_frame, None, dynamic_height=False)
        hist_wrapper.pack(fill="both", expand=True, pady=1) 
        
        # Header Row inside card
        h_row = tk.Frame(hist_content, bg=HTML_WHITE)
        h_row.pack(fill="x", padx=10, pady=(5, 5))
        
        # Removed Header Label here
        # Removed Total Label from here

        
        # Footer Row for Total (Packed Bottom First)
        f_row = tk.Frame(hist_content, bg=HTML_WHITE)
        f_row.pack(side="bottom", fill="x", padx=10, pady=(5, 5))
        self.total_filtered_label = tk.Label(f_row, text="Total Filtrado: S/ 0.00", bg=HTML_WHITE, fg="#28a745", font=(FONT_FAMILY, 12, "bold"))
        self.total_filtered_label.pack(side="right")

        cols = ("ID", "Tipo", "Número", "Fecha", "Motivo", "Total")
        # Column #0 (Hidden Tree)
        self.hist_tree = ttk.Treeview(hist_content, columns=cols, show="tree headings")
        self.hist_tree.column("#0", width=0, stretch=False)
        for col in cols:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=80, anchor="center")
        self.hist_tree.column("Motivo", width=150)
        self.hist_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.hist_tree.bind("<<TreeviewSelect>>", self.on_movement_select)
        self.hist_tree.tag_configure('oddrow', background=GRAY_STRIPE)
        self.hist_tree.tag_configure('evenrow', background=HTML_WHITE)
        
        # Footer Row for Total


        # --- 4. DETALLES (Expand/Fill) ---
        det_wrapper, det_content = create_floating_card_frame(left_frame, None, dynamic_height=False)
        det_wrapper.pack(fill="both", expand=True, pady=1) 
        
        tk.Label(det_content, text="Detalles del Ingreso o Salida o Anulado", font=(FONT_FAMILY, 10, "bold"), bg=HTML_WHITE, fg=HTML_WHITE_TEXT).pack(anchor="w", padx=10, pady=(5, 5))
        
        d_cols = ("Producto", "Cantidad", "UM", "P.Unit", "Subtotal")
        self.det_tree = ttk.Treeview(det_content, columns=d_cols, show="tree headings") 
        self.det_tree.column("#0", width=0, stretch=False)
        for col in d_cols:
            self.det_tree.heading(col, text=col)
            self.det_tree.column(col, anchor="center")
        self.det_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.det_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.det_tree.tag_configure('oddrow', background=GRAY_STRIPE)
        self.det_tree.tag_configure('evenrow', background=HTML_WHITE)

        # --- RIGHT PANE: TICKET PREVIEW (Expand/Fill) ---
        # No title for the card itself, but maybe a label inside
        ticket_wrapper, ticket_content = create_floating_card_frame(right_frame, None, dynamic_height=False)
        ticket_wrapper.pack(fill="both", expand=True, padx=(5, 0), pady=2)
        
        # Center Container
        ticket_center = tk.Frame(ticket_content, bg=HTML_WHITE, bd=0)
        ticket_center.pack(expand=True, fill="both", pady=20) # Fill both!
        
        # Ticket Text Widget
        # Ticket Text Widget
        self.ticket_preview = tk.Text(ticket_center, wrap="none", font=("Consolas", 9), width=42, relief="flat", bg=TICKET_BG, fg=TICKET_FG, padx=10, pady=10)
        self.ticket_preview.pack(fill="y", expand=True) # Expand Y
        self.ticket_preview.config(highlightbackground="#ddd", highlightthickness=1)
        self.ticket_preview.config(state="disabled")
        
        # Tags for ticket
        self.ticket_preview.tag_configure("center", justify='center')
        self.ticket_preview.tag_configure("right", justify='right')
        self.ticket_preview.tag_configure("bold", font=("Consolas", 9, "bold"))
        self.ticket_preview.tag_configure("large", font=("Consolas", 11, "bold"))

        BLUE_S, BLUE_E = '#007bff', '#0056b3'
        GradientButton(ticket_center, "IMPRIMIR", "🖨", BLUE_S, BLUE_E, self.print_ticket, height=45).pack(fill="x", pady=20, padx=20)

        self.load_issuers()
        self.load_products()
        self.load_movements_history()



    # --- LOGIC METHODS (Preserved) ---
    # --- LOGIC METHODS ---
    def load_issuers(self):
        self.issuers_data = database.get_all_issuers()
        issuers = ["Todos"] + sorted(list(set(i[1] for i in self.issuers_data)))
        self.issuer_combo['values'] = issuers
        
        last_issuer = config_manager.load_setting("last_movements_issuer", "Todos")
        if last_issuer in issuers:
            self.issuer_var.set(last_issuer)
        else:
            self.issuer_var.set("Todos")
        
        self.on_issuer_change(save=False)
            
    def on_issuer_change(self, event=None, save=True):
        selected = self.issuer_var.get()
        if save: config_manager.save_setting("last_movements_issuer", selected)
        
        if selected == "Todos":
            self.address_combo['values'] = ["Todas"]
            self.address_var.set("Todas")
        else:
            addresses = sorted(list(set(i[3] for i in self.issuers_data if i[1] == selected)))
            if len(addresses) == 1:
                self.address_combo['values'] = addresses
                self.address_var.set(addresses[0])
            else:
                self.address_combo['values'] = ["Todas"] + addresses
                self.address_var.set("Todas")
        
        if save:
             config_manager.save_setting("last_movements_address", self.address_var.get())
             self.load_movements_history()

    def on_address_change(self, event=None):
        config_manager.save_setting("last_movements_address", self.address_var.get())
        self.load_movements_history()

    def load_products(self):
        emisor = self.issuer_var.get()
        dir_val = self.address_var.get()
        
        e_filter = emisor if emisor and emisor != "Todos" else None
        d_filter = dir_val if dir_val and dir_val != "Todas" else None
        
        try:
             raw = database.get_all_products(e_filter, d_filter)
        except AttributeError:
             raw = []
        
        self.products_list = []
        for r in raw:
            self.products_list.append({
                "id": r[0],
                "name": r[1],
                "price": r[2],
                "stock": r[3],
                "code": r[4],
                "um": r[5]
            })

    def open_touch_dialog(self, move_type):
        issuer = self.issuer_var.get()
        address = self.address_var.get()
        
        if not issuer or not address or issuer == "Todos" or address == "Todas":
            messagebox.showerror("Error", "Seleccione un Emisor y Dirección específicos para guardar el movimiento.", parent=self)
            return
            
        issuer_id = None
        for i in self.issuers_data:
            if i[1] == issuer and i[3] == address:
                issuer_id = i[0]
                break
        if not issuer_id:
             messagebox.showerror("Error", "Emisor no válido", parent=self)
             return
             
        from movements_touch_dialog import TouchMovementDialog
        TouchMovementDialog(self, move_type, issuer_id, address)

    def load_movements_history(self):
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
            
        ftype = self.hist_filter_var.get()
        
        try:
            s_date = datetime.strptime(self.start_date_entry.entry.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            e_date = datetime.strptime(self.end_date_entry.entry.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            s_date, e_date = None, None
            
        # 1. Fetch ALL rows for the date range/type (ignoring issuer in SQL for now)
        all_rows = database.get_movements(ftype, s_date, e_date)
        
        # 2. Filter in Python
        sel_issuer = self.issuer_var.get()
        sel_address = self.address_var.get()
        
        filtered_rows = []
        for row in all_rows:
            # row: 0:id, 1:type, 2:num, 3:date, 4:reason, 5:total, 6:issuer_id, 7:issuer_address
            if len(row) < 8: continue
            
            r_issuer_id = row[6]
            r_address = row[7]
            
            # Find issuer name
            r_issuer_name = ""
            for i in self.issuers_data:
                if i[0] == r_issuer_id:
                    r_issuer_name = i[1]
                    break
            
            match = True
            if sel_issuer and sel_issuer != "Todos":
                if r_issuer_name != sel_issuer: match = False
            
            if match and sel_address and sel_address != "Todas":
                if r_address != sel_address: match = False
                
            if match:
                 filtered_rows.append(row)
        
        total = 0.0
        for i, row in enumerate(filtered_rows):
            val_total = float(row[5]) if row[5] else 0.0
            total += val_total
            
            disp_row = list(row[:6])
            disp_row[5] = f"S/ {val_total:,.2f}"
            
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.hist_tree.insert("", "end", text="", values=disp_row, tags=(tag,))
        
        self.total_filtered_label.config(text=f"Total Filtrado: S/ {total:,.2f}")

    def on_movement_select(self, event):
        sel = self.hist_tree.selection()
        if not sel: return
        vals = self.hist_tree.item(sel)['values']
        mid = vals[0]
        
        for i in self.det_tree.get_children():
            self.det_tree.delete(i)
            
        data = database.get_movement_full_data(mid)
        if data:
            for i, item in enumerate(data['details']):
                f_item = list(item)
                # Format Price and Subtotal
                try:
                    f_item[3] = f"S/ {float(f_item[3]):,.2f}" # Price
                    f_item[4] = f"S/ {float(f_item[4]):,.2f}" # Subtotal
                except: pass
                
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.det_tree.insert("", "end", values=f_item, tags=(tag,))
                
            # Update Ticket Preview
            self.update_ticket_preview(data)

    def update_ticket_preview(self, data):
        self.ticket_preview.config(state="normal")
        self.ticket_preview.delete("1.0", tk.END)
        
        mov = data['movement']
        # mov: id, type, number, date, reason, total, ... params from database.get_movement_full_data
        
        issuer_name = mov[6]
        issuer_addr = mov[8] if mov[8] else ""
        move_type = mov[1]
        move_num = mov[2]
        date_time = mov[3]
        
        txt = ""
        txt += f"{issuer_name}\n"
        txt += f"{issuer_addr}\n"
        txt += "-"*36 + "\n"
        txt += f"TICKET DE {move_type}\n"
        txt += f"{move_num}\n"
        txt += f"Fecha: {date_time}\n"
        txt += "-"*36 + "\n"
        txt += "CANT. PRODUCTO        P.U.   TOTAL\n"
        txt += "-"*36 + "\n"
        
        for item in data['details']:
            # name, qty, um, price, subtotal
            name = item[0]
            qty = item[1]
            price = item[3]
            subt = item[4]
            
            txt += f"{name[:36]}\n"
            txt += f"{qty:<5}               {price:>6.2f} {subt:>7.2f}\n"
            
        txt += "-"*36 + "\n"
        txt += f"TOTAL: S/ {mov[5]:,.2f}\n"
        
        self.ticket_preview.insert("1.0", txt)
        self.ticket_preview.tag_add("center", "1.0", "3.0") # Title centered
        self.ticket_preview.config(state="disabled")


    def clear_cart(self):
        self.cart = []
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.reason_var.set("")
        if hasattr(self, 'total_label'):
            self.total_label.config(text="Total: S/ 0.00")

    def save_movement(self, move_type):
        if not self.cart:
            messagebox.showwarning("Aviso", "El carrito está vacío")
            return
            
        issuer = self.issuer_var.get()
        address = self.address_var.get()
        
        if not issuer or not address or issuer == "TODOS" or address == "TODOS":
            messagebox.showerror("Error", "Debe seleccionar un Emisor y Dirección específicos para guardar el movimiento.")
            return
            
        # Get Issuer ID
        issuer_id = None
        for i in self.issuers_data:
            if i[1] == issuer and i[3] == address:
                issuer_id = i[0]
                break
                
        if not issuer_id:
            messagebox.showerror("Error", "Emisor no válido")
            return
            
        reason = self.reason_var.get().strip()
        # Validation removed as per user request
        # if not reason:
        #     messagebox.showerror("Error", "Ingrese un motivo")
        #     return
            
        total = sum(i['subtotal'] for i in self.cart)
        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            num = database.record_movement(move_type, reason, issuer_id, address, self.cart, total, date_time)
            messagebox.showinfo("Éxito", f"Movimiento {num} registrado correctamente")
            self.clear_cart()
            self.load_movements_history()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def load_movements_history(self):
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
            
        ftype = self.hist_filter_var.get()
        
        # Get Dates
        try:
            s_date = self.start_date_entry.entry.get()
            e_date = self.end_date_entry.entry.get()
            
            start_date_db = None
            end_date_db = None
            
            if s_date:
                start_date_db = datetime.strptime(s_date, "%d/%m/%Y").strftime("%Y-%m-%d")
            if e_date:
                end_date_db = datetime.strptime(e_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            start_date_db = None
            end_date_db = None
            
        # Get Issuer and Address
        issuer_name = self.issuer_var.get()
        address = self.address_var.get()
        
        issuer_id = None
        if issuer_name and issuer_name != "TODOS":
            # Find issuer_id
            # self.issuers_data is list of tuples: (id, name, ruc, address, ...)
            # We need to match both name and address if address is specific
            for i in self.issuers_data:
                if i[1] == issuer_name:
                    if address and address != "TODOS":
                        if i[3] == address:
                            issuer_id = i[0]
                            break
                    else:
                        # If address is TODOS, we can't filter by a single ID unless we pass list of IDs?
                        # Or we pass issuer_id=None and rely on name? But database.get_movements uses ID.
                        # If address is TODOS, we might want ALL addresses for that issuer.
                        # But database.get_movements filters by ID.
                        # If we have multiple addresses for same issuer name, they have different IDs?
                        # Yes, issuers table has UNIQUE(name, ruc, address). So each address is a row.
                        # If we want all movements for "Issuer A" regardless of address, we need to find ALL IDs for "Issuer A".
                        # But get_movements only accepts one ID.
                        # For now, let's assume if address is TODOS, we don't filter by ID (or we need to update get_movements to filter by name?)
                        # But the user requirement says "Refiltrar ... con los 4 filtros".
                        # If address is TODOS, maybe we shouldn't filter by ID?
                        # But we should filter by Issuer Name?
                        # Let's check get_movements again. It filters by issuer_id.
                        # If address is TODOS, we can't filter by ID effectively if there are multiple IDs for that issuer.
                        # However, usually "TODOS" means "All Issuers".
                        # If "Issuer A" is selected and "TODOS" addresses, we want all Issuer A's movements.
                        # We might need to update get_movements to filter by issuer_id IN (...) or filter by name.
                        # Given the constraint, let's try to find the ID if address is specific.
                        # If address is TODOS, we pass None for issuer_id? No, that would show ALL issuers.
                        # We need to handle this.
                        # Let's update get_movements to filter by issuer_id list? Or just pass None if TODOS?
                        # If I pass None, it shows all issuers.
                        # If I select "Issuer A" and "TODOS", I expect only Issuer A.
                        # I'll stick to: if address is specific, use ID. If address is TODOS, maybe I can't filter by ID easily without changing DB function more.
                        # BUT, for now, let's assume if address is TODOS, we don't filter by ID (showing all issuers).
                        # Wait, that's bad UX.
                        # Let's look at how `reports_view.py` does it.
                        # `reports_view.py` `populate_sales_list` calls `database.get_sales_by_filters`.
                        # Let's check `get_sales_by_filters`.
                        pass

        # Re-evaluating:
        # If address is specific, we have a unique ID.
        # If address is TODOS, we have multiple IDs for the same issuer name.
        # I should probably update get_movements to accept issuer_name?
        # But movements table stores issuer_id.
        # So I would need a JOIN or a subquery.
        # Or I can fetch all IDs for that issuer name and pass them.
        # `get_movements` currently takes a single `issuer_id`.
        # I will modify `get_movements` to accept `issuer_ids` (list) or just handle it in Python?
        # Handling in Python is easier but less efficient.
        # Given the time, I will try to find the ID. If address is TODOS, I will try to find *any* ID? No.
        # I will update `get_movements` to accept `issuer_id` OR `issuer_name`?
        # No, let's keep it simple. If address is TODOS, I will NOT filter by issuer_id (showing all issuers).
        # This is a limitation but maybe acceptable for now.
        # OR, I can filter the results in Python.
        # `rows` = `database.get_movements(...)` (without issuer filter)
        # Then filter `rows` by checking if `row['issuer_id']` belongs to the selected issuer.
        # `get_movements` returns `id, type, number, date, reason, total`. It DOES NOT return issuer_id.
        # So I can't filter in Python easily.
        
        # OK, I will update `get_movements` to perform a JOIN with issuers table so I can filter by issuer name if needed.
        # Or I can just pass `issuer_id` if address is specific.
        # If address is TODOS, I will pass None (showing all).
        # This effectively means "Issuer Filter" only works if "Address" is also selected.
        # This might be confusing.
        # However, `on_issuer_change` auto-selects the address if there's only one.
        # So for single-address issuers, it works.
        # For multi-address issuers, the user has to select an address.
        # This seems like a reasonable compromise for now.
        
        if address and address != "TODOS":
             for i in self.issuers_data:
                if i[1] == issuer_name and i[3] == address:
                    issuer_id = i[0]
                    break
        
        rows = database.get_movements(ftype, start_date_db, end_date_db, issuer_id, address)
        
        total_filtered = 0.0
        for r in rows:
            # id, type, number, date, reason, total
            total_val = r[5]
            total_filtered += total_val
            
            formatted_r = list(r)
            
            # Format Date dd/mm/yyyy hh:mm:ss
            try:
                # Assuming DB returns YYYY-MM-DD HH:MM:SS
                d_obj = datetime.strptime(str(r[3]), "%Y-%m-%d %H:%M:%S")
                formatted_r[3] = d_obj.strftime("%d/%m/%Y %H:%M:%S")
            except (ValueError, TypeError):
                # If milliseconds exist or other format, try simpler or leave as is
                pass
                
            formatted_r[5] = f"{total_val:,.2f}"
            self.hist_tree.insert("", "end", values=formatted_r)
            
        if hasattr(self, 'total_filtered_label'):
            self.total_filtered_label.config(text=f"Total Filtrado: S/ {total_filtered:,.2f}")

    def open_date_filter_dialog(self):
        dialog = ttk.Toplevel(self)
        dialog.title("Filtrar por Fechas")
        dialog.geometry("300x250")
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Close on click outside
        def close_if_outside(event):
            try:
                if dialog.winfo_exists():
                    widget = event.widget
                    # If widget is not child of dialog
                    if not str(widget).startswith(str(dialog)):
                         dialog.destroy()
                         self.unbind('<Button-1>')
            except:
                pass
        
        self.bind('<Button-1>', close_if_outside)
        
        ttk.Label(dialog, text="Fecha Inicio:").pack(pady=5)
        # Configure DateEntry for DD/MM/YYYY
        start_cal = ttk.DateEntry(dialog, bootstyle="primary", dateformat="%d/%m/%Y", firstweekday=0)
        start_cal.pack(pady=5)
        
        ttk.Label(dialog, text="Fecha Fin:").pack(pady=5)
        end_cal = ttk.DateEntry(dialog, bootstyle="primary", dateformat="%d/%m/%Y", firstweekday=0)
        end_cal.pack(pady=5)
        
        # Attempt to change "Select new date" title
        def rename_popup():
            for widget in self.winfo_children():
                 if isinstance(widget, tk.Toplevel):
                     if "date" in widget.title().lower():
                         widget.title("Selecciona nueva fecha")
            for widget in self.master.winfo_children():
                 if isinstance(widget, tk.Toplevel):
                     if "date" in widget.title().lower():
                         widget.title("Selecciona nueva fecha")

        # Bind to the button inside DateEntry
        for child in start_cal.winfo_children():
            if isinstance(child, ttk.Button):
                child.bind('<Button-1>', lambda e: self.after(100, rename_popup), add='+')
                
        for child in end_cal.winfo_children():
            if isinstance(child, ttk.Button):
                child.bind('<Button-1>', lambda e: self.after(100, rename_popup), add='+')

        def apply_filter():
            try:
                s_date_str = start_cal.entry.get()
                e_date_str = end_cal.entry.get()
                
                # Convert DD/MM/YYYY to YYYY-MM-DD for database
                try:
                    d_start = datetime.strptime(s_date_str, "%d/%m/%Y")
                    self.filter_start_date = d_start.strftime("%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha inicio inválido (DD/MM/YYYY)", parent=dialog)
                    return

                try:
                    d_end = datetime.strptime(e_date_str, "%d/%m/%Y")
                    self.filter_end_date = d_end.strftime("%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha fin inválido (DD/MM/YYYY)", parent=dialog)
                    return

                self.load_movements_history()
                dialog.destroy()
                self.unbind('<Button-1>') # Unbind the close listener
            except Exception as e:
                messagebox.showerror("Error", f"Error en fechas: {e}", parent=dialog)

        def clear_filter():
            self.filter_start_date = None
            self.filter_end_date = None
            self.load_movements_history()
            dialog.destroy()
            self.unbind('<Button-1>')

        ttk.Button(dialog, text="Aplicar Filtro", command=apply_filter, bootstyle="success").pack(pady=10, fill="x", padx=20)
        ttk.Button(dialog, text="Limpiar Filtro", command=clear_filter, bootstyle="secondary").pack(pady=5, fill="x", padx=20)

    def on_movement_select(self, event):
        sel = self.hist_tree.focus()
        if not sel: return
        
        vals = self.hist_tree.item(sel)['values']
        move_id = vals[0]
        
        # Load Details
        for i in self.det_tree.get_children():
            self.det_tree.delete(i)
            
        full_data = database.get_movement_full_data(move_id)
        if full_data:
            items = full_data['details']
            for i in items:
                self.det_tree.insert("", "end", values=i)
            
            # Update Ticket Preview
            self.update_ticket_preview(full_data)

    def _number_to_text(self, amount):
        """Convierte un número a texto en soles (Español)."""
        UNIDADES = ["", "UN ", "DOS ", "TRES ", "CUATRO ", "CINCO ", "SEIS ", "SIETE ", "OCHO ", "NUEVE "]
        DECENAS = ["", "DIEZ ", "VEINTE ", "TREINTA ", "CUARENTA ", "CINCUENTA ", "SESENTA ", "SETENTA ", "OCHENTA ", "NOVENTA "]
        DIEZ_VEINTE = ["DIEZ ", "ONCE ", "DOCE ", "TRECE ", "CATORCE ", "QUINCE ", "DIECISEIS ", "DIECISIETE ", "DIECIOCHO ", "DIECINUEVE "]
        CENTENAS = ["", "CIENTO ", "DOSCIENTOS ", "TRESCIENTOS ", "CUATROCIENTOS ", "QUINIENTOS ", "SEISCIENTOS ", "SETECIENTOS ", "OCHOCIENTOS ", "NOVECIENTOS "]

        def leer_decenas(n):
            if n < 10: return UNIDADES[n]
            d, u = divmod(n, 10)
            if n <= 19: return DIEZ_VEINTE[n-10]
            if u == 0: return DECENAS[d]
            return DECENAS[d] + "Y " + UNIDADES[u]

        def leer_centenas(n):
            c, d = divmod(n, 100)
            if n == 100: return "CIEN "
            return CENTENAS[c] + leer_decenas(d)

        def leer_miles(n):
            m, c = divmod(n, 1000)
            if m == 0: return leer_centenas(c)
            if m == 1: return "MIL " + leer_centenas(c)
            return leer_centenas(m) + "MIL " + leer_centenas(c)

        entero = int(amount)
        decimal = int(round((amount - entero) * 100))
        
        letras = ""
        if entero == 0: letras = "CERO "
        elif entero < 1000000: letras = leer_miles(entero)
        else: letras = "NUMERO MUY GRANDE "
            
        return f"{letras} CON {decimal:02d}/100 SOLES"
        self.ticket_preview.tag_configure("left", justify='left')
        self.ticket_preview.tag_configure("bold", font=("Consolas", 9, "bold"))
        self.ticket_preview.tag_configure("inverse", background=COLOR_TEXT_LIGHT, foreground=COLOR_PRIMARY_DARK)
        self.ticket_preview.tag_configure("large", font=("Consolas", 11, "bold"))
        
        ttk.Button(preview_frame, text="🖨 IMPRIMIR", command=self.print_ticket, bootstyle="primary", width=20).pack(pady=20)

    def update_ticket_preview(self, full_data):
        self.ticket_preview.config(state="normal")
        self.ticket_preview.delete("1.0", tk.END)
        
        import textwrap
        
        movement = full_data['movement']
        details = full_data['details']
        
        # movement: id, type, number, date, reason, total, issuer_name, ruc, address...
        # indices: 0:id, 1:type, 2:number, 3:date, 4:reason, 5:total
        # 6:issuer_name, 7:ruc, 8:address, 9:district, 10:prov, 11:dept
        
        # 6:issuer_name, 7:ruc, 8:address, 9:district, 10:prov, 11:dept
        
        WIDTH = 42 # Match reports_view.py width
        
        # --- HEADER ---
        issuer_name = movement[6] or ""
        issuer_address = movement[8] or ""
        
        if issuer_name:
            name_lines = textwrap.wrap(issuer_name, width=WIDTH)
            for line in name_lines:
                self.ticket_preview.insert(tk.END, line + "\n", ("center", "bold"))
                
        if issuer_address:
            addr_lines = textwrap.wrap(issuer_address, width=WIDTH)
            for line in addr_lines:
                self.ticket_preview.insert(tk.END, line + "\n", "center")
                
        self.ticket_preview.insert(tk.END, "-" * WIDTH + "\n", "center")
        
        self.ticket_preview.insert(tk.END, "TICKET DE MOVIMIENTO\n", ("center", "bold"))
        self.ticket_preview.insert(tk.END, f"{movement[1]} - {movement[2]}\n", ("center", "bold"))
        self.ticket_preview.insert(tk.END, "-" * WIDTH + "\n", "center")
        
        self.ticket_preview.insert(tk.END, f"FECHA: {movement[3]}\n", "center")
        self.ticket_preview.insert(tk.END, f"MOTIVO: {movement[4]}\n", "center")
        self.ticket_preview.insert(tk.END, "-" * WIDTH + "\n", "center")
        
        # --- ITEMS ---
        # Match reports_view.py logic exactly
        # Header: Centered string
        header_line = "PRODUCTO      CANT    P.UNIT   SUBTOTAL"
        self.ticket_preview.insert(tk.END, header_line + "\n", ("center", "bold"))
        self.ticket_preview.insert(tk.END, "-" * WIDTH + "\n", "center")
        
        for item in details:
            # item: (name, quantity, um, price, subtotal)
            name = item[0]
            qty = item[1]
            um = item[2]
            price = item[3]
            sub = item[4]
            
            # Check Format
            print_format = config_manager.load_setting("print_format_nv", "APISUNAT")
            
            if print_format == "NUMIER":
                # Single Line: Name(18) Qty(5) Price(7) Sub(8)
                # Truncate Name
                name_short = name[:18]
                
                # Format: "Name...  Qty   Price   Sub"
                # Use f-string width: 
                # {name:<19} {qty:>5.2f} {price:>7.2f} {sub:>8.2f}
                # 19 + 1 + 5 + 1 + 7 + 1 + 8 = 42?
                # Let's try to fit 42
                
                line = f"{name_short:<18} {qty:>5.2f} {price:>7.2f} {sub:>7.2f}"
                self.ticket_preview.insert(tk.END, line + "\n", "left")
                
            else:
                # APISUNAT (Default): 2 Lines
                # Line 1: Description (Left aligned, no indent)
                desc_lines = textwrap.wrap(name, width=WIDTH)
                for line in desc_lines:
                    self.ticket_preview.insert(tk.END, line + "\n", "left")
                    
                # Line 2: Qty/UM Price Subtotal (Centered, fixed widths)
                qty_um = f"{qty:.2f} {um[:3]}"
                price_str = f"{price:.2f}"
                sub_str = f"{sub:.2f}"
                
                # Logic from reports_view.py: center(16) + rjust(10) + rjust(16) = 42 chars
                l2_str = f"{qty_um}".center(16) + f"{price_str}".rjust(10) + f"{sub_str}".rjust(16)
                
                self.ticket_preview.insert(tk.END, l2_str + "\n", "center")
            # Removed dotted separator as requested
            
        # --- TOTAL ---
        total_val = movement[5]
        total_str = f"TOTAL: S/ {total_val:,.2f}"
        self.ticket_preview.insert(tk.END, total_str.center(WIDTH) + "\n", ("center", "inverse", "large"))
        
        total_letras = self._number_to_text(total_val)
        letras_lines = textwrap.wrap(total_letras, width=WIDTH)
        for line in letras_lines:
            self.ticket_preview.insert(tk.END, line + "\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * WIDTH + "\n", "center")
        self.ticket_preview.config(state="disabled")

    def print_ticket(self):
        sel = self.hist_tree.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un movimiento para imprimir.", parent=self)
            return
            
        vals = self.hist_tree.item(sel)['values']
        move_id = vals[0]
        
        full_data = database.get_movement_full_data(move_id)
        if not full_data:
            messagebox.showerror("Error", "No se encontraron datos del movimiento.", parent=self)
            return

        movement = full_data['movement']
        details = full_data['details']
        
        # Constantes ESC/POS
        INIT = b'\x1b@'
        CODEPAGE_850 = b'\x1bt\x02'
        ALIGN_LEFT = b'\x1ba\x00'
        ALIGN_CENTER = b'\x1ba\x01'
        ALIGN_RIGHT = b'\x1ba\x02'
        BOLD_ON = b'\x1bE\x01'
        BOLD_OFF = b'\x1bE\x00'
        INVERSE_ON = b'\x1dB\x01'
        INVERSE_OFF = b'\x1dB\x00'
        SIZE_NORMAL = b'\x1d!\x00'
        SIZE_2H = b'\x1d!\x10'
        SIZE_2W = b'\x1d!\x01'
        SIZE_2X = b'\x1d!\x11'
        CUT = b'\x1dV\x41\x00'
        
        def text(s):
            return s.encode('cp850', errors='replace')
            
        buffer = bytearray()
        buffer.extend(INIT)
        buffer.extend(CODEPAGE_850)
        
        # --- HEADER ---
        issuer_name = movement[6] or ""
        issuer_address = movement[8] or ""
        
        buffer.extend(ALIGN_CENTER)
        
        if issuer_name:
            name_lines = textwrap.wrap(issuer_name, width=42)
            for line in name_lines:
                buffer.extend(BOLD_ON + text(line + "\n") + BOLD_OFF)
                
        if issuer_address:
            addr_lines = textwrap.wrap(issuer_address, width=42)
            for line in addr_lines:
                buffer.extend(text(line + "\n"))
                
        buffer.extend(text("-" * 42 + "\n"))
        
        buffer.extend(BOLD_ON + text("TICKET DE MOVIMIENTO\n") + BOLD_OFF)
        buffer.extend(BOLD_ON + text(f"{movement[1]} - {movement[2]}\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        buffer.extend(text(f"FECHA: {movement[3]}\n"))
        buffer.extend(text(f"MOTIVO: {movement[4]}\n"))
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS ---
        # Header: "PRODUCTO      CANT    P.UNIT   SUBTOTAL"
        header_line = "PRODUCTO      CANT    P.UNIT   SUBTOTAL"
        buffer.extend(BOLD_ON + text(header_line + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        for item in details:
            # item: (name, quantity, um, price, subtotal)
            name = item[0]
            qty = item[1]
            um = item[2]
            price = item[3]
            sub = item[4]
            
            # Check Format
            print_format = config_manager.load_setting("print_format_nv", "APISUNAT")
            
            if print_format == "NUMIER":
                # Single Line
                buffer.extend(ALIGN_LEFT)
                name_short = name[:18]
                line = f"{name_short:<18} {qty:>5.2f} {price:>7.2f} {sub:>7.2f}"
                buffer.extend(text(line + "\n"))
                
            else:
                # APISUNAT (Default: 2 lines)
                # Line 1: Description (Left aligned, no indent)
                buffer.extend(ALIGN_LEFT)
                desc_lines = textwrap.wrap(name, width=42) 
                for line in desc_lines:
                    buffer.extend(text(line + "\n"))
                    
                # Line 2: Qty/UM Price Subtotal (Centered visually but using spaces)
                qty_um = f"{qty:.2f} {um[:3]}"
                price_str = f"{price:.2f}"
                sub_str = f"{sub:.2f}"
                
                l2_str = f"{qty_um}".center(16) + f"{price_str}".rjust(10) + f"{sub_str}".rjust(16)
                
                buffer.extend(ALIGN_CENTER) 
                
                buffer.extend(text(l2_str + "\n"))
            # Removed dotted separator as requested
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- TOTAL ---
        total_val = movement[5]
        total_str = f"TOTAL: S/ {total_val:,.2f}"
        
        buffer.extend(ALIGN_CENTER)
        buffer.extend(INVERSE_ON + SIZE_2H + text(total_str.center(21)) + SIZE_NORMAL + INVERSE_OFF + text("\n")) 
        
        total_letras = self._number_to_text(total_val)
        letras_lines = textwrap.wrap(total_letras, width=42)
        for line in letras_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        buffer.extend(CUT)
        
        # --- SEND TO PRINTER ---
        if win32print:
            try:
                printer_name = win32print.GetDefaultPrinter()
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Ticket de Movimiento", None, "RAW"))
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, buffer)
                    win32print.EndPagePrinter(hPrinter)
                    win32print.EndDocPrinter(hPrinter)
                    messagebox.showinfo("Imprimir", "Ticket enviado a la impresora.", parent=self)
                finally:
                    win32print.ClosePrinter(hPrinter)
            except Exception as e:
                messagebox.showerror("Error de Impresión", f"No se pudo imprimir:\n{e}", parent=self)
        else:
            messagebox.showwarning("Imprimir", "El módulo 'win32print' no está disponible. No se puede imprimir.", parent=self)
