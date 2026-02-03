import tkinter as tk
import custom_messagebox as messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
import database
import config_manager
import json
import io
from PIL import Image, ImageTk, ImageDraw
import qrcode
from datetime import datetime
try:
    import win32print
except ImportError:
    win32print = None
import xml_generator
import os
import re

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HEADER

COLOR_PRIMARY_DARK = COLOR_PRIMARY
COLOR_SECONDARY_DARK = COLOR_SECONDARY
COLOR_ACCENT_BLUE = COLOR_ACCENT
COLOR_TEXT_LIGHT = COLOR_TEXT
COLOR_TEXT_DARK = "#333333"

class GradientFrame(tk.Canvas):
    def __init__(self, parent, color1, color2, text="", text_color="white", shadow_color=None, font_size=20, anchor="center", **kwargs):
        super().__init__(parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self._text = text
        self._text_color = text_color
        self._shadow_color = shadow_color
        self._font_size = font_size
        self._anchor = anchor
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
            
            if self._anchor == "w":
                x = 20 # Padding left
            else:
                x = width // 2
                
            if self._shadow_color:
                self.create_text(x+2, y+2, text=self._text, fill=self._shadow_color, font=font, anchor=self._anchor, tags=("text",))
            self.create_text(x, y, text=self._text, fill=self._text_color, font=font, anchor=self._anchor, tags=("text",))

class ReportsView(ttk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Reporte de Ventas")
        self.configure(background=COLOR_PRIMARY_DARK)
        self.state('zoomed')

        # Estilos
        style = ttk.Style.get_instance()
        style.configure('TLabel', font=(FONT_FAMILY, FONT_SIZE_NORMAL), foreground=COLOR_TEXT_LIGHT, background=COLOR_PRIMARY_DARK)
        style.configure('Treeview', background="white", fieldbackground="white", foreground="black", bordercolor="#dddddd")
        style.map('Treeview', background=[('selected', COLOR_ACCENT_BLUE)], foreground=[('selected', 'white')])
        # Header Color #0a2240 as requested
        style.configure('Treeview.Heading', font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), background="#0a2240", foreground="white")
        style.configure('TLabelframe', background=COLOR_SECONDARY_DARK, foreground=COLOR_TEXT_LIGHT, bordercolor=COLOR_ACCENT_BLUE)
        # Create green check icon (Centered in 60px width)
        width = 60
        height = 16
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw a checkmark centered
        # Original points for 16x16: [(3, 8), (6, 11), (13, 4)]
        # Shift x by (60-16)/2 = 22
        shift_x = 22
        points = [(3 + shift_x, 8), (6 + shift_x, 11), (13 + shift_x, 4)]
        draw.line(points, fill='#00FF00', width=2)
        self.status_icon = ImageTk.PhotoImage(img)

        # Yellow Circle (Pending)
        img_pending = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(img_pending)
        offset_x = (width - 12) // 2
        draw_p.ellipse((offset_x, 2, offset_x+12, 14), fill='#FFC107', outline='#FFC107')
        self.status_icon_pending = ImageTk.PhotoImage(img_pending)
        
        # Red X (Rejected)
        img_rejected = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw_r = ImageDraw.Draw(img_rejected)
        offset_x = (width - 12) // 2
        # Draw X
        draw_r.line((offset_x+2, 2, offset_x+10, 14), fill='#DC3545', width=3)
        draw_r.line((offset_x+2, 14, offset_x+10, 2), fill='#DC3545', width=3)
        self.status_icon_rejected = ImageTk.PhotoImage(img_rejected)

        # Tooltip tracking
        self.tooltip = None
        self.last_tooltip_item = None

        # Helper for rounded widgets
        def create_rounded_widget(parent, widget_class, variable=None, width=150, **kwargs):
            container = tk.Canvas(parent, bg="white", height=35, width=width, highlightthickness=0)
            
            style_name = 'Borderless.TEntry'
            
            # Mutable state for border color
            container.border_color = "#cccccc"
            
            # Widget
            if widget_class == ttk.Combobox:
                 widget = widget_class(container, textvariable=variable, state="readonly", width=15, style='Borderless.TCombobox', **kwargs)
            elif widget_class == DateEntry:
                 # DateEntry (ttkbootstrap).
                 widget = widget_class(container, bootstyle="default", width=10, dateformat="%d/%m/%Y", **kwargs)
                 try: 
                     widget.entry.configure(style=style_name)
                 except: pass
            elif widget_class == ttk.Entry:
                 widget = widget_class(container, textvariable=variable, width=20, style=style_name, **kwargs)

            # Draw Rounded Rect
            bg_fill = "white"
            
            def _draw_bg(e=None):
                w = container.winfo_width()
                h = container.winfo_height()
                if w <= 1: return # Not rendered yet

                container.delete("bg")
                img = Image.new("RGBA", (w, h), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                # Rounded pill with outline (uses current container.border_color)
                draw.rounded_rectangle((0, 0, w-1, h-1), radius=15, fill=bg_fill, outline=container.border_color, width=1)
                
                bg = ImageTk.PhotoImage(img)
                container._bg_ref = bg
                container.create_image(0,0, image=bg, anchor="nw", tags="bg")
                container.tag_lower("bg")
                
                container.itemconfigure(win_path, width=w-25)
                
            container.bind("<Configure>", _draw_bg)
            win_path = container.create_window(12, 17, window=widget, anchor="w")

            # Focus Logic (Change Container Border)
            def _on_focus(e):
                container.border_color = "#007bff" # Blue focus
                _draw_bg()

            def _on_unfocus(e):
                container.border_color = "#cccccc" # Gray normal
                _draw_bg()

            # Bind Focus Events
            target = widget.entry if widget_class == DateEntry else widget
            target.bind("<FocusIn>", _on_focus, add="+")
            target.bind("<FocusOut>", _on_unfocus, add="+")
            
            return widget, container

        # Define Styles (Aggressive Border Hiding)
        # Combobox
        style.configure('Borderless.TCombobox', borderwidth=0, relief='flat', arrowsize=15)
        style.map('Borderless.TCombobox', 
                  fieldbackground=[('readonly','white'), ('active', 'white'), ('focus', 'white')], 
                  background=[('readonly','white')], 
                  bordercolor=[('focus', 'white'), ('!disabled', 'white')],
                  lightcolor=[('focus', 'white'), ('!disabled', 'white')],
                  darkcolor=[('focus', 'white'), ('!disabled', 'white')])
        
        # Entry
        style.configure('Borderless.TEntry', fieldbackground='white', borderwidth=0, relief='flat', highlightthickness=0)
        style.map('Borderless.TEntry', 
                  fieldbackground=[('focus','white'), ('!disabled', 'white')],
                  bordercolor=[('focus', 'white'), ('!disabled', 'white')],
                  lightcolor=[('focus', 'white'), ('!disabled', 'white')],
                  darkcolor=[('focus', 'white'), ('!disabled', 'white')])

        # --- Header ---
        # Align left (anchor="w")
        GradientFrame(self, color1="#0a2240", color2="#007bff", text="Ventas Realizadas", height=60, font_size=24, anchor="w").pack(fill="x", side="top")

        # --- Filter Card ---
        card_frame = tk.Frame(self, bg=COLOR_PRIMARY_DARK)
        card_frame.pack(fill="x", padx=10, pady=(5, 0)) # Reduced padding
        
        self.filter_card = tk.Canvas(card_frame, bg=COLOR_PRIMARY_DARK, height=80, highlightthickness=0)
        self.filter_card.pack(fill="x")
        
        # Improved Card Shadow (Material Box Shadow)
        def _draw_card(e):
             self.filter_card.delete("bg")
             w, h = e.width, e.height
             img = Image.new("RGBA", (w, h), (0,0,0,0))
             draw = ImageDraw.Draw(img)
             
             # Soft Shadow (Layered)
             # Key shadow
             draw.rounded_rectangle((3, 5, w-3, h-1), radius=15, fill="#ccd1d9") 
             # Ambient shadow
             draw.rounded_rectangle((2, 2, w-2, h-2), radius=15, fill="#e2e6ea")
             
             # Main Card Body (White)
             draw.rounded_rectangle((0, 0, w-5, h-5), radius=15, fill="white")
             
             bg = ImageTk.PhotoImage(img)
             self.filter_card._bg = bg
             self.filter_card.create_image(0,0, image=bg, anchor="nw", tags="bg")
             self.filter_card.tag_lower("bg")
        # Custom Responsive Layout Manager
        self.filter_items = []
        filter_row = tk.Frame(self.filter_card, bg="white")
        # Store window ID to resize it later
        self.filter_row_window = self.filter_card.create_window(20, 20, window=filter_row, anchor="nw")

        def create_filter_group(label_text, widget_class, var=None, width=150, is_date=False):
            frame = tk.Frame(filter_row, bg="white")
            lbl = tk.Label(frame, text=label_text, bg="white", font=(FONT_FAMILY, 10, "bold"))
            lbl.pack(side="left", padx=(0,5))
            
            if is_date:
                widget, container = create_rounded_widget(frame, widget_class, width=width)
            else:
                widget, container = create_rounded_widget(frame, widget_class, var, width=width)
            container.pack(side="left")
            return frame, widget

        # 1. Emisor
        self.issuer_filter_var = tk.StringVar(value="Todos")
        f1, self.issuer_filter_combo = create_filter_group("Emisor:", ttk.Combobox, self.issuer_filter_var, width=250)
        self.filter_items.append(f1)

        # 2. Dirección
        self.address_filter_var = tk.StringVar(value="Todas")
        f2, self.address_filter_combo = create_filter_group("Dirección:", ttk.Combobox, self.address_filter_var, width=350)
        self.filter_items.append(f2)

        # 3. Fecha Inicio
        f3, self.start_date_entry = create_filter_group("Inicio:", DateEntry, width=120, is_date=True)
        self.start_date_entry.entry.bind("<FocusOut>", lambda e: self.apply_filters())
        self.start_date_entry.entry.bind("<Return>", lambda e: self.apply_filters())
        self.start_date_entry.bind("<<DateEntrySelected>>", lambda e: self.apply_filters())
        self.filter_items.append(f3)

        # 4. Fecha Final
        f4, self.end_date_entry = create_filter_group("Fin:", DateEntry, width=120, is_date=True)
        self.end_date_entry.entry.bind("<FocusOut>", lambda e: self.apply_filters())
        self.end_date_entry.entry.bind("<Return>", lambda e: self.apply_filters())
        self.end_date_entry.bind("<<DateEntrySelected>>", lambda e: self.apply_filters())
        self.filter_items.append(f4)

        # 5. Filtrar Texto
        self.search_var = tk.StringVar()
        f5, self.search_entry = create_filter_group("Filtrar:", ttk.Entry, self.search_var, width=150)
        self.search_entry.bind("<KeyRelease>", self.apply_filters)
        self.search_entry.configure(style='Borderless.TEntry')
        self.filter_items.append(f5)

        def _update_layout(event):
            # Calculate Layout
            card_width = self.filter_card.winfo_width()
            if card_width < 50: return # Too small/initializing

            max_width = card_width - 40 # Padding
            x, y = 0, 0
            row_height = 0
            vertical_spacing = 15
            horizontal_spacing = 15

            # Place elements
            for item in self.filter_items:
                item.update_idletasks() # Ensure dimensions are known
                w = item.winfo_reqwidth()
                h = item.winfo_reqheight()
                
                if x + w > max_width and x > 0:
                    # Wrap to next line
                    x = 0
                    y += row_height + vertical_spacing
                    row_height = 0
                
                item.place(x=x, y=y)
                row_height = max(row_height, h)
                x += w + horizontal_spacing
            
            content_height = y + row_height
            self.filter_card.itemconfig(self.filter_row_window, width=max_width, height=content_height)
            
            total_height = content_height + 40 # Bottom padding
            
            # Check if we need to resize the canvas (avoid infinite loops by tolerance)
            current_height = int(self.filter_card.cget("height"))
            if abs(total_height - current_height) > 5:
                self.filter_card.configure(height=total_height)
                # Setting height triggers <Configure>, so we return and draw on next pass
                return

            # Update Background Drawing
            self.filter_card.delete("bg")
            w, h = card_width, total_height # Use calculated height for BG
            
            # Create image for shadow/bg
            img = Image.new("RGBA", (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            
            # Shadows
            draw.rounded_rectangle((3, 5, w-3, h-1), radius=15, fill="#ccd1d9") 
            draw.rounded_rectangle((2, 2, w-2, h-2), radius=15, fill="#e2e6ea")
            # Card Body
            draw.rounded_rectangle((0, 0, w-5, h-5), radius=15, fill="white")
            
            bg = ImageTk.PhotoImage(img)
            self.filter_card._bg = bg # Keep reference
            self.filter_card.create_image(0,0, image=bg, anchor="nw", tags="bg")
            self.filter_card.tag_lower("bg")

        self.filter_card.bind("<Configure>", _update_layout)




        # --- Configuración de Estilo Blanco ---
        style = ttk.Style()
        style.configure("White.TFrame", background="white")
        style.configure("White.TPanedwindow", background="white")
        self.configure(bg="white")

        # --- PanedWindow para dividir la vista ---
        main_paned_window = ttk.Panedwindow(self, orient=HORIZONTAL, style="White.TPanedwindow")
        main_paned_window.pack(expand=True, fill="both", padx=20, pady=0) # Zero vertical padding

        # --- Panel Izquierdo (Ventas y Detalles) ---
        left_pane = ttk.Frame(main_paned_window, style="White.TFrame")
        main_paned_window.add(left_pane, weight=4) 
        
        left_paned_window = ttk.Panedwindow(left_pane, orient=VERTICAL, style="White.TPanedwindow")
        left_paned_window.pack(expand=True, fill="both")

        # Helper for Floating Cards
        def create_floating_card_frame(parent_pane, title):
            # Wrapper frame for the pane
            wrapper = tk.Frame(parent_pane, bg="white", bd=0, highlightthickness=0) 
            
            # The Canvas Card
            card = tk.Canvas(wrapper, bg="white", highlightthickness=0, bd=0)
            card.pack(fill="both", expand=True, padx=5, pady=2)
            
            # Content Frame (White)
            content = tk.Frame(card, bg="white")
            content_window = card.create_window(20, 20, window=content, anchor="nw")

            def _draw(e):
                w, h = e.width, e.height
                if w < 50 or h < 50: return
                
                # Margins for shadow rendering (Reduced to maximize space)
                MARGIN = 8
                
                # Update content window size and position
                card.coords(content_window, MARGIN, MARGIN)
                card.itemconfig(content_window, width=w-(2*MARGIN), height=h-(2*MARGIN))
                
                card.delete("bg")
                
                # Create image
                img = Image.new("RGBA", (w, h), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                
                # Card Body Rect
                rect = (MARGIN, MARGIN, w-MARGIN, h-MARGIN)
                
                # Soft/Clean Shadow (Reference Style)
                # 1. Wide very soft blur
                draw.rounded_rectangle((rect[0]-5, rect[1]-3, rect[2]+5, rect[3]+5), radius=15, fill=(0,0,0,5))
                # 2. Soft ambient
                draw.rounded_rectangle((rect[0]-2, rect[1]-1, rect[2]+2, rect[3]+3), radius=15, fill=(0,0,0,15))
                # 3. Key shadow
                draw.rounded_rectangle((rect[0]-1, rect[1], rect[2]+1, rect[3]+2), radius=15, fill=(0,0,0,25))
                
                # Body
                draw.rounded_rectangle(rect, radius=15, fill="white")
                
                bg = ImageTk.PhotoImage(img)
                card._bg = bg
                card.create_image(0,0, image=bg, anchor="nw", tags="bg")
                card.tag_lower("bg")
            
            card.bind("<Configure>", _draw)
            
            # Title
            if title:
                tk.Label(content, text=title, font=(FONT_FAMILY, 12, "bold"), bg="white", anchor="w", fg=COLOR_TEXT_DARK).pack(fill="x", pady=(0, 10))
                
            return wrapper, content

        # Frame Superior: Lista de Ventas (Floating Card)
        # Title removed to match desired design (redundant with main header)
        sales_wrapper, sales_content = create_floating_card_frame(left_paned_window, None)
        left_paned_window.add(sales_wrapper, weight=1)

        # --- Totals Footer (Packed Before Tree to preserve bottom visibility) ---
        self.totals_frame = tk.Frame(sales_content, bg="white") 
        self.totals_frame.pack(side="bottom", fill="x", pady=2) 
        
        inner_total_frame = tk.Frame(self.totals_frame, bg="white") 
        inner_total_frame.pack(side="right", padx=10)
        
        # Total (Base)
        self.lbl_sum_total = tk.Label(inner_total_frame, text="Total: S/ 0.00", font=(FONT_FAMILY, 12, "bold"), bg="white", fg=COLOR_TEXT_DARK)
        self.lbl_sum_total.pack(side="left", padx=10)
        
        # Desc/Adic (Diff)
        self.lbl_sum_diff = tk.Label(inner_total_frame, text="Desc/Adic: S/ 0.00", font=(FONT_FAMILY, 12, "bold"), bg="white", fg="#17a2b8")
        self.lbl_sum_diff.pack(side="left", padx=10)
        
        # Total N. (Final)
        self.lbl_sum_final = tk.Label(inner_total_frame, text="Total N.: S/ 0.00", font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), bg="white", fg="#28a745")
        self.lbl_sum_final.pack(side="left", padx=10)

        # Treeview Container
        st_frame = tk.Frame(sales_content, bg="white")
        st_frame.pack(fill="both", expand=True)
        
        # Scrollbar needs to be defined first or packed side right
        sales_scrollbar = ttk.Scrollbar(st_frame, orient=VERTICAL)
        sales_scrollbar.pack(side="right", fill="y")
        
        self.sales_tree = ttk.Treeview(st_frame, columns=("ID", "Tipo", "Número", "Fecha", "Cliente", "TotalOriginal", "TotalFinal", "DescAdic"), show="tree headings", displaycolumns=("Tipo", "Número", "Fecha", "Cliente", "TotalOriginal", "TotalFinal", "DescAdic"), yscrollcommand=sales_scrollbar.set)
        self.sales_tree.pack(side="left", fill="both", expand=True)
        sales_scrollbar.config(command=self.sales_tree.yview)

        self.sales_tree.heading("#0", text="Estado", anchor="center", command=lambda: self.treeview_sort_column(self.sales_tree, "#0", False))
        self.sales_tree.column("#0", width=60, anchor="center", stretch=False)
        self.sales_tree.tag_configure('oddrow', background="#f2f2f2")
        self.sales_tree.tag_configure('evenrow', background="white")

        # Configurar encabezados con ordenamiento
        columns_data = [
            ("Tipo", "Tipo", 100, "center"),
            ("Número", "Número", 100, "center"),
            ("Fecha", "Fecha", 150, "center"),
            ("Cliente", "Cliente", 200, "w"),
            ("TotalOriginal", "Total", 100, "e"),
            ("DescAdic", "Total N.", 100, "e"),
            ("TotalFinal", "Desc/Adic", 100, "e")
        ]

        for col_id, col_text, col_width, col_anchor in columns_data:
            self.sales_tree.heading(col_id, text=col_text, command=lambda _col=col_id: self.treeview_sort_column(self.sales_tree, _col, False))
            self.sales_tree.column(col_id, width=col_width, anchor=col_anchor)

        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)
        self.sales_tree.bind("<Double-1>", self.on_tree_double_click)
        self.sales_tree.bind("<Button-3>", self.on_tree_right_click)
        self.sales_tree.bind("<Motion>", self.on_tree_motion) # Tooltip




        # Frame Inferior: Detalles de la Venta (Floating Card)
        details_wrapper, details_content = create_floating_card_frame(left_paned_window, "Detalles de la Venta")
        left_paned_window.add(details_wrapper, weight=1)

        # Tree Container
        dt_frame = tk.Frame(details_content, bg="white")
        dt_frame.pack(fill="both", expand=True)

        details_scrollbar = ttk.Scrollbar(dt_frame, orient=VERTICAL)
        details_scrollbar.pack(side="right", fill="y")

        self.details_tree = ttk.Treeview(dt_frame, columns=("Producto", "Cantidad", "U.Medida", "Precio", "Subtotal"), show="headings", yscrollcommand=details_scrollbar.set)
        self.details_tree.pack(side="left", fill="both", expand=True)
        details_scrollbar.config(command=self.details_tree.yview)
        
        self.details_tree.tag_configure('oddrow', background="#f2f2f2")
        self.details_tree.tag_configure('evenrow', background="white")

        self.details_tree.heading("Producto", text="Producto")
        self.details_tree.heading("Cantidad", text="Cant.")
        self.details_tree.heading("U.Medida", text="U.M.")
        self.details_tree.heading("Precio", text="P. Unit.")
        self.details_tree.heading("Subtotal", text="Subtotal")
        
        self.details_tree.column("Producto", width=250, anchor="w")
        self.details_tree.column("Cantidad", width=80, anchor="center")
        self.details_tree.column("U.Medida", width=80, anchor="center")
        self.details_tree.column("Precio", width=100, anchor="e")
        self.details_tree.column("Subtotal", width=100, anchor="e")


        # Helper for Ticket Card (80mm ~ 302px, Centered, Intense Homogeneous Shadow)
        def create_ticket_card_frame(parent_pane):
            wrapper = tk.Frame(parent_pane, bg="white", bd=0, highlightthickness=0)
            card = tk.Canvas(wrapper, bg="white", highlightthickness=0, bd=0)
            card.pack(fill="both", expand=True, padx=0, pady=0)
            
            # 80mm ~ 302px. Increased to 340 for better fit of long lines
            TICKET_WIDTH = 340 
            
            content = tk.Frame(card, bg="#ededed")
            content_window = card.create_window(0, 0, window=content, anchor="nw") 

            def _draw(e):
                w, h = e.width, e.height
                if w < 50 or h < 50: return
                
                # Center the ticket
                x_pos = max(10, (w - TICKET_WIDTH) // 2)
                paper_h = max(100, h - 40) # 20px vertical margins
                
                card.coords(content_window, x_pos, 20)
                card.itemconfig(content_window, width=TICKET_WIDTH, height=paper_h)
                
                card.delete("bg")
                
                img = Image.new("RGBA", (w, h), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                
                # Deep Lifted Shadow (Reference Style)
                # The reference shows a strong shadow, particularly bottom-right
                s_rect = (x_pos, 20, x_pos+TICKET_WIDTH, 20+paper_h)
                
                # 1. Wide soft expand
                draw.rectangle((s_rect[0]-8, s_rect[1]-4, s_rect[2]+8, s_rect[3]+12), fill=(0,0,0,5))
                # 2. Medium distinct shadow
                draw.rectangle((s_rect[0]-4, s_rect[1]-2, s_rect[2]+4, s_rect[3]+8), fill=(0,0,0,15))
                # 3. Tight deep shadow
                draw.rectangle((s_rect[0]-1, s_rect[1]-1, s_rect[2]+1, s_rect[3]+4), fill=(0,0,0,40))
                
                # Paper Body
                draw.rectangle(s_rect, fill="#ededed")
                
                bg = ImageTk.PhotoImage(img)
                card._bg = bg
                card.create_image(0,0, image=bg, anchor="nw", tags="bg")
                card.tag_lower("bg")
            
            card.bind("<Configure>", _draw)
            return wrapper, content

        # --- Panel Derecho (Vista Previa de Ticket - Custom 80mm Card) ---
        ticket_wrapper, ticket_content = create_ticket_card_frame(main_paned_window)
        main_paned_window.add(ticket_wrapper, weight=1) 
        
        # Use pack inside content frame
        self.ticket_preview = tk.Text(ticket_content, wrap="none", font=("Consolas", 9), width=42, relief="flat", background="#ededed", foreground=COLOR_TEXT_LIGHT, highlightthickness=0, borderwidth=0)
        self.ticket_preview.pack(fill="both", expand=True, padx=15, pady=15)
        self.ticket_preview.config(state="disabled")
        
        # Configurar tags para estilos
        self.ticket_preview.tag_configure("center", justify='center')
        self.ticket_preview.tag_configure("right", justify='right')
        self.ticket_preview.tag_configure("left", justify='left')
        self.ticket_preview.tag_configure("bold", font=("Consolas", 9, "bold"))
        self.ticket_preview.tag_configure("inverse", background=COLOR_TEXT_LIGHT, foreground="#ededed")
        self.ticket_preview.tag_configure("large", font=("Consolas", 11, "bold")) 
        
        self.reprint_button = ttk.Button(ticket_content, text="🖨️ Reimpresión", command=self.reprint_ticket, bootstyle="secondary-outline", state="disabled")
        if config_manager.load_setting("allow_reprint", "Si") == "Si":
            self.reprint_button.pack(fill="x", padx=15, pady=(0,15))

        self.load_filters()

    def treeview_sort_column(self, tv, col, reverse):
        """Ordena la columna de un treeview al hacer click en el encabezado."""
        if col == "#0":
            # Sort by tags (Status)
            l = [(tv.item(k, "tags")[0] if tv.item(k, "tags") else "", k) for k in tv.get_children('')]
        else:
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        # Intentar convertir a números para ordenar correctamente
        try:
            # Limpiar símbolos de moneda y separadores para la conversión
            l.sort(key=lambda t: float(t[0].replace('S/ ', '').replace(',', '')), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def check_status_soap(self, sale_id):
        """Consulta el estado del comprobante en SUNAT via SOAP."""
        conn = database.create_connection()
        conn.row_factory = database.sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales WHERE id=?", (sale_id,))
        sale_row = cur.fetchone()
        if not sale_row:
             conn.close()
             return
        
        issuer_id = sale_row['issuer_id']
        doc_type_full = sale_row['document_type']
        doc_number = sale_row['document_number']
        sunat_status = sale_row['sunat_status']
        sunat_note = sale_row['sunat_note']
        conn.close()
        
        issuer = database.get_issuer_by_id(issuer_id)
        if not issuer:
            messagebox.showerror("Error", "No se encontró el emisor.", parent=self)
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        see_dir = os.path.join(base_dir, "SEE Electronica")
        xml_gen = xml_generator.XMLGenerator(see_dir)
        
        result = None
        
        # Check is valid doc type
        if "FACTURA" in doc_type_full.upper():
             type_code = "01"
        elif "BOLETA" in doc_type_full.upper():
             type_code = "03"
        else:
             messagebox.showerror("Error", "Solo se consulta estado de Facturas y Boletas.", parent=self)
             return

        # Check for Ticket in note
        ticket_match = re.search(r"Ticket:\s*(\d+)", sunat_note or "")
        
        consulted = False
        if ticket_match:
            ticket = ticket_match.group(1)
            # Ask user preference
            # "Yes" -> Ticket, "No" -> CDR (Validez)
            ans = messagebox.askyesnocancel("Consulta SUNAT", f"Se encontró Ticket {ticket}.\nSI: Consultar getStatus(Ticket)\nNO: Consultar getStatusCdr(Validez)\nCANCELAR: Salir", parent=self)
            if ans is None: return
            
            if ans: # YES -> Ticket
                result = xml_gen.check_ticket_status(issuer, ticket)
                consulted = True
        
        if not consulted:
             parts = doc_number.split('-')
             if len(parts) != 2:
                  messagebox.showerror("Error", "Formato de número inválido.", parent=self)
                  return
             series, number = parts
             result = xml_gen.check_cdr_status(issuer, type_code, series, number)
             
        if result:
             msg = result.get('response') or result.get('error')
             
             # Clean up message (Extract FaultString or Description)
             clean_msg = msg
             if msg:

                 # Try to find SOAP Fault String
                 fault_match = re.search(r'<[^:]*?:?faultstring>(.*?)</[^:]*?:?faultstring>', msg, re.IGNORECASE | re.DOTALL)
                 if fault_match:
                     clean_msg = f"Resultado:\n{fault_match.group(1).strip()}"
                 else:
                     # Try to find CDR Description
                     desc_match = re.search(r'<[^:]*?:?Description>(.*?)</[^:]*?:?Description>', msg, re.IGNORECASE | re.DOTALL)
                     if desc_match:
                         clean_msg = f"Resultado:\n{desc_match.group(1).strip()}"

             messagebox.showinfo("Respuesta SUNAT", clean_msg, parent=self)

    def on_tree_right_click(self, event):
        """Maneja el click derecho en el Treeview para mostrar menú contextual."""
        region = self.sales_tree.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            return

        column = self.sales_tree.identify_column(event.x)
        

        
        if column == "#0": # Columna "Estado"
            item_id = self.sales_tree.identify_row(event.y)
            if not item_id: return
            
            self.sales_tree.selection_set(item_id)
            item_values = self.sales_tree.item(item_id, "values")
            # values[0] is sale_id
            
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Consultar Estado (SUNAT)", command=lambda: self.check_status_soap(item_values[0]))
            menu.post(event.x_root, event.y_root)
            return

        if column == "#1": # Columna "Tipo"
            item_id = self.sales_tree.identify_row(event.y)
            if not item_id: return
            
            # Select the row
            self.sales_tree.selection_set(item_id)
            self.sales_tree.focus(item_id)
            
            item_values = self.sales_tree.item(item_id, "values")
            # values index: 0=ID, 1=Tipo, ...
            doc_type = item_values[1]
            
            menu = tk.Menu(self, tearoff=0)
            
            if "NOTA DE VENTA" in doc_type.upper():
                menu.add_command(label="Emitir Boleta", command=lambda: self.convert_document(item_values[0], "BOLETA"))
                menu.add_command(label="Emitir Factura", command=lambda: self.convert_document(item_values[0], "FACTURA"))
            elif "BOLETA" in doc_type.upper() or "FACTURA" in doc_type.upper():
                if "NOTA" not in doc_type.upper():
                    menu.add_command(label="Emitir Nota de Crédito", command=lambda: self.convert_document(item_values[0], "NOTA_CREDITO"))
            
            if menu.index("end") is not None:
                menu.post(event.x_root, event.y_root)

    def on_tree_double_click(self, event):
        """Maneja el doble click en el Treeview para mostrar menú contextual."""
        region = self.sales_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.sales_tree.identify_column(event.x)
        
        if column == "#1": # Columna "Tipo" (Updated)
            item_id = self.sales_tree.identify_row(event.y)
            if not item_id: return
            
            item_values = self.sales_tree.item(item_id, "values")
            # values index: 0=ID, 1=Tipo, ...
            doc_type = item_values[1]
            
            menu = tk.Menu(self, tearoff=0)
            
            if "NOTA DE VENTA" in doc_type.upper():
                menu.add_command(label="Emitir Boleta", command=lambda: self.convert_document(item_values[0], "BOLETA"))
                menu.add_command(label="Emitir Factura", command=lambda: self.convert_document(item_values[0], "FACTURA"))
            elif "BOLETA" in doc_type.upper() or "FACTURA" in doc_type.upper():
                if "NOTA" not in doc_type.upper():
                    menu.add_command(label="Emitir Nota de Crédito", command=lambda: self.convert_document(item_values[0], "NOTA_CREDITO"))
            
            if menu.index("end") is not None:
                menu.post(event.x_root, event.y_root)

    def on_tree_motion(self, event):
        """Muestra tooltip al pasar el mouse sobre la columna de estado (#0)."""
        region = self.sales_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.sales_tree.identify_column(event.x)
            if column == "#0": # Status Column
                item_id = self.sales_tree.identify_row(event.y)
                if item_id and item_id != self.last_tooltip_item:
                    tags = self.sales_tree.item(item_id, "tags")
                    # Check tags for status info? 
                    # Tags: ('Activo', 'oddrow', 'STATUS_ACEPTADO/RECHAZADO/PENDIENTE', 'NOTE_XYZ') 
                    # Better: Store tooltip text in a hidden way or map?
                    # Or fetch from DB? No, fetching on motion is slow.
                    # Let's store the NOTE in tags if short, or in a dict map in python.
                    
                    note = self.sales_notes.get(item_id, "")
                    status = self.sales_statuses.get(item_id, "")
                    
                    if not note and not status: 
                        if self.tooltip: self.tooltip.hide_tip()
                        return

                    text = f"Estado: {status}\n{note}"
                    
                    if self.tooltip: self.tooltip.hide_tip()
                    from ttkbootstrap.tooltip import ToolTip
                    self.tooltip = ToolTip(self.sales_tree, text=text, bootstyle="info")
                    self.tooltip.show_tip()
                    self.last_tooltip_item = item_id
                elif not item_id:
                    if self.tooltip: self.tooltip.hide_tip()
                    self.last_tooltip_item = None
            else:
                if self.tooltip: 
                    self.tooltip.hide_tip()
                    self.last_tooltip_item = None
        else:
            if self.tooltip: 
                self.tooltip.hide_tip()
                self.last_tooltip_item = None

    def convert_document(self, sale_id, target_type):
        """Placeholder para la lógica de conversión."""
        messagebox.showinfo("En Desarrollo", f"Funcionalidad para convertir venta ID {sale_id} a {target_type} pendiente de implementación.", parent=self)

    def _number_to_text(self, amount):
        """Convierte un número a texto en soles (Español)."""
        # Esta es una implementación simplificada.
        # En producción, usar librería num2words si es posible, o esta lógica básica.
        # Por ahora copiamos la lógica básica de sales_view.
        
        UNIDADES = ["", "UN ", "DOS ", "TRES ", "CUATRO ", "CINCO ", "SEIS ", "SIETE ", "OCHO ", "NUEVE "]
        DECENAS = ["", "DIEZ ", "VEINTE ", "TREINTA ", "CUARENTA ", "CINCUENTA ", "SESENTA ", "SETENTA ", "OCHENTA ", "NOVENTA "]
        DIEZ_VEINTE = ["DIEZ ", "ONCE ", "DOCE ", "TRECE ", "CATORCE ", "QUINCE ", "DIECISEIS ", "DIECISIETE ", "DIECIOCHO ", "DIECINUEVE "]
        CENTENAS = ["", "CIENTO ", "DOSCIENTOS ", "TRESCIENTOS ", "CUATROCIENTOS ", "QUINIENTOS ", "SEISCIENTOS ", "SETECIENTOS ", "OCHOCIENTOS ", "NOVECIENTOS "]

        def leer_decenas(n):
            if n < 10:
                return UNIDADES[n]
            d, u = divmod(n, 10)
            if n <= 19:
                return DIEZ_VEINTE[n-10]
            if u == 0:
                return DECENAS[d]
            return DECENAS[d] + "Y " + UNIDADES[u]

        def leer_centenas(n):
            c, d = divmod(n, 100)
            if n == 100: return "CIEN "
            return CENTENAS[c] + leer_decenas(d)

        def leer_miles(n):
            m, c = divmod(n, 1000)
            if m == 0:
                return leer_centenas(c)
            if m == 1:
                return "MIL " + leer_centenas(c)
            return leer_centenas(m) + "MIL " + leer_centenas(c)

        entero = int(amount)
        decimal = int(round((amount - entero) * 100))
        
        letras = ""
        if entero == 0:
            letras = "CERO "
        elif entero < 1000000:
            letras = leer_miles(entero)
        else:
            letras = "NUMERO MUY GRANDE "
            
        return f"{letras} CON {decimal:02d}/100 SOLES"

    def load_filters(self):
        self.issuers = database.get_all_issuers()
        issuer_names = ["Todos"] + sorted(list(set(i[1] for i in self.issuers)))
        self.issuer_filter_combo['values'] = issuer_names
        
        # Load persistence
        last_issuer = config_manager.load_setting("last_report_issuer", "Todos")
        last_address = config_manager.load_setting("last_report_address", "Todas")
        # Dates default to today as per user request
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        if last_issuer in issuer_names:
            self.issuer_filter_var.set(last_issuer)
            self.on_issuer_filter_select(save=False) # Update addresses but don't save yet
            
            if last_address in self.address_filter_combo['values']:
                self.address_filter_var.set(last_address)
        else:
            self.issuer_filter_var.set("Todos")
            self.on_issuer_filter_select(save=False)

        # Set dates to today
        self.start_date_entry.entry.delete(0, tk.END)
        self.start_date_entry.entry.insert(0, today_str)
        self.end_date_entry.entry.delete(0, tk.END)
        self.end_date_entry.entry.insert(0, today_str)

        # Bind events for auto-filtering
        self.issuer_filter_combo.bind("<<ComboboxSelected>>", self.on_issuer_filter_select)
        self.address_filter_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
        # Apply initial filter
        self.apply_filters()

    def on_issuer_filter_select(self, event=None, save=True):
        selected_issuer_name = self.issuer_filter_var.get()
        if selected_issuer_name == "Todos":
            self.address_filter_combo['values'] = ["Todas"]
            self.address_filter_var.set("Todas")
        else:
            addresses = [i[3] for i in self.issuers if i[1] == selected_issuer_name]
            # Smart Address Selection: If only one address, select it automatically
            if len(addresses) == 1:
                self.address_filter_combo['values'] = addresses
                self.address_filter_var.set(addresses[0])
            else:
                self.address_filter_combo['values'] = ["Todas"] + addresses
                self.address_filter_var.set("Todas")
        
        if save:
            self.apply_filters()

    def apply_filters(self, event=None):
        issuer_name = self.issuer_filter_var.get()
        address = self.address_filter_var.get()
        
        # Obtener fechas
        try:
            start_date = self.start_date_entry.entry.get()
            end_date = self.end_date_entry.entry.get()
            
            # Save persistence
            config_manager.save_setting("last_report_issuer", issuer_name)
            config_manager.save_setting("last_report_address", address)
            config_manager.save_setting("last_report_start_date", start_date)
            config_manager.save_setting("last_report_end_date", end_date)
            
            # Convertir de DD/MM/YYYY a YYYY-MM-DD para la base de datos
            
            # Convertir de DD/MM/YYYY a YYYY-MM-DD para la base de datos
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%d/%m/%Y")
                start_date_db = start_date_obj.strftime("%Y-%m-%d")
            else:
                start_date_db = None
                
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%d/%m/%Y")
                end_date_db = end_date_obj.strftime("%Y-%m-%d")
            else:
                end_date_db = None
                
        except ValueError:
            # Si hay error en formato, ignorar fechas
            start_date_db = None
            end_date_db = None

        # Obtener texto de filtro
        filter_text = self.search_var.get().strip()

        self.populate_sales_list(issuer_name if issuer_name != "Todos" else None,
                                 address if address != "Todas" else None,
                                 start_date_db,
                                 end_date_db,
                                 filter_text)

    def _adjust_column_widths(self, tree):
        """Ajusta automáticamente el ancho de las columnas basado en el contenido."""
        font = tk.font.Font(font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        for col in tree['columns']:
            max_width = font.measure(tree.heading(col, 'text')) + 20 # Ancho del encabezado + padding
            for item in tree.get_children():
                if 'placeholder' in tree.item(item, 'tags'): continue
                cell_value = tree.set(item, col)
                cell_width = font.measure(str(cell_value)) + 20
                if cell_width > max_width:
                    max_width = cell_width
            
            # Cap width for Product column to avoid excessive expansion
            if col == "Producto" and max_width > 300:
                max_width = 300
                
            tree.column(col, width=max_width)

    def populate_sales_list(self, issuer_name=None, address=None, start_date=None, end_date=None, filter_text=""):
        for i in self.sales_tree.get_children(): self.sales_tree.delete(i)
        
        sales_data = database.get_all_sales_with_customer_name(issuer_name, address, start_date, end_date)
        
        
        total_filtered = 0.0
        total_base = 0.0
        total_diff = 0.0
        
        if not sales_data:

            self.sales_tree.insert("", "end", values=("", "", "No hay ventas para este filtro", "", "", "", "", ""), tags=('placeholder',))
        else:
            self.sales_notes = {}
            self.sales_statuses = {}
            for i, row in enumerate(sales_data):
                tag_stripe = 'oddrow' if i % 2 == 1 else 'evenrow'
                # row: id, doc_type, doc_number, date, customer_name, total_amount, diff_amount, issuer_name, issuer_address, sunat_status, sunat_note
                sale_id = row[0]
                doc_type = row[1]
                doc_number = row[2]
                date_str = row[3] 
                customer = row[4] or ""
                total = row[5]
                diff = row[6] if row[6] is not None else 0.0
                sunat_status = row[9] if len(row) > 9 else None
                sunat_note = row[10] if len(row) > 10 else ""
                
                # --- Filtering Logic ---
                if filter_text:
                    ft = filter_text.lower()
                    # Clean amount for comparison (remove commas)
                    total_str_clean = f"{total:.2f}".replace(",", "") # 1000.00
                    total_str_int = f"{int(total)}" # 1000
                    
                    match = False
                    # 1. Series/Number (doc_number)
                    if doc_number and ft in str(doc_number).lower(): match = True
                    # 2. Customer Name
                    elif customer and ft in customer.lower(): match = True
                    # 3. Amount (Exact match or close string match?)
                    # User asked for "1,000.00 or 1000 or 1000.00"
                    # We check if the filter text is contained in the formatted amount or matches clean versions
                    elif ft in total_str_clean or ft == total_str_int: match = True
                    # Also check if user typed "1,000.00" exactly
                    elif ft in f"{total:,.2f}".lower(): match = True
                    
                    if not match:
                        continue

                # --- Date Formatting (DD/MM/YYYY) ---
                try:
                    # Try parsing assuming standard SQL format YYYY-MM-DD HH:MM:SS
                    date_obj = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except ValueError:
                    try:
                        # Try YYYY-MM-DD
                        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%d/%m/%Y")
                    except ValueError:
                        formatted_date = str(date_str) # Fallback

                total_normal = total - diff
                
                desc_adic_str = f"S/ {diff:,.2f}"
                total_original_str = f"S/ {total_normal:,.2f}" 
                total_final_str = f"S/ {total:,.2f}" 
                
                # Order: ID, Tipo, Número, Fecha, Cliente, TotalOriginal, DescAdic, TotalFinal
                formatted_row = (sale_id, doc_type, doc_number, formatted_date, customer, total_original_str, desc_adic_str, total_final_str)
                # Add 'Activo' tag for sorting purposes
                # Status Icon
                icon = self.status_icon # Default Green for 'ACEPTADO' or empty
                if sunat_status == 'PENDIENTE':
                    icon = self.status_icon_pending
                elif sunat_status == 'RECHAZADO':
                    icon = self.status_icon_rejected
                elif sunat_status == 'ACEPTADO':
                    icon = self.status_icon
                else: 
                     # If no status but is Boleta/Factura, maybe pending logic? Or just no icon if old?
                     # User wants icons for Factura/Boleta.
                     doc_type_upper = doc_type.upper()
                     if "FACTURA" in doc_type_upper or "BOLETA" in doc_type_upper:
                         if "NOTA" not in doc_type_upper:
                             if not sunat_status:
                                 icon = self.status_icon_pending 
                         else:
                             icon = ""
                     else:
                         icon = ""

                # Store for tooltip
                item_iid = self.sales_tree.insert("", "end", text="", image=icon, values=formatted_row, tags=('Activo', tag_stripe))
                self.sales_notes[item_iid] = sunat_note
                self.sales_statuses[item_iid] = sunat_status or "Sin Estado"
                total_filtered += total
                total_base += total_normal
                total_diff += diff
                
            self._adjust_column_widths(self.sales_tree)
        
        self.lbl_sum_total.config(text=f"Total: S/ {total_base:,.2f}")
        self.lbl_sum_diff.config(text=f"Desc/Adic: S/ {total_diff:,.2f}")
        self.lbl_sum_final.config(text=f"Total N.: S/ {total_filtered:,.2f}")

        
        # Limpiar vistas de detalle y ticket
        for i in self.details_tree.get_children(): self.details_tree.delete(i)
        self.ticket_preview.config(state="normal")
        self.ticket_preview.delete("1.0", tk.END)
        self.ticket_preview.config(state="disabled")

    def on_sale_select(self, event):
        for i in self.details_tree.get_children(): self.details_tree.delete(i)
        selected_item = self.sales_tree.focus()
        if not selected_item or 'placeholder' in self.sales_tree.item(selected_item, 'tags'):
            return
            
        sale_id = self.sales_tree.item(selected_item)["values"][0]
        details = database.get_sale_details_by_sale_id(sale_id)
        
        if not details:
            self.details_tree.insert("", "end", values=("No hay detalles.", "", "", "", ""), tags=('placeholder',))
        else:
            for i, row in enumerate(details):
                tag_stripe = 'evenrow' if i % 2 == 0 else 'oddrow'
                formatted_row = (row[0], f"{row[1]:.2f}", row[4], f"S/ {row[2]:,.2f}", f"S/ {row[3]:,.2f}")
                self.details_tree.insert("", "end", values=formatted_row, tags=(tag_stripe,))
            self._adjust_column_widths(self.details_tree)
        
        self.update_ticket_preview(sale_id)

    def update_ticket_preview(self, sale_id):
        self.ticket_preview.config(state="normal")
        self.ticket_preview.delete("1.0", tk.END)
        
        sale_full_data = database.get_full_sale_data(sale_id)
        if not sale_full_data:
            self.ticket_preview.config(state="disabled")
            self.reprint_button.config(state="disabled")
            self.current_sale_data = None
            return

        self.current_sale_data = sale_full_data
        self.reprint_button.config(state="normal")

        sale = sale_full_data["sale"]
        details = sale_full_data["details"]
        
        # sale indices (UPDATED):
        # 0: date, 1: total, 2: obs, 3: doc_type, 4: doc_number, 5: customer_name, 6: customer_doc
        # 7: issuer_name, 8: issuer_ruc, 9: issuer_address
        # 10: district, 11: province, 12: department
        # 13: commercial_name, 14: bank_accounts, 15: initial_greeting, 16: final_greeting, 17: logo
        
        import textwrap

        # --- HEADER ---
        commercial_name = sale[13] or ""
        if commercial_name:
            self.ticket_preview.insert(tk.END, commercial_name + "\n", ("center", "bold"))
            
        issuer_name = sale[7] or ""
        ruc = sale[8] or ""
        self.ticket_preview.insert(tk.END, f"RUC: {ruc}\n", "center")
        issuer_name_lines = textwrap.wrap(issuer_name, width=42)
        for line in issuer_name_lines:
            self.ticket_preview.insert(tk.END, line + "\n", "center")
        
        address = sale[9] or ""
        district = sale[10] or ""
        province = sale[11] or ""
        department = sale[12] or ""
        
        address_parts = [address]
        if district: address_parts.append(district)
        if province: address_parts.append(province)
        if department: address_parts.append(department)
        
        full_address = " ".join([p for p in address_parts if p])
        address_lines = textwrap.wrap(full_address, width=42)
        for line in address_lines:
            self.ticket_preview.insert(tk.END, line + "\n", "center")
            
        initial_greeting = sale[15] or ""
        if initial_greeting:
            greeting_lines = textwrap.wrap(initial_greeting, width=42)
            for line in greeting_lines:
                self.ticket_preview.insert(tk.END, line + "\n", "center")

        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")

        # --- DOCUMENT INFO ---
        doc_type = sale[3] or ""
        # Mapping for full names
        if doc_type == "BOLETA":
            doc_type = "BOLETA DE VENTA ELECTRÓNICA"
        elif doc_type == "FACTURA":
            doc_type = "FACTURA ELECTRÓNICA"
            
        self.ticket_preview.insert(tk.END, doc_type + "\n", ("center", "bold"))
        
        doc_number = sale[4] or "" # Assuming format "SERIE-NUMERO" or just number
        if doc_number:
            self.ticket_preview.insert(tk.END, f"{doc_number}\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # --- EMISSION INFO ---
        self.ticket_preview.insert(tk.END, f"EMISIÓN: {sale[0]}\n", "center")
        
        customer_doc = sale[6] or ""
        if customer_doc:
            label = "RUC" if len(customer_doc) == 11 else "DNI"
            self.ticket_preview.insert(tk.END, f"{label}: {customer_doc}\n", "center")
            
        customer_name = sale[5] or ""
        if customer_name:
            self.ticket_preview.insert(tk.END, f"CLIENTE: {customer_name}\n", "center")
            
        # Address not always stored in sale record directly if simpler query used, 
        # but assuming it might be missing or we skip it if not available in `sale` tuple.
        # Based on `database.get_full_sale_data`, it seems we might not have customer address stored in `sales` table history
        # unless we join with customers table. 
        # For now, we skip customer address in history if not present.
        
        is_proforma = "NOTA DE VENTA" in doc_type.upper()
        
        if not is_proforma:
            self.ticket_preview.insert(tk.END, "MONEDA: SOL(PEN)\n", "center")
            self.ticket_preview.insert(tk.END, "FORMA DE PAGO: CONTADO\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # --- ITEMS ---
        header = "PRODUCTO      PESO    P.UNIT   P.TOTAL"
        self.ticket_preview.insert(tk.END, header + "\n", ("center", "bold"))
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # details: [(name, quantity, price, subtotal, unit_of_measure), ...]
        for item in details:
            # Line 1: Description (Left Aligned with indent)
            desc = item[0]
            desc_lines = textwrap.wrap(desc, width=40)
            for line in desc_lines:
                self.ticket_preview.insert(tk.END, "  " + line + "\n", "left")
            
            # Line 2: Qty+UM (PESO) Price Subtotal (Centered)
            qty = item[1]
            um = item[4]
            price = item[2]
            subtotal = item[3]
            
            qty_um = f"{qty:.2f} {um[:3]}"
            price_str = f"{price:.2f}"
            subtotal_str = f"{subtotal:.2f}"
            
            line2 = f"{qty_um}".center(16) + f"{price_str}".rjust(10) + f"{subtotal_str}".rjust(16)
            self.ticket_preview.insert(tk.END, line2 + "\n", "center")
            self.ticket_preview.insert(tk.END, "." * 42 + "\n", "center")
            
        # --- TOTALS ---
        total_val = sale[1]
        
        if not is_proforma:
            subtotal = total_val / 1.18
            igv = total_val - subtotal
            
            self.ticket_preview.insert(tk.END, f"Total Op.Gravadas: S/ {subtotal:.2f}\n", "center")
            self.ticket_preview.insert(tk.END, f"Total I.G.V 18%:   S/ {igv:.2f}\n", "center")
            
        # TOTAL A PAGAR (Inverse + Centered + Larger)
        total_str = f"TOTAL A PAGAR: S/ {total_val:,.2f}"
        self.ticket_preview.insert(tk.END, total_str.center(42) + "\n", ("center", "inverse", "large"))
        
        # Amount in letters
        total_letras = self._number_to_text(total_val)
        letras_lines = textwrap.wrap(total_letras, width=42)
        for line in letras_lines:
            self.ticket_preview.insert(tk.END, line + "\n", "center")
            
        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")
        
        # --- FOOTER ---
        if not is_proforma:
            self.ticket_preview.insert(tk.END, f"Representación Impresa de la\n", "center")
            self.ticket_preview.insert(tk.END, f"{doc_type}.\n", "center")
            self.ticket_preview.insert(tk.END, "Consultar su validez en https://shorturl.at/WoJnM\n", "center")
            
            # QR Placeholder
            self.ticket_preview.insert(tk.END, "\n[CÓDIGO QR]\n", "center")
            self.ticket_preview.insert(tk.END, f"Resumen: HASH_DUMMY_VALUE\n", "center")
            

        self.ticket_preview.insert(tk.END, "-" * 42 + "\n", "center")

        # Bank Accounts (Larger Font)
        bank_accounts = sale[14] or ""
        if bank_accounts:
            self.ticket_preview.insert(tk.END, "\n", "center")
            ba_lines = textwrap.wrap(bank_accounts, width=25)
            for line in ba_lines:
                self.ticket_preview.insert(tk.END, line + "\n", ("center", "large"))
            


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
        if not hasattr(self, 'current_sale_data') or not self.current_sale_data:
            return b""
            
        sale = self.current_sale_data["sale"]
        details = self.current_sale_data["details"]
        
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
        

        # --- PREPARE DATA ---
        import textwrap
        doc_type = sale[3] or ""
        commercial_name = sale[13] or ''
        address = sale[9] or ''
        district = sale[10] or ''
        province = sale[11] or ''
        department = sale[12] or ''
        
        address_parts = [address]
        if district: address_parts.append(district)
        if province: address_parts.append(province)
        if department: address_parts.append(department)
        full_address = " ".join([p for p in address_parts if p])
        
        doc_number = sale[4] or ""

        # --- NUMIER FORMAT CHECK ---
        print_format_nv = config_manager.load_setting('print_format_nv', 'APISUNAT')
        is_proforma = "NOTA DE VENTA" in doc_type.upper()
        
        if is_proforma and print_format_nv == "NUMIER":
             # ==========================================
             #              NUMIER FORMAT (REPRINT)
             # ==========================================
             
             # --- HEADER ---
             buffer.extend(ALIGN_CENTER)
             
             # Commercial Name (***NOMBRE***)
             if commercial_name:
                 buffer.extend(BOLD_ON + text(f"***{commercial_name}***\n") + BOLD_OFF)
             
             # Address
             # address, district, province, department are already extracted above
             if full_address:
                 # Wrap address
                 addr_lines = textwrap.wrap(full_address, width=42)
                 for line in addr_lines:
                     buffer.extend(text(line + "\n"))
             
             # DATE AND TIME
             # sale[0] is "YYYY-MM-DD HH:MM:SS" or similar
             date_time = sale[0].split(" ")
             date_str = date_time[0]
             time_str = date_time[1] if len(date_time) > 1 else ""
             
             # Use split to format date d-m-y if possible
             try:
                 parts = date_str.split("-")
                 if len(parts) == 3: # YYYY-MM-DD
                    date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
             except:
                 pass

             buffer.extend(text(f"FECHA:{date_str}\n"))
             
             # USUARIO Y HORA
             # We don't track the user who created the sale yet in this query
             # But we can use current user context or generic
             user_name = "ADMIN" # Placeholder or get from context if passed
             try:
                 user_name = self.master.master.master.username.upper()
             except:
                 pass
                 
             buffer.extend(text(f"USUARIO: {user_name} HORA:{time_str}\n"))
             
             # DOC NUMBER
             if doc_number:
                 buffer.extend(text(f"N.DOC: {doc_number}\n"))
                 
             # DOCUMENT TITLE
             buffer.extend(BOLD_ON + text("NOTA DE VENTA\n") + BOLD_OFF)
             
             # ITEMS HEADER
             # 42 chars:
             # PROD (20) | UND (3) | PRC (8) | TOT (9)
             header = "PRODUCTO             UND   PRECIO   IMPORTE"
             buffer.extend(text(header + "\n"))
             buffer.extend(text("-" * 42 + "\n"))
             
             # ITEMS
             for item in details:
                 # Single Line Format
                 description = item[0] # assuming index 0 is name
                 name = description[:20].ljust(20)
                 
                 # Qty
                 qty_val = item[1]
                 qty_str = f"{qty_val:.0f}" if qty_val.is_integer() else f"{qty_val:.1f}"
                 qty_str = qty_str[:3].center(3)
                 
                 # Price
                 price_val = item[2]
                 price_str = f"{price_val:.2f}".rjust(8)
                 
                 # Subtotal
                 subtotal_val = item[3]
                 subtotal_str = f"{subtotal_val:.2f}".rjust(9)

                 line = f"{name} {qty_str} {price_str}{subtotal_str}"
                 buffer.extend(text(line + "\n"))
                 
             buffer.extend(text("-" * 42 + "\n"))
             
             # TOTAL
             total_label = "TOTAL     S/"
             total_val = f"{sale[1]:.2f}"
             total_line = total_label.rjust(25) + total_val.rjust(16)
             buffer.extend(BOLD_ON + text(total_line + "\n") + BOLD_OFF)
             
             buffer.extend(text("-" * 42 + "\n"))
             
             # PAYMENT INFO (From sale indices 20-23)
             # 20: payment_method1, 21: amount_paid1, 22: payment_method2, 23: amount_paid2
             pm1 = sale[20] or "EFECTIVO"
             ap1 = sale[21] or 0.0
             pm2 = sale[22]
             ap2 = sale[23] or 0.0
             
             payment_method_str = pm1
             if ap2 > 0 and pm2 and pm2 != "NINGUNO":
                 payment_method_str += f" + {pm2}"
             
             amount_received = ap1 + ap2
             change = amount_received - sale[1]
             if change < 0: change = 0.0
             
             # Calculate Discount/Adic
             # details[1] = quantity, details[2] = sold_price, details[6] = original_price (fetched now)
             total_diff = 0.0
             for item in details:
                 qty = item[1]
                 sold_price = item[2]
                 original_price = item[6] if len(item) > 6 and item[6] is not None else sold_price
                 total_diff += (sold_price - original_price) * qty
             
             discount_text = ""
             if total_diff > 0.001:
                 discount_text = f"ADIC.: S/ {total_diff:.2f}"
             elif total_diff < -0.001:
                 discount_text = f"DSCTO.: S/ {abs(total_diff):.2f}"
             
             if discount_text:
                 buffer.extend(ALIGN_LEFT)
                 buffer.extend(text(f"{discount_text}\n"))
             
             buffer.extend(ALIGN_LEFT)
             buffer.extend(text(f"PAGO: {payment_method_str}\n"))
             buffer.extend(text(f"RECIBIDO: S/ {amount_received:.2f}\n"))
             buffer.extend(text(f"VUELTO:   S/ {change:.2f}\n"))
             
             # FOOTER MESSAGE
             buffer.extend(ALIGN_CENTER)
             buffer.extend(text("NOTA DE VENTA CANJEAR POR BOLETA/FACTURA\n"))
             
             buffer.extend(CUT)
             return buffer

        # ==========================================
        #           END NUMIER FORMAT
        # ==========================================

        import textwrap
        
        # --- HEADER ---
        buffer.extend(ALIGN_CENTER)
        
        # LOGO
        logo_data = sale[17]
        if logo_data:
            logo_bytes = self._get_escpos_image_bytes(logo_data, max_width=384)
            buffer.extend(logo_bytes)
        
        # Commercial Name
        commercial_name = sale[13] or ''
        if commercial_name:
            buffer.extend(BOLD_ON + text(commercial_name + "\n") + BOLD_OFF)
        
        # RUC
        ruc = sale[8] or ''
        buffer.extend(text(f"RUC: {ruc}\n"))
        
        # Name
        issuer_name = sale[7] or ''
        buffer.extend(text(issuer_name + "\n"))
        
        # Address
        address = sale[9] or ''
        district = sale[10] or ''
        province = sale[11] or ''
        department = sale[12] or ''
        
        address_parts = [address]
        if district: address_parts.append(district)
        if province: address_parts.append(province)
        if department: address_parts.append(department)
        
        full_address = " ".join([p for p in address_parts if p])
        address_lines = textwrap.wrap(full_address, width=42)
        for line in address_lines:
            buffer.extend(text(line + "\n"))
            
        # Initial Greeting
        initial_greeting = sale[15]
        if initial_greeting:
            greeting_lines = textwrap.wrap(initial_greeting, width=42)
            for line in greeting_lines:
                buffer.extend(text(line + "\n"))

        buffer.extend(text("-" * 42 + "\n"))

        # --- DOCUMENT INFO ---
        doc_type = sale[3] or ""
        # Mapping for full names
        if doc_type == "BOLETA":
            doc_type = "BOLETA DE VENTA ELECTRÓNICA"
        elif doc_type == "FACTURA":
            doc_type = "FACTURA ELECTRÓNICA"
            
        buffer.extend(BOLD_ON + text(doc_type + "\n") + BOLD_OFF)
        
        doc_number = sale[4] or ""
        if doc_number:
            buffer.extend(text(f"{doc_number}\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
            
        # --- EMISSION INFO ---
        buffer.extend(text(f"EMISIÓN: {sale[0]}\n"))
        
        customer_doc = sale[6] or ""
        if customer_doc:
            label = "RUC" if len(customer_doc) == 11 else "DNI"
            buffer.extend(text(f"{label}: {customer_doc}\n"))
            
        customer_name = sale[5] or ""
        if customer_name:
            buffer.extend(text(f"CLIENTE: {customer_name}\n"))
            
        is_proforma = "NOTA DE VENTA" in doc_type.upper()
        
        if not is_proforma:
            buffer.extend(text("MONEDA: SOL(PEN)\n"))
            buffer.extend(text("FORMA DE PAGO: CONTADO\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS ---
        buffer.extend(ALIGN_CENTER)
        header = "PRODUCTO      PESO    P.UNIT   P.TOTAL"
        buffer.extend(BOLD_ON + text(header + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        for item in details:
            # item: name, quantity, price, subtotal, unit_of_measure
            buffer.extend(ALIGN_LEFT)
            desc = item[0]
            desc_lines = textwrap.wrap(desc, width=40)
            for line in desc_lines:
                buffer.extend(text("  " + line + "\n"))
            
            buffer.extend(ALIGN_CENTER)
            qty_um = f"{item[1]:.2f} {item[4][:3]}"
            price = f"{item[2]:.2f}"
            subtotal = f"{item[3]:.2f}"
            
            line2 = f"{qty_um}".center(16) + f"{price}".rjust(10) + f"{subtotal}".rjust(16)
            buffer.extend(text(line2 + "\n"))
            buffer.extend(text("." * 42 + "\n"))
            
        # --- TOTALS ---
        buffer.extend(ALIGN_CENTER)
        total_val = sale[1]
        
        if not is_proforma:
            subtotal = total_val / 1.18
            igv = total_val - subtotal
            
            buffer.extend(text(f"Total Op.Gravadas: S/ {subtotal:.2f}\n"))
            buffer.extend(text(f"Total I.G.V 18%:   S/ {igv:.2f}\n"))
            
        # TOTAL A PAGAR
        total_str = f"TOTAL A PAGAR: S/ {total_val:,.2f}"
        buffer.extend(SIZE_2X + INVERSE_ON + text(total_str.center(21) + "\n") + INVERSE_OFF + SIZE_NORMAL)
        
        # Amount in letters
        total_letras = self._number_to_text(total_val)
        letras_lines = textwrap.wrap(total_letras, width=42)
        for line in letras_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- FOOTER ---
        if not is_proforma:
            buffer.extend(text(f"Representación Impresa de la\n"))
            buffer.extend(text(f"{doc_type}.\n"))
            buffer.extend(text("Consultar su validez en https://shorturl.at/WoJnM\n"))
            
            if issuer_name:
                ruc_emisor = ruc
                tipo_cpe = "01" if "FACTURA" in doc_type else "03" if "BOLETA" in doc_type else "00"
                
                serie = ""
                numero = ""
                if "-" in doc_number:
                    serie, numero = doc_number.split("-")
                
                fecha = sale[0].split(" ")[0] if " " in sale[0] else sale[0]
                total_qr = f"{total_val:.2f}"
                igv_qr = f"{(total_val - (total_val/1.18)):.2f}"
                
                qr_content = f"{ruc_emisor}|{tipo_cpe}|{serie}|{numero}|{igv_qr}|{total_qr}|{fecha}|6|{customer_doc}|HASH_DUMMY|"
                
                try:
                    qr = qrcode.QRCode(version=1, box_size=10, border=1)
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    
                    buffer.extend(text("\n"))
                    qr_bytes = self._get_escpos_image_bytes(qr_img, max_width=250)
                    buffer.extend(qr_bytes)
                except Exception as e:
                    print(f"Error generando QR: {e}")
                    buffer.extend(text("[ERROR QR]\n"))

                buffer.extend(text(f"Resumen: HASH_DUMMY_VALUE\n"))
                

        buffer.extend(text("-" * 42 + "\n"))

        # Bank Accounts
        bank_accounts = sale[14]
        if bank_accounts:
            ba_lines = textwrap.wrap(bank_accounts, width=25)
            for line in ba_lines:
                buffer.extend(SIZE_2H + text(line + "\n") + SIZE_NORMAL)
            
        # Final Greeting
        final_greeting = sale[16]
        if final_greeting:
             buffer.extend(text("\n"))
             greeting_lines = textwrap.wrap(final_greeting, width=42)
             for line in greeting_lines:
                 buffer.extend(text(line + "\n"))
                
        buffer.extend(CUT)
        return buffer

    def reprint_ticket(self):
        if win32print is None:
            messagebox.showerror("Error de Impresión", "El módulo 'pywin32' es necesario para imprimir. Por favor, instálelo.", parent=self)
            return
        printer_name = config_manager.load_setting('default_printer')
        if not printer_name:
            messagebox.showwarning("Impresora no Configurada", "Por favor, seleccione una impresora por defecto en el módulo de Configuración.", parent=self)
            return
        
        if "MICROSOFT PRINT TO PDF" in printer_name.upper():
            messagebox.showerror(
                "Impresora no Compatible",
                "La impresora 'Microsoft Print to PDF' no es compatible con la impresión de tickets en formato RAW.\n"
                "Por favor, seleccione una impresora térmica real para imprimir tickets.",
                parent=self
            )
            return
        
        try:
            data_to_send = self._generate_escpos_ticket()
            if not data_to_send:
                messagebox.showerror("Error", "No hay datos para imprimir.", parent=self)
                return

            h_printer = win32print.OpenPrinter(printer_name)
            try:
                h_job = win32print.StartDocPrinter(h_printer, 1, ("Reimpresión Ticket", None, "RAW"))
                try:
                    win32print.StartPagePrinter(h_printer)
                    win32print.WritePrinter(h_printer, data_to_send)
                    win32print.EndPagePrinter(h_printer)
                finally:
                    win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
            messagebox.showinfo("Impresión", "El ticket ha sido enviado a la impresora.", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Impresión", f"No se pudo imprimir el ticket.\nError: {e}", parent=self)