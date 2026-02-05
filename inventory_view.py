import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont # Added ImageDraw, ImageFont
import io
import database
import random
import string
import json
import config_manager
import utils
import textwrap
from datetime import datetime
try:
    import pandas as pd
except ImportError:
    pd = None

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
        self._font_args = font_args or ("Roboto", 11, "bold")
        self._height_val = height
        
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
        
        # Colors based on state
        c1, c2 = self._color1, self._color2
        if self._is_pressed:
            # Darken
            c1 = c2
        elif self._is_hovering:
            pass

        # Create Image with PIL
        # 1. Create a transparent image
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Linear Gradient generation
        base = Image.new('RGBA', (width, height), c1)
        top = Image.new('RGBA', (width, height), c2)
        mask = Image.new('L', (width, height))
        mask_data = []
        for y in range(height):
            mask_data.extend([int(255 * (y / height))] * width)
        mask.putdata(mask_data)
        
        # Paste top onto base with mask -> Vertical Gradient
        base.paste(top, (0, 0), mask)
        gradient_img = base
        
        # 3. Apply Mask only if radius > 0
        if self.corner_radius > 0:
            mask_img = Image.new('L', (width, height), 0)
            draw_mask = ImageDraw.Draw(mask_img)
            draw_mask.rounded_rectangle((0, 0, width, height), radius=self.corner_radius, fill=255)
            
            final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            final_img.paste(gradient_img, (0, 0), mask_img)
        else:
            final_img = gradient_img
        
        # 5. Draw Text & Icon
        # Need to draw text on top using PIL for best antialiasing or use Canvas text?
        # Canvas text is easier to center and manage fonts.
        
        self.image_ref = ImageTk.PhotoImage(final_img)
        self.delete("all")
        self.create_image(0, 0, image=self.image_ref, anchor='nw')
        
        # Text/Icon
        full_text = f"{self.icon} {self.text}"
        self.create_text(width//2, height//2, text=full_text, fill=self._text_color, font=self._font_args) # "Roboto 11 bold"

    def set_state(self, state):
        if state == "disabled":
            self._is_pressed = False
            self.bind('<Button-1>', lambda e: "break")
            self.bind('<ButtonRelease-1>', lambda e: "break")
            self.bind('<Enter>', lambda e: "break")
            self.bind('<Leave>', lambda e: "break")
            # Gray out
            self._original_color1 = self._color1
            self._original_color2 = self._color2
            self._color1 = "#cccccc"
            self._color2 = "#999999"
            self._draw(self.winfo_width(), self.winfo_height())
        elif state == "normal":
            self.bind('<Button-1>', self._on_press)
            self.bind('<ButtonRelease-1>', self._on_release)
            self.bind('<Enter>', self._on_enter)
            self.bind('<Leave>', self._on_leave)
            # Restore
            if hasattr(self, '_original_color1'):
                self._color1 = self._original_color1
                self._color2 = self._original_color2
            self._draw(self.winfo_width(), self.winfo_height())

class GradientFrame(tk.Canvas):
    def __init__(self, parent, color1, color2, **kwargs):
        super().__init__(parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self.bind('<Configure>', self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete('gradient')
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

try:
    import win32print
except ImportError:
    win32print = None

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, COLOR_BUTTON_PRIMARY, COLOR_BUTTON_SECONDARY, FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HEADER

COLOR_PRIMARY_DARK = COLOR_PRIMARY
COLOR_SECONDARY_DARK = COLOR_SECONDARY
COLOR_ACCENT_BLUE = COLOR_ACCENT
COLOR_TEXT_LIGHT = COLOR_TEXT

class InventoryView(ttk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Gestión de Inventario y Servicios")
        self.state('zoomed')
        
        # Import Colors from HTML spec
        is_dark = "Dark" in config_manager.load_setting("system_theme", "Dark")

        # Import Colors from HTML spec (Dynamic)
        HTML_NAVY = '#0a2240'
        
        if is_dark:
             HTML_BG = COLOR_PRIMARY_DARK # e.g. #181A1B
             HTML_WHITE = COLOR_SECONDARY_DARK # e.g. #252A2E
             HTML_BLUE = '#0d6efd' # Brighter blue for dark mode
             HTML_RED = '#dc3545'
             HTML_BORDER = '#444444' # Dark gray border
             TEXT_ON_CARD = COLOR_TEXT_LIGHT
             HEADER_FG = 'white'
        else:
             HTML_BG = '#f0f2f5'
             HTML_WHITE = '#ffffff'
             HTML_BLUE = '#007bff'
             HTML_RED = '#dc3545'
             HTML_BORDER = '#999999'
             TEXT_ON_CARD = '#333333'
             HEADER_FG = 'white'
        
        self.configure(background=HTML_BG)
        
        # --- Loading Data Steps (Initialized early for filters) ---
        self.filter_issuer_var = tk.StringVar(value="Todas") 
        self.filter_address_var = tk.StringVar(value="Todas")
        self.image_data = None
        
        style = ttk.Style.get_instance()
        
        # --- HTML-Like Styles ---
        # Header
        style.configure('HtmlHeader.TFrame', background=HTML_NAVY)
        style.configure('HtmlHeader.TLabel', background=HTML_NAVY, foreground='white', font=(FONT_FAMILY, 14, 'bold'))
        style.configure('HtmlSubHeader.TLabel', background=HTML_NAVY, foreground='white', font=(FONT_FAMILY, 10))

        # Main Card
        style.configure('HtmlCard.TFrame', background=HTML_WHITE)
        style.configure('HtmlCard.TLabel', background=HTML_WHITE, foreground=TEXT_ON_CARD, font=(FONT_FAMILY, 10, 'bold'))
        
        # Inputs (Rounded Clean Look)
        # Helper to create rounded border images
        def create_rounded_element(name, color, border_color, width=150, height=30, radius=10, image_name=None):
            # Create high-res image for anti-aliasing (optional, but 1x is usually fine for widget bg)
            # Actually with ttk elements, slicing is key.
            # We create a fixed size image and use it as a 9-slice.
            w, h = 60, 30 # Enough to have corners and center
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw rounded rect with border
            # Draw border first (slightly larger or same size?)
            # Draw fill
            
            # Using pieslice/rectangle manual method for exact control or rounded_rectangle
            
            # Border
            draw.rounded_rectangle((0, 0, w-1, h-1), radius=radius, fill=color, outline=border_color, width=1)
            
            if image_name:
                 return ImageTk.PhotoImage(img, name=image_name)
            return ImageTk.PhotoImage(img)

        bg_input = "#2c3e50" if is_dark else HTML_WHITE # Dark input background if dark mode
        fg_input = "white" if is_dark else "black"

        self.img_rounded_field = create_rounded_element("field", bg_input, HTML_BORDER, image_name="img_rounded_field_common")
        self.img_rounded_focus = create_rounded_element("focus", bg_input, HTML_BLUE, image_name="img_rounded_focus_common") # Focus state
        
        # Register Elements
        try:
             style.element_create("Rounded.field", "image", self.img_rounded_field,
                                  ('focus', self.img_rounded_focus),
                                  border=10, sticky="ewns")
        except tk.TclError:
             pass # Already exists

        # Configure Entry Style
        style.layout('HtmlEntry.TEntry', [
            ('Rounded.field', {'sticky': 'nswe', 'children': [
                ('Entry.padding', {'sticky': 'nswe', 'children': [
                    ('Entry.textarea', {'sticky': 'nswe'})
                ]})
            ]})
        ])
        style.configure('HtmlEntry.TEntry', padding=5, foreground=fg_input) # Padding inside the border
        
        # Configure Combobox Style
        # Combobox needs the arrow. We can reuse Rounded.field as the background.
        # But we need the layout to include the arrow.
        style.layout('HtmlEntry.TCombobox', [
             ('Rounded.field', {'sticky': 'nswe', 'children': [
                  ('Combobox.padding', {'sticky': 'nswe', 'children': [
                       ('Combobox.textarea', {'sticky': 'nswe'}),
                       ('Combobox.arrow', {'side': 'right', 'sticky': 'ns'})
                  ]})
             ]})
        ])
        style.configure('HtmlEntry.TCombobox', padding=5)
        style.map('HtmlEntry.TCombobox', 
                  fieldbackground=[('readonly', bg_input)],
                  selectbackground=[('readonly', '#007bff')],
                  selectforeground=[('readonly', 'white')],
                  foreground=[('readonly', fg_input)]) # Ensure text is visible

        # Buttons (Modern Rounded - utilizing bootstyle primary/danger)
        # We will use 'primary' (Blue) and 'danger' (Red) directly in widget creation for rounded look.
        # Custom styles below are for specific overrides if needed, but bootstyle gives the best "modern rounded" shape.
        
        style.configure('HtmlPrint.TButton', background=HTML_NAVY, foreground='white', font=(FONT_FAMILY, 8), borderwidth=0)
        style.map('HtmlPrint.TButton', background=[('active', '#0a2240')]) 

        # Table (Borderless)
        style.configure("Html.Treeview.Heading", background=HTML_NAVY, foreground="white", font=(FONT_FAMILY, 9, "bold"))
        style.map("Html.Treeview.Heading", background=[('active', HTML_NAVY)])
        style.configure("Html.Treeview", font=(FONT_FAMILY, 9), rowheight=28, borderwidth=0, relief="flat")
        style.layout("Html.Treeview", [('Html.Treeview.treearea', {'sticky': 'nswe'})]) # Remove borders from layout if present

        # Footer
        style.configure('HtmlFooter.TFrame', background=HTML_WHITE)
        style.configure('HtmlStat.TLabel', background=HTML_WHITE, foreground='#aaaaaa' if is_dark else '#555555', font=(FONT_FAMILY, 9))       # Label (Normal)
        style.configure('HtmlStatBold.TLabel', background=HTML_WHITE, foreground=TEXT_ON_CARD, font=(FONT_FAMILY, 10, 'bold')) # Value (Bold)

        # --- LAYOUT ---
        
        # 1. Header Bar (Gradient)
        header = GradientFrame(self, HTML_NAVY, HTML_BLUE, height=60)
        header.pack(fill='x')
        header.create_text(20, 30, text="Almacén", fill="white", anchor="w", font=(FONT_FAMILY, 20, 'bold'))

        # 2. Main Wrapper (Gray BG, Padding)
        main_wrapper = ttk.Frame(self, style='TFrame') # Uses default root bg (light gray)
        style.configure('TFrame', background=HTML_BG) # Ensure default is gray
        main_wrapper.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 3. White Card Container
        card = ttk.Frame(main_wrapper, style='HtmlCard.TFrame')
        card.pack(fill='both', expand=True) # Inner white card
        
        # --- FILTERS (Emisor / Dirección) ---
        filters_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=(10, 5))
        filters_frame.pack(fill='x')
        
        ttk.Label(filters_frame, text="Emisor:", style='HtmlCard.TLabel').pack(side='left', padx=(0, 5))
        self.filter_issuer_combo = ttk.Combobox(filters_frame, textvariable=self.filter_issuer_var, state="readonly", width=30, style='HtmlEntry.TCombobox')
        self.filter_issuer_combo.pack(side='left', padx=(0, 20))
        self.filter_issuer_combo.bind("<<ComboboxSelected>>", lambda e: self.on_filter_issuer_change(e))
        
        ttk.Label(filters_frame, text="Dirección:", style='HtmlCard.TLabel').pack(side='left', padx=(0, 5))
        self.filter_address_combo = ttk.Combobox(filters_frame, textvariable=self.filter_address_var, state="readonly", width=40, style='HtmlEntry.TCombobox')
        self.filter_address_combo.pack(side='left')
        self.filter_address_combo.bind("<<ComboboxSelected>>", lambda e: self.populate_products_list())
        
        # Excel Buttons
        btn_template = ttk.Button(filters_frame, text="Plantilla Excel", command=self.generate_excel_template, bootstyle="success-outline")
        btn_template.pack(side='left', padx=(20, 5))
        
        btn_import = ttk.Button(filters_frame, text="Importar Excel", command=self.import_from_excel, bootstyle="info-outline")
        btn_import.pack(side='left', padx=5)
        
        # --- FORM SECTION (Top of Card) ---
        form_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=10)
        form_frame.pack(fill='x')
        form_frame.columnconfigure(0, weight=1) # Left Col
        form_frame.columnconfigure(1, weight=1) # Right Col (smaller)
        
        # Grid Layout imitating the HTML Grid
        # Left Col: Fields
        # Grid Layout imitating the HTML Grid
        # Left Col: Fields (Nombre, Código, Precio, Grupo)
        left_col = ttk.Frame(form_frame, style='HtmlCard.TFrame')
        left_col.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        left_col.columnconfigure(1, weight=1)
        
        # Right Col: (U. Medida, Tipo Op, Imagen)
        right_col = ttk.Frame(form_frame, style='HtmlCard.TFrame')
        right_col.grid(row=0, column=1, sticky='nsew', padx=20)
        right_col.columnconfigure(1, weight=1)

        # --- LEFT COLUMN FIELDS ---
        l_row_idx = 0
        for label_text in ["Nombre:", "Código:", "Precio:", "Grupo:"]:
            ttk.Label(left_col, text=label_text, style='HtmlCard.TLabel', width=10, anchor='e').grid(row=l_row_idx, column=0, sticky='e', padx=5, pady=4)
            l_row_idx += 1
            
        # 1. Nombre
        self.name_var = ttk.StringVar()
        self._trace_uppercase(self.name_var)
        self.name_entry = ttk.Entry(left_col, textvariable=self.name_var, style='HtmlEntry.TEntry')
        self.name_entry.grid(row=0, column=1, sticky='ew', pady=4)
        
        # 2. Código + Auto
        code_frame = ttk.Frame(left_col, style='HtmlCard.TFrame')
        code_frame.grid(row=1, column=1, sticky='ew', pady=4)
        self.code_var = ttk.StringVar()
        self._trace_uppercase(self.code_var)
        self.code_entry = ttk.Entry(code_frame, textvariable=self.code_var, style='HtmlEntry.TEntry')
        self.code_entry.pack(side='left', fill='x', expand=True)
        self.generate_code_button = ttk.Button(code_frame, text="Auto", command=self.generate_unique_code, bootstyle="secondary-outline")
        self.generate_code_button.pack(side='left', padx=(5, 0))

        # 3. Precio
        self.price_var = ttk.DoubleVar()
        self.price_entry = ttk.Entry(left_col, textvariable=self.price_var, style='HtmlEntry.TEntry')
        self.price_entry.grid(row=2, column=1, sticky='ew', pady=4)
        
        # 4. Grupo (Moved from Row 4 to Row 3)
        self.category_var = ttk.StringVar()
        self._trace_uppercase(self.category_var)
        self.category_combo = ttk.Combobox(left_col, textvariable=self.category_var, style='HtmlEntry.TCombobox')
        self.category_combo.grid(row=3, column=1, sticky='ew', pady=4)


        # --- RIGHT COLUMN FIELDS ---
        r_row_idx = 0
        for label_text in ["U. Medida:", "Tipo Operación:", "Imagen:"]:
             ttk.Label(right_col, text=label_text, style='HtmlCard.TLabel', width=15, anchor='e').grid(row=r_row_idx, column=0, sticky='e', padx=5, pady=4)
             r_row_idx += 1

        # 1. U. Medida
        self.unit_of_measure_var = ttk.StringVar()
        self.unit_of_measure_combo = ttk.Combobox(right_col, textvariable=self.unit_of_measure_var, style='HtmlEntry.TCombobox')
        self.unit_of_measure_combo.grid(row=0, column=1, sticky='ew', pady=4)
        self.unit_of_measure_combo.bind("<KeyRelease>", self.filter_um_combo) # Changed from <Return> to <KeyRelease>
        self.unit_of_measure_combo.bind("<<ComboboxSelected>>", lambda e: self.name_entry.focus()) # Optional: move focus after selection
        
        # 2. Tipo Operación
        self.operation_type_var = ttk.StringVar(value="Gravada")
        self.operation_type_combo = ttk.Combobox(right_col, textvariable=self.operation_type_var, values=["Gravada", "Exonerada", "Inafecta", "Exportación"], state="readonly", style='HtmlEntry.TCombobox')
        self.operation_type_combo.grid(row=1, column=1, sticky='ew', pady=4)

        # 3. Imagen
        img_frame = ttk.Frame(right_col, style='HtmlCard.TFrame')
        img_frame.grid(row=2, column=1, sticky='ew', pady=4)
        self.select_image_btn = ttk.Button(img_frame, text="Seleccionar", command=self.select_image, bootstyle="secondary-outline")
        self.select_image_btn.pack(side='left')
        self.image_status_label = ttk.Label(img_frame, text="Sin imagen", font=(FONT_FAMILY, 9), foreground="#888", style='HtmlCard.TLabel')
        self.image_status_label.pack(side='left', padx=10)


        # --- ACTION BUTTONS (Row) ---
        actions_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=(10, 5))
        actions_frame.pack(fill='x')
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        
        # New (Blue) and Delete (Red) - 50% Width each
        # New and Delete (50% Width each)
        # Gradient Colors
        BLUE_START = '#007bff'
        BLUE_END = '#0056b3'
        
        RED_START = '#dc3545'
        RED_END = '#bd2130'
        
        self.add_btn = GradientButton(actions_frame, text="Nuevo", icon="✚", color1=BLUE_START, color2=BLUE_END, command=self.add_product, height=45)
        self.add_btn.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        
        self.delete_btn = GradientButton(actions_frame, text="Eliminar", icon="🗑", color1=RED_START, color2=RED_END, command=self.delete_product, height=45)
        self.delete_btn.grid(row=0, column=1, sticky='ew')
        
        # --- TABLE ---
        # --- FOOTER (Gradient Blue) ---
        # Using Gradient from HTML_NAVY to HTML_BLUE
        footer = GradientFrame(card, HTML_NAVY, HTML_BLUE, height=50, highlightthickness=0)
        footer.pack(fill='x', side='bottom')
        footer_frame = footer # Patch for label reference compatibility
        
        # Style update for White Text on Dark Background
        style.configure('HtmlStat.TLabel', background=HTML_NAVY, foreground='white', font=(FONT_FAMILY, 10))
        style.configure('HtmlStatBold.TLabel', background=HTML_NAVY, foreground='white', font=(FONT_FAMILY, 10, 'bold'))
        
        # Helper to treat Canvas as frame for packing transparency workaround
        # Since standard labels have backgrounds, we create a transparent-like effect
        # by matching the label background to the gradient start color (approximation)
        # or using standard labels on top. 
        # Ideally, we place items or use a transparent container, but Tkinter labels aren't transparent.
        # Workaround: Use a Frame *inside* the canvas? No, that hides the gradient.
        # Solution: Use `create_window` on the canvas for better control, or just pack with approximate bg match.
        # Given strict gradient request, let's use `place` or `pack` but set label bg to matching average color? 
        # Actually, simpler: Set label background to one of the colors (e.g. Navy) 
        # and accept it might not perfectly match the gradient pixel-perfectly, 
        # OR use a solid color footer frame if gradient is too glitchy with labels on top.
        # HOWEVER, User ASKED for gradient.
        # Better visual hack: Set Label background to '' (system transparent) if supported? No on Windows.
        # Let's try matching the Start Color (Navy) for the labels and pack them left.
        
        container = ttk.Frame(footer, style='HtmlFooter.TFrame') # Container needs to be transparent... impossible in standard ttk.
        # OK, PLAN B: Draw text directly on Canvas? 
        # Hard to manage layout.
        # PLAN C: Use a standard Frame with a Background Image?
        # PLAN D (Best for Tkinter): Just use a Frame with a SOLID Color (Gradient is very hard to make labels transparent over).
        # WAITING: User asked for "Sombreado de azul con degradado".
        # Let's try the GradientFrame but use `create_window` to place widgets, 
        # and acknowledge labels will have a solid background. 
        # To make it look good, we can make the labels have the SAME background as the LEFT side of gradient (Navy).
        
        # Redefining GradientFrame slightly to manage layout
        # Or... Just use a colored frame and tell user gradient text background issue.
        # Let's try simply putting the widgets into the canvas using create_window.
        
        # Adjusted implementation:
        
        # Widget container (transparent-ish behavior via placement)
        # We will pack a frame 'inside' but we can't make it transparent.
        # CRITICAL: Tkinter labels have solid backgrounds.
        # If I want a smooth gradient behind text, I must use `canvas.create_text`.
        
        # Let's render text directly on canvas!
        # And for the button, use create_window.
        
        # Products
        x_pos = 20
        y_pos = 25 # Center vertically (height=50)
        
        footer.create_text(x_pos, y_pos, text="📦 Productos: ", fill="white", anchor="w", font=(FONT_FAMILY, 11))
        x_pos += 100
        self.total_products_val_id = footer.create_text(x_pos, y_pos, text="0", fill="white", anchor="w", font=(FONT_FAMILY, 11, 'bold'))
        x_pos += 55
        
        # Groups
        footer.create_text(x_pos, y_pos, text="📂 Grupos: ", fill="white", anchor="w", font=(FONT_FAMILY, 11))
        x_pos += 90
        self.total_groups_val_id = footer.create_text(x_pos, y_pos, text="0", fill="white", anchor="w", font=(FONT_FAMILY, 11, 'bold'))
        x_pos += 55
        
        # Stock
        footer.create_text(x_pos, y_pos, text="📊 Stock Total: ", fill="white", anchor="w", font=(FONT_FAMILY, 11))
        x_pos += 115
        self.total_stock_val_id = footer.create_text(x_pos, y_pos, text="0.00", fill="white", anchor="w", font=(FONT_FAMILY, 11, 'bold'))
        x_pos += 95
        
        # Value
        footer.create_text(x_pos, y_pos, text="💰 Valorizado Total: ", fill="white", anchor="w", font=(FONT_FAMILY, 11))
        x_pos += 145
        self.total_value_val_id = footer.create_text(x_pos, y_pos, text="S/ 0.00", fill="white", anchor="w", font=(FONT_FAMILY, 11, 'bold'))

        # Print Button (Right aligned)
        # Using create_window
        # Print Button (Right aligned)
        # Using create_window
        # Using GradientButton for "Imprimir"
        # Color: #0a2240 (Navy)
        # Background: #007bff (Blue - to match Footer end)
        NAVY_SOLID = '#0a2240'
        FOOTER_END_BLUE = '#007bff'
        
        self.print_btn = GradientButton(footer, text="🖨 Imprimir", icon="", color1=NAVY_SOLID, color2=NAVY_SOLID, command=self.print_inventory, height=35, width=120, bg=FOOTER_END_BLUE, corner_radius=0)
        
        def place_button(event):
             w = footer.winfo_width()
             # Adjust position to be right aligned, ensuring it doesn't overlap
             footer.coords('print_btn', w - 80, 25)
             
        footer.bind('<Configure>', lambda e: (footer._draw_gradient(e), place_button(e)))
        footer.create_window(1000, 25, window=self.print_btn, anchor="center", tags="print_btn")
        
        # For compatibility with populate function updating values:
        # We need a way to update the text items.
        # We'll store the canvas and IDs and update `config` calls to `itemconfigure`.
        self.footer_canvas = footer
        
        tree_container = ttk.Frame(card, style='HtmlCard.TFrame', padding=10)
        tree_container.pack(fill='both', expand=True)
        
        # Table Header Styling with Rounded Extremes
        # We need three images: Center (Square), Left (Round Top-Left), Right (Round Top-Right)
        img_h = 35
        # The width doesn't matter much as it stretches, but let's give it some width
        img_w = 40
        
        # Gradient colors
        def hex_to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        c1 = hex_to_rgb(HTML_NAVY)
        c2 = hex_to_rgb(HTML_BLUE)

        def create_header_img(radius_corners=[]):
            # radius_corners: list of corners to round 'tl', 'tr', 'bl', 'br'
            # Here we only care about top corners for headers
            img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw solid color on a temporary image
            grad = Image.new('RGBA', (img_w, img_h), c1 + (255,)) # c1 is HTML_NAVY rgb tuple, add alpha
            
            # If no radius, return solid image
            if not radius_corners:
                return grad
            
            # Create mask for rounded corners
            mask = Image.new('L', (img_w, img_h), 255)
            m_draw = ImageDraw.Draw(mask)
            
            r = 10 # Radius
            
            # Draw black rectangles on corners to be transparent, then draw white circles
            # Actually easier: Draw white rounded rect on black background? 
            # No, standard is white mask = opaque.
            
            # Let's start with full white (opaque) and cut out corners if needed?
            # Better: Draw a rounded rectangle on the mask from 0,0 to w,h.
            # But we only want specific corners rounded.
            
            # Clear mask to black (transparent)
            # m_draw.rectangle((0, 0, img_w, img_h), fill=0)
            # Draw main rect
            # m_draw.rectangle((0, 0, img_w, img_h), fill=255) 
            
            # To mask ONLY the corners out, we can draw black on the corners and then fill back?
            # Standard rounding:
            
            # Top Left
            if 'tl' in radius_corners:
                 m_draw.rectangle((0, 0, r, r), fill=0) # Cut corner
                 m_draw.pieslice((0, 0, r*2, r*2), 180, 270, fill=255) # Add round
                 
            # Top Right
            if 'tr' in radius_corners:
                 m_draw.rectangle((img_w-r, 0, img_w, 0+r), fill=0)
                 m_draw.pieslice((img_w-2*r, 0, img_w, r*2), 270, 360, fill=255)
                 
            # Apply mask to gradient
            grad.putalpha(mask)
            return grad

        # Create Images
        self.img_header_center_pil = create_header_img([])
        self.img_header_left_pil = create_header_img(['tl'])
        self.img_header_right_pil = create_header_img(['tr'])
        
        self.img_header_center = ImageTk.PhotoImage(self.img_header_center_pil)
        self.img_header_left = ImageTk.PhotoImage(self.img_header_left_pil)
        self.img_header_right = ImageTk.PhotoImage(self.img_header_right_pil)

        # Apply General Style (Center)
        style.configure("Html.Treeview.Heading", image=self.img_header_center, background=HTML_NAVY, foreground="white", font=(FONT_FAMILY, 9, "bold"), borderwidth=0)
        style.map("Html.Treeview.Heading", background=[('active', HTML_NAVY)], relief=[('pressed', 'flat'), ('active', 'flat')])
        
        style.configure("Html.Treeview", 
                        background=HTML_WHITE, 
                        fieldbackground=HTML_WHITE, 
                        foreground=TEXT_ON_CARD, 
                        font=(FONT_FAMILY, 9), 
                        rowheight=28, 
                        borderwidth=0, 
                        relief="flat")
        
        self.tree = ttk.Treeview(tree_container, columns=("ID", "Código", "Categoría", "Nombre", "Precio", "Stock", "Valorizado", "U. Medida", "Tipo Op.", "Emisor", "Dirección"), show="headings", style="Html.Treeview")
        
        # Columns
        headers = [("ID", 50), ("Código", 80), ("Categoría", 100), ("Nombre", 250), ("Precio", 80), ("Stock", 60), ("Valorizado", 90), ("U. Medida", 70), ("Tipo Op.", 80), ("Emisor", 100), ("Dirección", 100)]
        
        for i, (col, width) in enumerate(headers):
            # Determine Image
            if i == 0:
                img = self.img_header_left
            elif i == len(headers) - 1:
                img = self.img_header_right
            else:
                img = self.img_header_center
                
            self.tree.heading(col, text=col.upper(), image=img, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=width)
            if col in ["Precio", "Valorizado", "Stock"]: self.tree.column(col, anchor='e')
        
        self.tree["displaycolumns"] = ("Código", "Categoría", "Nombre", "Precio", "Stock", "Valorizado", "U. Medida", "Tipo Op.", "Emisor", "Dirección")
        
        sb_style = "secondary-round" if is_dark else "default"
        scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.tree.yview, bootstyle=sb_style)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # --- Loading Data Steps ---
        # Variables initialized at top of __init__
        self.load_units_of_measure()
        self.load_categories()
        self.load_issuers_for_filter()

        # Tags
        self.tree.tag_configure('stock_negative', foreground='#dc3545') 
        self.tree.tag_configure('stock_zero', foreground='#ffc107')
        
        if is_dark:
             self.tree.tag_configure('evenrow', background='#2a2e33') # Dark Alternate
             self.tree.tag_configure('oddrow', background=HTML_WHITE) # Dark Base
        else:
             self.tree.tag_configure('evenrow', background='#f8f9fa')
             self.tree.tag_configure('oddrow', background='#ffffff')
        


        self.populate_products_list()
        self.clear_fields() # Set defaults (like Unit of Measure)
        self.name_entry.focus_set()

    def _trace_uppercase(self, string_var):
        def to_uppercase(*args):
            s = string_var.get()
            if s != s.upper():
                string_var.set(s.upper())
        string_var.trace_add('write', to_uppercase)

    def load_units_of_measure(self):
        try:
            with open(utils.resource_path('unidades_medida.json'), 'r', encoding='utf-8') as f:
                self.units_data = json.load(f)
            
            self.um_description_to_code = {item['descripcion']: item['codigo_sunat'] for item in self.units_data}
            self.um_code_to_description = {item['codigo_sunat']: item['descripcion'] for item in self.units_data}
            self.um_descriptions = sorted(list(self.um_description_to_code.keys()))
            
            # Initial Population of dropdown
            if hasattr(self, 'unit_of_measure_combo'):
                self.unit_of_measure_combo['values'] = self.um_descriptions
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar 'unidades_medida.json'.\n{e}", parent=self)
            self.units_data = []
            self.um_description_to_code = {}
            self.um_code_to_description = {}
            self.um_descriptions = []

    def filter_um_combo(self, event):
        # Allow navigation keys to work normally
        if event.keysym in ['Up', 'Down', 'Return', 'ISO_Left_Tab', 'Tab']:
            return

        typed = self.unit_of_measure_combo.get()
        cursor_pos = self.unit_of_measure_combo.index(tk.INSERT)
        
        if not typed:
            self.unit_of_measure_combo['values'] = self.um_descriptions
        else:
            filtered = [item for item in self.um_descriptions if typed.lower() in item.lower()]
            self.unit_of_measure_combo['values'] = filtered
            
            # Open dropdown only if there are results
            # NOTE: We avoid event_generate('<Down>') on every keystroke because it can select text 
            # or interfere with typing. We just update values.
            # If user wants to see list, they can press Down.
            if filtered:
                 # Attempt to keep list open without stealing focus/selection if possible
                 # verify if list is already open? Tkinter difficult.
                 # Safer: Only update values. User presses Down to choose.
                 pass
                 
        # Restore cursor position (updating values might reset it)
        try:
            self.unit_of_measure_combo.icursor(cursor_pos)
        except:
            pass

    def load_issuers_for_filter(self):
        # Build structure similar to SalesView: Name -> List of Data
        all_issuers_raw = database.get_all_issuers()
        self.issuers_map = {}
        
        for row in all_issuers_raw:
            # row structure: id, name, ruc, address, ...
            # We only need: id, name, address
            i_id, name, ruc, address = row[0], row[1], row[2], row[3]
            if name not in self.issuers_map:
                self.issuers_map[name] = []
            self.issuers_map[name].append({'id': i_id, 'name': name, 'address': address})
            
        # Sort issuers
        issuers_list = sorted(list(self.issuers_map.keys()))
        
        # Add "Todas" for Inventory context
        self.filter_issuer_combo['values'] = ["Todas"] + issuers_list
        
        # Load persistence
        last_issuer = config_manager.load_setting("last_inventory_issuer", "Todas")
        last_address = config_manager.load_setting("last_inventory_address", "Todas")
        
        if last_issuer in self.filter_issuer_combo['values']:
            self.filter_issuer_var.set(last_issuer)
            # Find addresses for this issuer
            self.on_filter_issuer_change(save=False) # Populate addresses
            
            if last_address in self.filter_address_combo['values']:
                self.filter_address_var.set(last_address)
            else:
                self.filter_address_var.set("Todas")
        else:
            self.filter_issuer_var.set("Todas")
            self.on_filter_issuer_change(save=False)
            
        # Initial populate
        self.populate_products_list()

    def on_filter_issuer_change(self, event=None, save=True):
        selected_issuer = self.filter_issuer_var.get()
        
        if selected_issuer == "Todas":
            self.filter_address_combo['values'] = ["Todas"]
            self.filter_address_var.set("Todas")
        else:
            # Get addresses from map
            if selected_issuer in self.issuers_map:
                addresses = sorted([i['address'] for i in self.issuers_map[selected_issuer]])
                
                if len(addresses) == 1:
                    # Case: Only 1 address -> Auto-select it, no "Todas" needed (as it's the same)
                    self.filter_address_combo['values'] = addresses
                    self.filter_address_var.set(addresses[0])
                else:
                    # Case: Multiple addresses -> Add "Todas", default to "Todas" if no valid persistence
                    self.filter_address_combo['values'] = ["Todas"] + addresses
                    
                    # check if current/persisted value is valid for this new list
                    current_val = self.filter_address_var.get()
                    if current_val in self.filter_address_combo['values']:
                         # Keep current if valid (e.g. during load)
                         pass 
                    else:
                        self.filter_address_var.set("Todas")
            else:
                self.filter_address_combo['values'] = ["Todas"]
                self.filter_address_var.set("Todas")
        
        if save:
            self.populate_products_list()

    def load_categories(self):
        categories = database.get_all_categories()
        self.category_combo['values'] = categories
        if not categories:
             self.category_var.set("OTROS")

    def populate_products_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        issuer_filter = self.filter_issuer_var.get()
        address_filter = self.filter_address_var.get()
        
        # Save persistence
        config_manager.save_setting("last_inventory_issuer", issuer_filter)
        config_manager.save_setting("last_inventory_address", address_filter)
        
        # Pass filters to database function
        products = database.get_all_products(issuer_filter, address_filter)
        
        total_stock = 0.0
        total_value = 0.0
        count = 0
        groups = set()

        for row in products:
            # row: id(0), name(1), price(2), stock(3), code(4), um(5), op(6), iss(7), addr(8), cat(9), img(10), active(11)
            is_active = row[11]
            # Ensure strict filtering
            if is_active == 0 or str(is_active) == '0':
                continue

            price = row[2]
            stock = row[3]
            category = row[9] or "OTROS"
            valorizado = price * stock
            
            total_stock += stock
            total_value += valorizado
            count += 1
            groups.add(category)
            
            display_row = (row[0], row[4], category, row[1], f"S/ {price:.2f}", f"{stock:,.2f}", f"S/ {valorizado:,.2f}", row[5], row[6], row[7] or "Global", row[8] or "Global")
            
            tag = ""
            if stock < 0:
                tag = "stock_negative"
            elif stock == 0:
                tag = "stock_zero"
            
            # Row Striping
            row_tag = "evenrow" if count % 2 == 0 else "oddrow"
            
            # Combine tags
            final_tags = (tag, row_tag) if tag else (row_tag,)
                
            self.tree.insert("", "end", values=display_row, tags=final_tags)
            
        # Update Canvas Text Items
        if hasattr(self, 'footer_canvas'):
            self.footer_canvas.itemconfigure(self.total_products_val_id, text=f"{count}")
            self.footer_canvas.itemconfigure(self.total_groups_val_id, text=f"{len(groups)}")
            self.footer_canvas.itemconfigure(self.total_stock_val_id, text=f"{total_stock:,.2f}")
            self.footer_canvas.itemconfigure(self.total_value_val_id, text=f"S/ {total_value:,.2f}")

    def add_product(self):
        name = self.name_var.get().strip()
        code = self.code_var.get().strip()
        unit_of_measure_desc = self.unit_of_measure_var.get().strip()
        operation_type = self.operation_type_var.get().strip()
        operation_type = self.operation_type_var.get().strip()
        category = self.category_var.get().strip()
        if not category:
            category = "OTROS"
            self.category_var.set(category)
        try:
            price = self.price_var.get()
            stock = 0.0 # Always 0 for new products
        except ttk.TclError:
            messagebox.showerror("Error de Datos", "El precio debe ser un número válido.", parent=self)
            return

        issuer_name = self.filter_issuer_var.get()
        issuer_address = self.filter_address_var.get()
        
        if issuer_name == "Todas":
            messagebox.showwarning("Seleccionar Emisor", "Por favor, seleccione una Empresa en el filtro para asignar el nuevo producto.", parent=self)
            return

        if issuer_address == "Todas":
             messagebox.showwarning("Seleccionar Dirección", "Por favor, seleccione una Dirección específica para asignar el nuevo producto.", parent=self)
             return

        if code and not database.is_code_unique(code):
            messagebox.showerror("Error de Validación", f"El código '{code}' ya existe. Por favor use un código único.", parent=self)
            return

        if name and price >= 0 and unit_of_measure_desc:
            try:
                # Map Description -> Code
                um_code = self.um_description_to_code.get(unit_of_measure_desc, unit_of_measure_desc)
                database.add_product(name, price, stock, code, um_code, operation_type, issuer_name, issuer_address, category, image=self.image_data)
                messagebox.showinfo("Éxito", "Producto añadido correctamente.", parent=self)
                self.load_categories() # Recargar categorías por si se agregó una nueva
                self.populate_products_list()
                self.clear_fields()
            except Exception as e:
                messagebox.showerror("Error de Base de Datos", f"No se pudo añadir el producto. El nombre o código ya podría existir para esta empresa/dirección.\n\nError: {e}", parent=self)
        else:
            messagebox.showerror("Datos Incompletos", "Los campos 'Nombre', 'Precio' y 'U. Medida' son obligatorios.", parent=self)

    def update_product(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Sin Selección", "Por favor, seleccione un producto para actualizar.", parent=self)
            return
        
        product_id = self.tree.item(selected_item)["values"][0]
        name = self.name_var.get().strip()
        code = self.code_var.get().strip()
        unit_of_measure_desc = self.unit_of_measure_var.get().strip()
        operation_type = self.operation_type_var.get().strip()
        category = self.category_var.get().strip()
        try:
            price = self.price_var.get()
            stock = self.stock_var.get()
        except ttk.TclError:
            messagebox.showerror("Error de Datos", "El precio y el stock deben ser números válidos.", parent=self)
            return

        # Retrieve current issuer and address from the selected item in the treeview
        values = self.tree.item(selected_item)['values']
        # values indices: 0=ID, 1=Code, 2=Name, 3=Price, 4=Stock, 5=UM, 6=OpType, 7=Issuer, 8=Address
        current_issuer = values[7]
        current_address = values[8]
        
        # Convert "Global" back to None if it was originally None in the database
        if current_issuer == "Global": current_issuer = None
        if current_address == "Global": current_address = None

        # Check for unique code if changed
        current_code = values[1]
        if code != current_code and code and not database.is_code_unique(code):
            messagebox.showerror("Error de Validación", f"El código '{code}' ya existe. Por favor use un código único.", parent=self)
            return

        if name and price >= 0 and unit_of_measure_desc:
            try:
                # Map Description -> Code
                um_code = self.um_description_to_code.get(unit_of_measure_desc, unit_of_measure_desc)
                database.update_product(product_id, name, price, stock, code, um_code, operation_type, current_issuer, current_address, category)
                messagebox.showinfo("Éxito", "Producto actualizado correctamente.", parent=self)
                self.populate_products_list()
                self.clear_fields()
                self.add_btn.set_state("normal")
            except Exception as e:
                messagebox.showerror("Error de Base de Datos", f"No se pudo actualizar el producto.\n\nError: {e}", parent=self)
        else:
            messagebox.showerror("Datos Incompletos", "Los campos 'Nombre', 'Precio' y 'U. Medida' son obligatorios.", parent=self)

    def delete_product(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Sin Selección", "Por favor, seleccione un producto para eliminar.", parent=self)
            return

        values = self.tree.item(selected_item)["values"]
        
        product_id = values[0]
        product_name = values[3] 
        # Clean stock string
        stock_str = str(values[5]).replace(",", "")
        try:
            stock = float(stock_str)
        except ValueError:
            stock = 0.0

        # Use epsilon for float comparison
        if abs(stock) > 0.001:
            messagebox.showwarning("Acción Denegada", f"Solo se pueden eliminar productos con stock 0. El producto '{product_name}' tiene stock ({stock}).", parent=self)
            return
        
        # Usar messagebox nativo de tkinter para evitar problemas con ttkbootstrap
        import tkinter.messagebox as tk_messagebox
        
        if tk_messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar el producto '{product_name}'?", parent=self):
            try:
                # Ensure ID is treated as correct type
                try: product_id_int = int(product_id)
                except: product_id_int = product_id
                
                if database.delete_product(product_id_int):
                    self.tree.delete(selected_item)
                    messagebox.showinfo("Éxito", "Producto eliminado correctamente.", parent=self)
                    self.populate_products_list()
                    self.clear_fields()
                else:
                    messagebox.showerror("Error", "No se pudo eliminar el producto (ID no encontrado o error de BD).", parent=self)
            except Exception as e:
                messagebox.showerror("Error de Base de Datos", f"No se pudo eliminar el producto.\n\nError: {e}", parent=self)

    def load_selected_product(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item)["values"]
            # values: 0=ID, 1=Code, 2=Name, 3=Price, 4=Stock, 5=UM, 6=OpType, 7=Issuer, 8=Address
            self.code_var.set(values[1])
            self.name_var.set(values[2])
            
            # Price comes as "S/ 25.00", need to parse
            price_str = values[3].replace("S/ ", "").strip()
            try:
                self.price_var.set(float(price_str))
            except ValueError:
                self.price_var.set(0.0)
                
            self.stock_var.set(values[4])
            
            # Map Code -> Description
            um_code = values[5]
            um_desc = self.um_code_to_description.get(um_code, um_code)
            self.unit_of_measure_var.set(um_desc)
            
            if len(values) > 6:
                self.operation_type_var.set(values[6])
            else:
                self.operation_type_var.set("Gravada")
            
            if len(values) > 9:
                self.category_var.set(values[9])
            else:
                self.category_var.set("General")
            
            # Enable Update, Disable Add
            if hasattr(self, 'add_btn'): self.add_btn.set_state("disabled")
            # Update button removed per user request

    def clear_fields(self):
        self.name_var.set("")
        self.price_var.set(0.0)
        # self.stock_var.set(0.0)
        self.code_var.set("")
        default_um = config_manager.load_setting("default_unit_of_measure", "")
        self.unit_of_measure_var.set(default_um)
        self.operation_type_var.set("Gravada")
        # No resetear categoría para facilitar ingreso continuo
        # self.category_var.set("General") 
        if self.tree.focus():
            self.tree.selection_remove(self.tree.focus())
        self.image_data = None
        if hasattr(self, 'image_status_label'):
             self.image_status_label.config(text="Sin imagen seleccionada", foreground="gray")
        
        # Reset Button States
        if hasattr(self, 'add_btn'): self.add_btn.set_state("normal")
        
        self.name_entry.focus_set()

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Imagen del Producto",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            try:
                # Resize and convert to bytes
                img = Image.open(file_path)
                # Resize to thumbnail (128x128 max)
                img.thumbnail((128, 128))
                
                # Convert to bytes
                output = io.BytesIO()
                # Default to PNG for preservation
                img.save(output, format="PNG")
                self.image_data = output.getvalue()
                
                filename = file_path.split("/")[-1]
                self.image_status_label.config(text=f"Cargada: {filename}", foreground=COLOR_ACCENT)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen: {e}", parent=self)


    def generate_unique_code(self):
        length = 6
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if database.is_code_unique(code):
                self.code_var.set(code)
                break

    def sort_treeview(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Try to convert to float for numerical sorting
        try:
            # Clean currency symbols if present
            sample = l[0][0]
            if "S/" in str(sample):
                l.sort(key=lambda t: float(t[0].replace("S/", "").strip()), reverse=reverse)
            elif str(sample).replace('.', '', 1).isdigit():
                 l.sort(key=lambda t: float(t[0]), reverse=reverse)
            else:
                 l.sort(reverse=reverse)
        except:
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # Reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def _get_escpos_image_bytes(self, image_data, max_width=384):
        """
        Convierte una imagen (bytes o PIL Image) a comandos ESC/POS raster bit image (GS v 0).
        max_width: Ancho máximo en puntos (default 384 para 58mm, usar 512 o 576 para 80mm).
        """
        from PIL import Image
        import io
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
                            pixel = img.getpixel((x, y))
                            if pixel == 0: 
                                byte_val |= (1 << (7 - bit))
                    raster_data.append(byte_val)
            
            return header + raster_data + b'\n' # Salto de línea después de imagen
        except Exception as e:
            print(f"Error procesando imagen ESC/POS: {e}")
            return b""

    def _generate_inventory_ticket(self):
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
        buffer.extend(ALIGN_CENTER)
        buffer.extend(BOLD_ON + text("REPORTE DE INVENTARIO\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        buffer.extend(text(f"FECHA: {now}\n"))
        
        issuer = self.filter_issuer_var.get()
        address = self.filter_address_var.get()
        
        # Centered and Wrapped Issuer
        buffer.extend(text("EMISOR:\n"))
        issuer_lines = textwrap.wrap(issuer, width=42)
        for line in issuer_lines:
            buffer.extend(BOLD_ON + text(line + "\n") + BOLD_OFF)
        
        # Wrap address if long
        addr_lines = textwrap.wrap(f"DIRECCION: {address}", width=42)
        for line in addr_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS SECTION ---
        # 4 Column Layout Compact: PRODUCTO | STOCK | PRECIO | VALORIZ.
        # Widths: 15 | 7 | 8 | 9 (Total 39 + 3 spaces = 42)
        
        header = "PRODUCTO        STOCK   PRECIO   VALORIZ."
        buffer.extend(BOLD_ON + text(header + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        total_products = 0
        total_stock = 0.0
        total_value = 0.0
        
        # Iterate children in current display order (respecting sort)
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            # values: 0=ID, 1=Code, 2=Category, 3=Name, 4=Price, 5=Stock, 6=Valorizado...
            
            name = str(values[3])
            price_str = str(values[4]).replace("S/ ", "")
            stock_str = str(values[5])
            valorizado_str = str(values[6]).replace("S/ ", "")
            
            # Calculate totals
            try:
                stock_val = float(stock_str.replace(",", ""))
                price_val = float(price_str.replace(",", ""))
                val_val = float(valorizado_str.replace(",", ""))
                
                total_products += 1
                total_stock += stock_val
                total_value += val_val
            except ValueError:
                pass
            
            # Compact Layout: Single line, Truncated Name
            # {name:15} {stock:7} {price:8} {val:9}
            
            # Truncate name to 15 chars
            name_trunc = name[:15]
            
            # Format line
            line = f"{name_trunc:<15} {stock_str:>7} {price_str:>8} {valorizado_str:>9}"
            buffer.extend(text(line + "\n"))
                
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- FOOTER ---
        # Centered totals
        buffer.extend(ALIGN_CENTER)
        buffer.extend(text(f"PRODUCTOS: {total_products}\n"))
        buffer.extend(text(f"STOCK TOTAL: {total_stock:,.2f}\n"))
        buffer.extend(BOLD_ON + text(f"VALORIZADO: S/ {total_value:,.2f}\n") + BOLD_OFF)
        
        buffer.extend(CUT)
        return buffer
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
        buffer.extend(ALIGN_CENTER)
        buffer.extend(BOLD_ON + text("REPORTE DE INVENTARIO\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        buffer.extend(text(f"FECHA: {now}\n"))
        
        issuer = self.filter_issuer_var.get()
        address = self.filter_address_var.get()
        
        # Centered and Wrapped Issuer
        buffer.extend(text("EMISOR:\n"))
        issuer_lines = textwrap.wrap(issuer, width=42)
        for line in issuer_lines:
            buffer.extend(BOLD_ON + text(line + "\n") + BOLD_OFF)
        
        # Wrap address if long
        addr_lines = textwrap.wrap(f"DIRECCION: {address}", width=42)
        for line in addr_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS SECTION ---
        # 4 Column Layout: PRODUCTO | STOCK | PRECIO | VALORIZADO
        # Widths approx: 15 | 7 | 9 | 10  (+ spaces)
        
        header = "PRODUCTO        STOCK   PRECIO   VALORIZ."
        buffer.extend(BOLD_ON + text(header + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        total_products = 0
        total_stock = 0.0
        total_value = 0.0
        
        # Iterate children in current display order (respecting sort)
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            # values: 0=ID, 1=Code, 2=Category, 3=Name, 4=Price, 5=Stock, 6=Valorizado...
            
            name = str(values[3])
            price_str = str(values[4]).replace("S/ ", "")
            stock_str = str(values[5])
            valorizado_str = str(values[6]).replace("S/ ", "")
            
            # Calculate totals
            try:
                stock_val = float(stock_str.replace(",", ""))
                price_val = float(price_str.replace(",", ""))
                # valorizado_str typically comes formatted "S/ 1,200.00", need to clean
                val_val = float(valorizado_str.replace(",", ""))
                
                total_products += 1
                total_stock += stock_val
                total_value += val_val
            except ValueError:
                pass
            
            # Layout
            # Name: Left aligned, Wrapped if needed (max 15 chars for first column visually?)
            # Actually, to make it look like columns, we should probably stick to lines.
            # But wrapping name might break column alignment if we just append.
            # Strategy:
            # Line 1: Name part 1 (15 chars) | Stock (7) | Price (9) | Value (10)
            # Line 2+: Name part remaining...
            
            col_width_name = 15
            name_lines = textwrap.wrap(name, width=col_width_name)
            
            # First line with data
            n1 = name_lines[0] if name_lines else ""
            remaining_names = name_lines[1:]
            
            # Format: "{:<15} {:>7} {:>9} {:>10}"
            line1 = f"{n1:<15} {stock_str:>7} {price_str:>8} {valorizado_str:>9}"
            buffer.extend(text(line1 + "\n"))
            
            # Remaining name lines
            for r_name in remaining_names:
                buffer.extend(text(f"{r_name}\n"))
                
            buffer.extend(text("." * 42 + "\n"))
                
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- FOOTER ---
        # Centered totals
        buffer.extend(ALIGN_CENTER)
        buffer.extend(text(f"PRODUCTOS: {total_products}\n"))
        buffer.extend(text(f"STOCK TOTAL: {total_stock:,.2f}\n"))
        buffer.extend(BOLD_ON + text(f"VALORIZADO: S/ {total_value:,.2f}\n") + BOLD_OFF)
        
        buffer.extend(CUT)
        return buffer
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
        buffer.extend(ALIGN_CENTER)
        buffer.extend(BOLD_ON + text("REPORTE DE INVENTARIO\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        buffer.extend(text(f"FECHA: {now}\n"))
        
        issuer = self.filter_issuer_var.get()
        address = self.filter_address_var.get()
        
        buffer.extend(text(f"EMISOR: {issuer}\n"))
        
        # Wrap address if long
        addr_lines = textwrap.wrap(f"DIRECCION: {address}", width=42)
        for line in addr_lines:
            buffer.extend(text(line + "\n"))
            
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- ITEMS ---
        # Header: PRODUCTO (Left), STOCK (Right), PRECIO (Right)
        # Using 42 chars width for 80mm
        # PRODUCTO (22) | STOCK (10) | PRECIO (10)
        header = "PRODUCTO              STOCK     PRECIO"
        buffer.extend(BOLD_ON + text(header + "\n") + BOLD_OFF)
        buffer.extend(text("-" * 42 + "\n"))
        
        total_products = 0
        total_stock = 0.0
        total_value = 0.0
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            # values: 0=ID, 1=Code, 2=Category, 3=Name, 4=Price, 5=Stock, 6=Valorizado...
            
            name = str(values[3])
            price_str = str(values[4]).replace("S/ ", "")
            stock_str = str(values[5])
            valorizado_str = str(values[6]).replace("S/ ", "")
            
            try:
                stock = float(stock_str.replace(",", ""))
                price = float(price_str.replace(",", ""))
                valorizado = float(valorizado_str.replace(",", ""))
                
                total_products += 1
                total_stock += stock
                total_value += valorizado
            except ValueError:
                pass
                
            buffer.extend(ALIGN_LEFT)
            
            # Name wrapping
            name_lines = textwrap.wrap(name, width=22)
            
            # Print first line with stock and price
            line1_name = name_lines[0]
            
            # Format: Name(22) + Stock(10) + Price(10)
            line = f"{line1_name:<22}{stock_str:>10}{price_str:>10}"
            buffer.extend(text(line + "\n"))
            
            # Print remaining name lines
            for extra_line in name_lines[1:]:
                buffer.extend(text(f"{extra_line:<22}\n"))
                
        buffer.extend(text("-" * 42 + "\n"))
        
        # --- FOOTER ---
        buffer.extend(ALIGN_RIGHT)
        buffer.extend(text(f"PRODUCTOS: {total_products}\n"))
        buffer.extend(text(f"STOCK TOTAL: {total_stock:,.2f}\n"))
        buffer.extend(BOLD_ON + text(f"VALORIZADO: S/ {total_value:,.2f}\n") + BOLD_OFF)
        
        buffer.extend(CUT)
        return buffer

    def print_inventory(self):
        if win32print is None:
            messagebox.showerror("Error de Impresión", "El módulo 'pywin32' es necesario para imprimir.", parent=self)
            return
            
        printer_name = config_manager.load_setting('default_printer')
        if not printer_name:
            messagebox.showwarning("Impresora no Configurada", "Por favor, configure una impresora por defecto.", parent=self)
            return
            
        try:
            data = self._generate_inventory_ticket()
            if not data:
                return

            h_printer = win32print.OpenPrinter(printer_name)
            try:
                h_job = win32print.StartDocPrinter(h_printer, 1, ("Reporte Inventario", None, "RAW"))
                try:
                    win32print.StartPagePrinter(h_printer)
                    win32print.WritePrinter(h_printer, data)
                    win32print.EndPagePrinter(h_printer)
                finally:
                    win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
                
            messagebox.showinfo("Impresión", "Reporte enviado a la impresora.", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Impresión", f"No se pudo imprimir: {e}", parent=self)

    def generate_excel_template(self):
        if pd is None:
            messagebox.showerror("Error", "La librería 'pandas' no está instalada. No se puede generar Excel.", parent=self)
            return

        import os
        import winreg
        
        # Obtener ruta del escritorio desde el registro de Windows (funciona en cualquier idioma/usuario)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            winreg.CloseKey(key)
        except Exception:
            # Fallback: usar USERPROFILE/Desktop
            desktop_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        
        # Verificar que el directorio exista
        if not os.path.exists(desktop_path):
            messagebox.showerror("Error", f"No se encontró el escritorio: {desktop_path}", parent=self)
            return
            
        file_path = os.path.join(desktop_path, "PLANTILLA EXCEL.xlsx")

        # Columns
        columns = ["NOMBRE", "CODIGO", "PRECIO", "STOCK", "UNIDAD_MEDIDA", "CATEGORIA", "TIPO_OPERACION"]
        
        # Create empty DF
        df = pd.DataFrame(columns=columns)
        
        try:
            df.to_excel(file_path, index=False)
            
            # Auto open
            try:
                os.startfile(file_path)
            except: pass
            
            messagebox.showinfo("Éxito", f"Plantilla guardada y abierta:\n{file_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar plantilla: {e}", parent=self)

    def import_from_excel(self):
        if pd is None:
            messagebox.showerror("Error", "La librería 'pandas' no está instalada.", parent=self)
            return
            
        # Validate Context
        issuer = self.filter_issuer_var.get()
        address = self.filter_address_var.get()
        
        if issuer == "Todas" or address == "Todas":
            messagebox.showwarning("Selección Requerida", "Por favor seleccione un Emisor y Dirección específicos antes de importar.", parent=self)
            return

        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")], title="Seleccionar Excel")
        if not file_path:
            return
            
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo Excel: {e}", parent=self)
            return
            
        # Normalize Headers
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        required_cols = ["CODIGO", "CATEGORIA", "NOMBRE", "PRECIO", "UNIDAD_MEDIDA", "TIPO_OPERACION"]
        for col in required_cols:
            if col not in df.columns:
                 messagebox.showerror("Error de Formato", f"Falta la columna obligatoria: {col}\n\nTodas las columnas son obligatorias:\nCODIGO, CATEGORIA, NOMBRE, PRECIO, UNIDAD_MEDIDA, TIPO_OPERACION", parent=self)
                 return
                 
        # Process Rows
        added_count = 0
        errors = []
        
        valid_ops = ["Gravada", "Exonerada", "Inafecta", "Exportación"]
        valid_ops_upper = {v.upper(): v for v in valid_ops}
        
        for index, row in df.iterrows():
            row_num = index + 2 # Excel Row Reference
            
            try:
                # 1. Name (Required)
                name = str(row.get("NOMBRE", "")).strip()
                if not name or name.lower() == "nan":
                    errors.append(f"Fila {row_num}: 'NOMBRE' es obligatorio.")
                    continue
                
                # 2. Price (Required)
                price_val = row.get("PRECIO", 0)
                try: 
                    price = float(price_val)
                except: 
                    errors.append(f"Fila {row_num}: 'PRECIO' inválido.")
                    continue
                
                # 3. Stock (Forced to 0)
                stock = 0.0
                
                # 4. Code (Required)
                code = str(row.get("CODIGO", "")).strip()
                if not code or code.lower() == "nan":
                    errors.append(f"Fila {row_num}: 'CODIGO' es obligatorio.")
                    continue

                # 5. Category (Required)
                cat = str(row.get("CATEGORIA", "")).strip()
                if not cat or cat.lower() == "nan":
                    errors.append(f"Fila {row_num}: 'CATEGORIA' es obligatoria.")
                    continue
                
                # 6. Unit of Measure (Required + Valid)
                um_raw = str(row.get("UNIDAD_MEDIDA", "")).strip()
                if not um_raw or um_raw.lower() == "nan":
                    errors.append(f"Fila {row_num}: 'UNIDAD_MEDIDA' es obligatoria.")
                    continue
                
                # Check map Description -> Code
                found_code = None
                
                # Direct Code Match?
                if um_raw in self.um_code_to_description:
                    found_code = um_raw
                # Description Match?
                elif um_raw in self.um_description_to_code:
                    found_code = self.um_description_to_code[um_raw]
                # Partial Match?
                else:
                    for desc, code_val in self.um_description_to_code.items():
                        if um_raw.upper() in desc.upper():
                            found_code = code_val
                            break
                
                if not found_code:
                    errors.append(f"Fila {row_num}: 'UNIDAD_MEDIDA' inválida ('{um_raw}').")
                    continue
                um_code = found_code
                    
                # 7. Operation Type (Required + Valid)
                op_raw = str(row.get("TIPO_OPERACION", "")).strip()
                if not op_raw or op_raw.lower() == "nan":
                     errors.append(f"Fila {row_num}: 'TIPO_OPERACION' es obligatorio.")
                     continue

                if op_raw.upper() in valid_ops_upper:
                    op_type = valid_ops_upper[op_raw.upper()]
                else:
                    errors.append(f"Fila {row_num}: 'TIPO_OPERACION' inválido ('{op_raw}').")
                    continue
                
                # Check Code Uniqueness (Locally for this Issuer)
                # Since we are inserting new, check if code already exists in db for this issuer
                # (Assuming is_code_unique checks globally or per issuer? 
                #  Actually database.is_code_unique checks GLOBALLY in most functions, but v30 introduced per-issuer unique index)
                #  We should arguably check if it exists to avoid IntegrityError or just let IntegrityError handle it.
                #  Let's let try/except handle IntegrityError from DB constraint if present.
                
                try:
                    database.add_product(name, price, stock, code, um_code, op_type, issuer, address, cat, image=None)
                    added_count += 1
                except Exception as e:
                     errors.append(f"Fila {row_num}: Error al guardar (¿Código duplicado?): {e}")
                     
            except Exception as e:
                errors.append(f"Fila {row_num}: Error Inesperado: {e}")
                
        # Result
        self.populate_products_list()
        
        if errors:
            msg = f"Importación completada con OBSERVACIONES.\n\nProductos Agregados: {added_count}\n\nErrores ({len(errors)}):\n" + "\n".join(errors[:15])
            if len(errors) > 15: msg += "\n..."
            messagebox.showwarning("Reporte de Importación", msg, parent=self)
        else:
            msg = f"Confirmación de Importación\n\nSe han importado exitosamente {added_count} productos.\n\nTodos los datos son conformes."
            messagebox.showinfo("Éxito", msg, parent=self)