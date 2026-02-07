import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import io
import custom_messagebox as messagebox
import database
from datetime import datetime
import config_manager
import json
import textwrap
import json_generator
from sales_view import SalesView, FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HEADER
from theme_manager import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_TEXT, 
    COLOR_BUTTON_PRIMARY, COLOR_BUTTON_SECONDARY, COLOR_BUTTON_DANGER,
    POS_PRIMARY_DARK, POS_PRIMARY_LIGHT, POS_BG_MAIN, POS_BG_WHITE,
    POS_ACCENT_GREEN_START, POS_ACCENT_GREEN_END, POS_ACCENT_RED, POS_ACCENT_BLUE,
    POS_GRP_COLORS, POS_TEXT_COLOR
)

# Map to expected names if needed, or use directly
COLOR_PRIMARY_DARK = POS_PRIMARY_DARK
COLOR_SECONDARY_DARK = POS_PRIMARY_LIGHT
COLOR_ACCENT_BLUE = POS_ACCENT_BLUE
COLOR_TEXT_LIGHT = POS_BG_MAIN # Used for text on dark bg? No, BG_MAIN is light gray.
# Override standard constants for this view only if really needed, better use POS_ directly.


import os
import textwrap
from tkinter.colorchooser import askcolor

import state_manager
from movements_touch_dialog import TouchMovementDialog
GROUP_ORDER_FILE = 'group_order.json'
PRODUCT_ORDER_FILE = 'product_order.json'

from PIL import ImageDraw, ImageFont

class GradientFrame(tk.Canvas):
    def __init__(self, parent, color1, color2, text="", text_color="white", shadow_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self._text = text
        self._text_color = text_color
        self._shadow_color = shadow_color
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
        
        # Draw Text if present
        if self._text:
            x = width // 2
            y = height // 2
            font = (FONT_FAMILY, 14, "bold")
            
            # Shadow removed per user request
            # if self._shadow_color:
            #    self.create_text(x+2, y+2, text=self._text, fill=self._shadow_color, font=font, anchor="center", tags=("text",))
            
            # Main Text
            self.create_text(x, y, text=self._text, fill=self._text_color, font=font, anchor="center", tags=("text",))

class GradientButton(tk.Canvas):
    def __init__(self, parent, text, icon="", color1="#007bff", color2="#0056b3", command=None, width=None, height=40, text_color="white", corner_radius=10, border_color=None, image=None, font_size=10, shadow_color=None, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, takefocus=True, **kwargs)
        self.text = text
        self.icon = icon
        self._color1 = color1
        self._color2 = color2
        self._text_color = text_color
        self._command = command
        self.corner_radius = corner_radius
        self.border_color = border_color
        self.image = image # PhotoImage
        
        # Font for Text and Icon
        self._font_args = (FONT_FAMILY, font_size, "bold")
        
        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Configure>', lambda e: self._draw(e.width, e.height))
        self.bind('<FocusIn>', self._on_focus_in)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Return>', self._simulate_click)
        self.bind('<space>', self._simulate_click)
        
        self._is_pressed = False
        self._is_hover = False
        self._is_focused = False

    def _on_focus_in(self, event):
        self._is_focused = True
        self._draw(self.winfo_width(), self.winfo_height())
        
    def _on_focus_out(self, event):
        self._is_focused = False
        self._draw(self.winfo_width(), self.winfo_height())
        
    def _simulate_click(self, event):
        self._on_press(event)
        self.after(100, lambda: self._on_release(event))

    def configure(self, **kwargs):
        redraw = False
        if 'text' in kwargs:
             self.text = kwargs.pop('text')
             redraw = True
        
        if 'image' in kwargs:
             self.image = kwargs.pop('image')
             redraw = True
        
        # Handle custom colors
        if 'color1' in kwargs:
             self._color1 = kwargs.pop('color1')
             redraw = True
        if 'color2' in kwargs:
             self._color2 = kwargs.pop('color2')
             redraw = True
        if 'text_color' in kwargs:
             self._text_color = kwargs.pop('text_color')
             redraw = True
        if 'border_color' in kwargs:
             self.border_color = kwargs.pop('border_color')
             redraw = True

        # Handle style mapping to colors (Emulation for Product Buttons)
        if 'style' in kwargs:
             style = kwargs.pop('style')
             if style == "ProductLowStock.TButton":
                  self._color1 = POS_ACCENT_RED
                  self._color2 = POS_ACCENT_RED
                  self._text_color = "white"
             elif style == "Product.TButton":
                  self._color1 = "#ffffff"
                  self._color2 = "#ffffff"
                  self._text_color = "black"
             # Ignore other styles or add mappings as needed
             redraw = True

        # Pass remaining valid kwargs to super (Canvas)
        if kwargs:
            super().configure(**kwargs)
            
        if redraw:
             self._draw(self.winfo_width(), self.winfo_height())

    def config(self, **kwargs):
        self.configure(**kwargs)
        
    def cget(self, key):
        if key == "text":
            return self.text
        return super().cget(key)
        
    def __setitem__(self, key, value):
        self.configure(**{key: value})

    def _adjust_brightness(self, hex_color, factor):
        # Resolve bootstyle names if possible
        hex_color = self._resolve_color(hex_color)
            
        try:
            r, g, b = self.winfo_rgb(hex_color)
            r, g, b = r//256, g//256, b//256
        except:
            return hex_color
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return "#%02x%02x%02x" % (r, g, b)

    def _resolve_color(self, color):
        """Resolves ttkbootstrap color keywords to hex."""
        if not color: return "#000000"
        if color.startswith("#"): return color
        
        # Check standard bootstrap colors
        style = ttk.Style.get_instance()
        # Access colors via the theme definition if available, or try lookup
        # ttkbootstrap styles allow looking up colors by name from the 'colors' object associated with style?
        # Actually style.colors is handy but private-ish or version dependent.
        # Safer: use the color definition if it matches standard names.
        
        # Valid bootstrap colors: primary, secondary, success, info, warning, danger, light, dark
        valid = ["primary", "secondary", "success", "info", "warning", "danger", "light", "dark"]
        if color in valid:
             try:
                 return style.colors.get(color)
             except:
                 pass
        
        return color

    def _draw(self, width, height):
        self.delete("all")
        
        # Determine current colors
        if self._is_pressed:
            # Darken
            c1 = self._adjust_brightness(self._color1, 0.8)
            c2 = self._adjust_brightness(self._color2, 0.8)
        elif self._is_hover:
            # Lighten
            c1 = self._adjust_brightness(self._color1, 1.1)
            c2 = self._adjust_brightness(self._color2, 1.1)
        else:
            c1 = self._resolve_color(self._color1)
            c2 = self._resolve_color(self._color2)
            
        # Draw Gradient Rounded Rectangle using PIL
        # 1. Create Gradient Image
        gradient_img = Image.new('RGBA', (width, height))
        draw_g = ImageDraw.Draw(gradient_img)
        
        # Horizontal Gradient
        try:
            r1, g1, b1 = self.winfo_rgb(c1)
            r2, g2, b2 = self.winfo_rgb(c2)
        except tk.TclError:
            # Fallback if somehow still invalid
            r1, g1, b1 = 200, 200, 200
            r2, g2, b2 = 100, 100, 100
            
        r1, g1, b1 = r1//256, g1//256, b1//256
        r2, g2, b2 = r2//256, g2//256, b2//256
        
        for x in range(width):
            r = int(r1 + (r2 - r1) * x / width)
            g = int(g1 + (g2 - g1) * x / width)
            b = int(b1 + (b2 - b1) * x / width)
            draw_g.line((x, 0, x, height), fill=(r, g, b, 255))

        # 2. Mask for Rounded Corners
        mask_img = Image.new('L', (width, height), 0)
        draw_mask = ImageDraw.Draw(mask_img)
        
        draw_mask.rounded_rectangle((0, 0, width, height), radius=self.corner_radius, fill=255)
        
        final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        final_img.paste(gradient_img, (0, 0), mask_img)
        
        # Draw Border if needed (Overlay)
        if self.border_color:
             draw_final = ImageDraw.Draw(final_img)
             br, bg, bb = self.winfo_rgb(self.border_color)
             br, bg, bb = br//256, bg//256, bb//256
             draw_final.rounded_rectangle((0, 0, width-1, height-1), radius=self.corner_radius, outline=(br, bg, bb, 255), width=2, fill=None)
        
        if self._is_focused:
             draw_final = ImageDraw.Draw(final_img)
             draw_final.rounded_rectangle((1, 1, width-2, height-2), radius=self.corner_radius, outline="white", width=3, fill=None)
        
        self.image_ref = ImageTk.PhotoImage(final_img)
        self.create_image(0, 0, image=self.image_ref, anchor='nw')
        
        # Draw Product Image if present (Right Side)
        text_x = 10
        text_width = width - 20
        text_anchor = "center" # default
        
        if self.image:
             # Assuming self.image is a PhotoImage
             try:
                 img_w = self.image.width()
                 img_h = self.image.height()
                 # Position: Right side, centered vertically
                 padding = 10
                 x_img = width - img_w - padding
                 y_img = (height - img_h) // 2
                 self.create_image(x_img, y_img, image=self.image, anchor='nw')
                 
                 # Adjust text area
                 # Text should be on the left
                 text_width = x_img - 15 # padding
                 text_x = text_width // 2 + 5
             except: pass

        # Text/Icon
        full_text = f"{self.icon} {self.text}"
        # If we have image, we might want to align text left or center in remaining space.
        # "center" of remaining space (0 to text_width) is text_width//2
        # If no image, center of button is width//2
        
        if self.image:
             center_x = text_width // 2 + 5
        else:
             center_x = width // 2
             
        self.create_text(center_x, height//2, text=full_text, fill=self._text_color, font=self._font_args, justify="center", width=text_width)

    def _adjust_brightness(self, hex_color, factor):
        try:
            r, g, b = self.winfo_rgb(hex_color)
            r, g, b = r//256, g//256, b//256
        except:
            return hex_color
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return "#%02x%02x%02x" % (r, g, b)

    def _on_press(self, event):
        self._is_pressed = True
        self._draw(self.winfo_width(), self.winfo_height())

    def _on_release(self, event):
        self._is_pressed = False
        self._draw(self.winfo_width(), self.winfo_height())
        if self._command:
            self._command()

    def _on_enter(self, event):
        self._is_hover = True
        self._draw(self.winfo_width(), self.winfo_height())

    def _on_leave(self, event):
        self._is_hover = False
        self._is_pressed = False
        self._draw(self.winfo_width(), self.winfo_height())

class SalesTouchView(SalesView):
    def _is_dark(self, hex_color):
        """Determine if a hex color is dark (to set text color to white)"""
        if not hex_color.startswith('#'): return False
        hex_color = hex_color.lstrip('#')
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # YIQ equation
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq < 128
        except:
            return False

    def __init__(self, master, caja_id=None):
        # Initialize ttk.Frame directly
        ttk.Frame.__init__(self, master, padding=0, style='SalesView.TFrame') # Padding 0 for full bleed
        
        if caja_id:
            self.caja_id = str(caja_id)
        else:
            self.caja_id = config_manager.load_setting('caja_id', '1')
        
        # --- Layout Configuration ---
        # --- Layout Configuration ---
        # Left Pane (Products): Allow expansion
        self.columnconfigure(0, weight=1) 
        
        # Right Pane (Cart): Fixed width or limited expansion to prevent "widening bug"
        # We set weight to 0 and a minsize, or we rely on the frame's internal strict width.
        # Ideally, we set a reasonable fixed width for the cart panel (e.g., 35% or fixed pixels).
        # Let's try weight 0 with minsize.
        self.columnconfigure(1, weight=0, minsize=450) 
        
        self.rowconfigure(0, weight=1)

        # --- Custom Styles (Modern POS) ---
        style = ttk.Style.get_instance()
        
        # specific styles for this view
        style.configure('SalesView.TFrame', background=POS_BG_WHITE)
        style.configure('Catalog.TFrame', background=POS_BG_WHITE)
        style.configure('Sidebar.TFrame', background=POS_BG_WHITE)
        style.configure('Sidebar.TLabel', background=POS_BG_WHITE, foreground=POS_PRIMARY_DARK)
        
        # Banners for Sections (Grupos/Productos)
        style.configure('Banner.TLabel', background=POS_PRIMARY_DARK, foreground='#FFFFFF', font=(FONT_FAMILY, 10, 'bold'), anchor="center", padding=5)
        
        # Product Button Style (White Card effect)
        style.configure('Product.TButton', background=POS_BG_WHITE, foreground=POS_PRIMARY_DARK, font=(FONT_FAMILY, 10, 'bold'), borderwidth=1, relief="solid")
        style.map('Product.TButton', 
                  background=[('active', '#eef2f7')], 
                  foreground=[('active', POS_PRIMARY_DARK)],
                  relief=[('pressed', 'sunken')])
                  
        # Low Stock
        style.configure('ProductLowStock.TButton', background=POS_BG_WHITE, foreground=POS_ACCENT_RED, font=(FONT_FAMILY, 10, 'bold'), borderwidth=1)

        # Group Buttons: Will be dynamic based on POS_GRP_COLORS
        for i, color in enumerate(POS_GRP_COLORS):
            style_name = f"Group{i}.TButton"
            style.configure(style_name, background=color, foreground='white', font=(FONT_FAMILY, 10, 'bold'), width=10)
            style.map(style_name, background=[('active', color), ('pressed', color)], relief=[('pressed', 'sunken')])

        # Cobrar Button (Gradient simulation -> Solid for now, or Image)
        # We will use a custom style or canvas. For now, solid Green.
        style.configure('Pay.TButton', background=POS_ACCENT_GREEN_START, foreground='white', font=(FONT_FAMILY, 16, 'bold'))
        style.map('Pay.TButton', background=[('active', POS_ACCENT_GREEN_END)])

        # Secondary Buttons
        style.configure('Delete.TButton', foreground=POS_ACCENT_RED, background='white', font=(FONT_FAMILY, 10, 'bold'))
        style.configure('Clear.TButton', foreground=POS_ACCENT_BLUE, background='white', font=(FONT_FAMILY, 10, 'bold'))

        # Borderless Combobox for use inside Rounded Canvas
        style.configure('Borderless.TCombobox', borderwidth=0, relief='flat', selectborderwidth=0)
        style.map('Borderless.TCombobox', 
                  fieldbackground=[('readonly', 'white')], 
                  background=[('readonly', 'white')],
                  bordercolor=[('readonly', 'white'), ('active', 'white')], # Hide border
                  lightcolor=[('readonly', 'white')], 
                  darkcolor=[('readonly', 'white')]) # Attempts to flatten standard ttk themes



        # --- Initialize Variables (Copied from SalesView) ---
        self.products = {}
        self.issuers = {}
        self.cart = []
        self.total = 0.0
        self.editing_item_index = None
        
        self.product_order = {} # {category: [product_id, ...]}
        self.product_colors = {} # {product_id: color_code}
        
        self.doc_type_var = tk.StringVar(value="BOLETA DE VENTA ELECTRÓNICA")
        self.doc_series_var = tk.StringVar()
        self.doc_number_var = tk.StringVar()
        
        self.payment_method_var = tk.StringVar(value="EFECTIVO")
        self.payment_method_var = tk.StringVar(value="EFECTIVO")
        self.amount_paid_var = tk.StringVar(value="0.0") # Changed to StringVar to avoid TclError on empty input
        self.payment_method_var2 = tk.StringVar(value="NINGUNO")
        self.amount_paid_var2 = tk.DoubleVar(value=0.0)
        
        self.issuer_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.datetime_var = tk.StringVar()
        
        self.customer_doc_var = tk.StringVar()
        self.customer_name_var = tk.StringVar()
        self.customer_address_var = tk.StringVar()
        self.customer_phone_var = tk.StringVar()
        
        self.product_var = tk.StringVar()
        self.quantity_var = tk.DoubleVar(value=1.0)
        self.price_var = tk.DoubleVar(value=0.0)
        self.unit_of_measure_var = tk.StringVar()
        
        # --- Load Helpers ---
        self.load_units_of_measure()
        
        # --- Build UI ---
        self.setup_left_pane()
        self.setup_right_pane()
        
        # --- Load Data ---
        self.update_datetime()
        self.update_datetime()
        self.load_group_order()
        self.load_product_order()
        self.load_issuers_from_db()
        # load_products_from_db is called inside load_issuers_from_db (via on_issuer_select -> on_address_select)
        
        self.product_buttons = {} # Store button references by product ID
        
        if hasattr(self, 'scan_entry'):
            def force_scan_focus(event=None):
                try:
                    self.scan_entry.focus_set()
                except: pass
            
            # Try setting focus after a distinct delay to override any other initialization focus
            self.after(500, force_scan_focus)
            
            # Also ensure focus when window is mapped/shown
            self.bind("<Map>", lambda e: self.after(100, force_scan_focus))
        
        # --- State Persistence ---
        self.load_state_from_disk()
        
        # Add traces for persistence
        self.doc_type_var.trace_add("write", lambda *args: self._persist_state())
        self.payment_method_var.trace_add("write", lambda *args: self._persist_state())
        self.amount_paid_var.trace_add("write", lambda *args: self._persist_state())
        self.customer_doc_var.trace_add("write", lambda *args: self._persist_state())
        self.customer_name_var.trace_add("write", lambda *args: self._persist_state())



    def load_group_order(self, issuer_id=None, address=None):
        if not hasattr(self, 'caja_id'):
             self.caja_id = config_manager.load_setting('caja_id', '1')
        
        self.group_order = []
        self.group_colors = {}
        
        if os.path.exists(GROUP_ORDER_FILE):
            try:
                with open(GROUP_ORDER_FILE, 'r') as f:
                    all_data = json.load(f)
                    
                    # Determine which key to use
                    # Priority 1: Context (Issuer + Address)
                    # Priority 2: Caja ID (Default/Last used for this Caja)
                    
                    data = None
                    if issuer_id and address:
                        context_key = f"CTX_{issuer_id}_{address}"
                        if context_key in all_data:
                            data = all_data[context_key]
                    
                    if data is None:
                        data = all_data.get(self.caja_id, {})
                    
                    if isinstance(data, list):
                        self.group_order = data
                        self.group_colors = {}
                    elif isinstance(data, dict):
                        self.group_order = data.get("order", [])
                        self.group_colors = data.get("colors", {})
            except json.JSONDecodeError:
                self.group_order = []
                self.group_colors = {}

    def save_group_order(self):
        all_data = {}
        if os.path.exists(GROUP_ORDER_FILE):
            try:
                with open(GROUP_ORDER_FILE, 'r') as f:
                    all_data = json.load(f)
            except json.JSONDecodeError:
                all_data = {}
        
        # Data to save
        data_to_save = {
            "order": self.group_order,
            "colors": getattr(self, 'group_colors', {})
        }
        
        # 1. Always save to current Caja ID (as "Last Used" fallback)
        all_data[self.caja_id] = data_to_save
        
        # 2. If we have an active context, save there too
        issuer_name = self.issuer_var.get()
        issuer_address = self.address_var.get()
        
        if issuer_name and issuer_address:
             # Find ID
            issuer_id = None
            if issuer_name in self.issuers:
                for i_data in self.issuers[issuer_name]:
                    if i_data['address'] == issuer_address:
                        issuer_id = i_data['id']
                        break
            
            if issuer_id:
                context_key = f"CTX_{issuer_id}_{issuer_address}"
                all_data[context_key] = data_to_save
        
        with open(GROUP_ORDER_FILE, 'w') as f:
            json.dump(all_data, f, indent=4)

    def load_product_order(self, issuer_id=None, address=None):
        if not hasattr(self, 'caja_id'):
             self.caja_id = config_manager.load_setting('caja_id', '1')
        
        self.product_order = {}
        self.product_colors = {}
        
        if os.path.exists(PRODUCT_ORDER_FILE):
            try:
                with open(PRODUCT_ORDER_FILE, 'r') as f:
                    all_data = json.load(f)
                    
                    data = None
                    if issuer_id and address:
                        context_key = f"CTX_{issuer_id}_{address}"
                        if context_key in all_data:
                            data = all_data[context_key]
                    
                    if data is None:
                        data = all_data.get(self.caja_id, {})
                    
                    if isinstance(data, dict):
                        self.product_order = data.get("order", {})
                        self.product_colors = data.get("colors", {})
            except json.JSONDecodeError:
                self.product_order = {}
                self.product_colors = {}

    def save_product_order(self):
        all_data = {}
        if os.path.exists(PRODUCT_ORDER_FILE):
            try:
                with open(PRODUCT_ORDER_FILE, 'r') as f:
                    all_data = json.load(f)
            except json.JSONDecodeError:
                all_data = {}
        
        # Data to save
        data_to_save = {
            "order": self.product_order,
            "colors": self.product_colors
        }
        
        # 1. Always save to current Caja ID
        all_data[self.caja_id] = data_to_save
        
        # 2. If we have an active context, save there too
        issuer_name = self.issuer_var.get()
        issuer_address = self.address_var.get()
        
        if issuer_name and issuer_address:
             # Find ID
            issuer_id = None
            if issuer_name in self.issuers:
                for i_data in self.issuers[issuer_name]:
                    if i_data['address'] == issuer_address:
                        issuer_id = i_data['id']
                        break
            
            if issuer_id:
                context_key = f"CTX_{issuer_id}_{issuer_address}"
                all_data[context_key] = data_to_save
        
        with open(PRODUCT_ORDER_FILE, 'w') as f:
            json.dump(all_data, f, indent=4)

    def on_address_select(self, event=None):
        # Override to load group order before loading products
        issuer_name = self.issuer_var.get()
        issuer_address = self.address_var.get()
        
        if issuer_name and issuer_address:
            # Find ID
            issuer_id = None
            if issuer_name in self.issuers:
                for i_data in self.issuers[issuer_name]:
                    if i_data['address'] == issuer_address:
                        issuer_id = i_data['id']
                        break
            
            if issuer_id:
                self.load_group_order(issuer_id, issuer_address)
                self.load_product_order(issuer_id, issuer_address)
        
        # Call super to handle product loading and persistence of last_issuer/address
        super().on_address_select(event)

    def refresh_group_order_if_needed(self):
        """Reloads group order based on current context. Called when switching tabs."""
        issuer_name = self.issuer_var.get()
        issuer_address = self.address_var.get()
        
        if issuer_name and issuer_address:
            # Find ID
            issuer_id = None
            if issuer_name in self.issuers:
                for i_data in self.issuers[issuer_name]:
                    if i_data['address'] == issuer_address:
                        issuer_id = i_data['id']
                        break
            
            if issuer_id:
                # Reload order from file (which might have been updated by another tab)
                self.load_group_order(issuer_id, issuer_address)
                self.load_product_order(issuer_id, issuer_address)
                self.refresh_category_buttons()
        
    def setup_left_pane(self):
        left_frame = ttk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.rowconfigure(4, weight=1) # Product grid expands (now at row 4)
        left_frame.columnconfigure(0, weight=1)
        
        # --- GROUPS SECTION ---
        # Banner using GradientFrame
        # Gradient from Dark Navy (#0a2240) to Bright Blue (#007bff)
        group_banner = GradientFrame(left_frame, color1="#0a2240", color2="#007bff", height=40, text="GRUPOS", shadow_color="#000000")
        group_banner.grid(row=0, column=0, sticky="ew")
        
        # Groups Container (White bg, rounded bottom effect - simulated with frame)
        groups_container = tk.Frame(left_frame, bg=POS_BG_WHITE) # Tk Frame for white bg
        groups_container.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=5)
        
        self.category_frame = ttk.Frame(groups_container, style='White.TFrame') # Transparent in tk frame? Tk frame is bg white.
        # Make sure category_frame buttons use the white bg.
        # Check configure of White.TFrame? I haven't defined it.
        # Let's just pack buttons.
        self.category_frame.pack(fill="x", padx=10, pady=10)
        
        # Pagination for groups
        self.pagination_frame = ttk.Frame(groups_container)
        self.pagination_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        self.current_category_page = 0
        self.categories_per_page = 14 # 7 columns x 2 rows
        
        # --- SEARCH ---
        search_frame = ttk.Frame(left_frame, style='Catalog.TFrame')
        search_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15), padx=10)
        
        # Rounded Search Entry simulation
        # Using a Canvas (GradientFrame logic or just rounded rect) containing an Entry
        # Since we want a white background with rounded border:
        
        self.scan_var = tk.StringVar()
        
        # Container for visual rounded border
        search_container = tk.Canvas(search_frame, bg=POS_BG_WHITE, height=45, highlightthickness=0)
        search_container.pack(fill="x", ipady=2)
        
        # Draw rounded rect
        # Fix search bar border: Use relief="flat" and explicit bg
        self.scan_entry = tk.Entry(search_container, textvariable=self.scan_var, font=(FONT_FAMILY, 12), fg=POS_TEXT_COLOR, bg=POS_BG_WHITE, borderwidth=0, highlightthickness=0, relief="flat", insertbackground=POS_TEXT_COLOR, selectbackground="#e0e0e0", selectforeground="black")
        
        # Place entry inside canvas
        # Store ID for resizing
        self.scan_entry_window = search_container.create_window(20, 23, window=self.scan_entry, anchor="w", width=300) 

        # Draw rounded rect and handle resize
        def _draw_search_bg(e):
            search_container.delete("bg")
            w, h = e.width, e.height
            
            # --- Draw Background Image ---
            import PIL.ImageDraw as ImageDraw
            import PIL.Image as Image
            import PIL.ImageTk as ImageTk
            
            # Create rounded rect image
            img = Image.new("RGBA", (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((0, 0, w-1, h-1), radius=20, fill=POS_BG_WHITE, outline="#cccccc", width=2)
            
            self._search_bg_img = ImageTk.PhotoImage(img) # Keep ref
            search_container.create_image(0,0, image=self._search_bg_img, anchor="nw", tags="bg")
            search_container.tag_lower("bg")
            
            # --- Resize Entry ---
            # Entry width = Container Width - Padding (Left 20 + Right 20 = 40)
            new_width = max(100, w - 40)
            search_container.itemconfigure(self.scan_entry_window, width=new_width)
            
        search_container.bind("<Configure>", _draw_search_bg)   
        
        # Placeholder logic
        self.scan_placeholder = "Buscar producto o escanear código..."
        self._setup_placeholder(self.scan_entry, self.scan_placeholder)
        
        self.scan_entry.bind("<Return>", self.handle_scan)
        self.scan_entry.bind("<KP_Enter>", self.handle_scan)
        self.scan_var.trace_add("write", self._on_scan_input)
        
        # --- PRODUCTS SECTION ---
        # Banner with Gradient
        prod_banner = GradientFrame(left_frame, color1="#0a2240", color2="#007bff", height=40, text="PRODUCTOS", shadow_color="#000000")
        prod_banner.grid(row=3, column=0, sticky="ew")

        # --- Products (Center - Scrollable, White Background) ---
        # Container for canvas to have white bg
        products_container_bg = tk.Frame(left_frame, bg=POS_BG_WHITE)
        products_container_bg.grid(row=4, column=0, sticky="nsew")
        products_container_bg.rowconfigure(0, weight=1)
        products_container_bg.columnconfigure(0, weight=1)

        canvas = tk.Canvas(products_container_bg, background=POS_BG_WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(products_container_bg, orient="vertical", command=canvas.yview)
        
        self.product_grid_frame = tk.Frame(canvas, bg=POS_BG_WHITE) # Use Tk Frame for bg white
        
        # 1. Store window_id to resize it
        self.grid_window_id = canvas.create_window((0, 0), window=self.product_grid_frame, anchor="nw")
        
        # 2. Resize frame when canvas resizes
        def _on_canvas_configure(event):
             canvas.itemconfig(self.grid_window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # 3. Reflow columns when frame width changes
        self.product_grid_frame.bind("<Configure>", self._on_grid_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1) # 1px padding to show border if any
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))
        
        self.products_canvas = canvas

    def _create_rounded_combobox(self, parent, variable, values=None, bg_color=None):
        # Determine background color logic if not provided
        if bg_color is None:
            bg_color = self._get_real_bg(parent)

        container = tk.Canvas(parent, bg=bg_color, height=40, highlightthickness=0)
        container.pack(fill="x", pady=5)
        
        # Ensure Borderless Style for Combobox
        style = ttk.Style.get_instance()
        style.configure('Borderless.TCombobox', borderwidth=0, relief='flat', arrowsize=15, foreground=POS_TEXT_COLOR)
        style.map('Borderless.TCombobox', 
                  fieldbackground=[('readonly',POS_BG_WHITE), ('active', POS_BG_WHITE)],
                  background=[('readonly',POS_BG_WHITE), ('active', POS_BG_WHITE)],
                  foreground=[('readonly',POS_TEXT_COLOR), ('active', POS_TEXT_COLOR)],
                  bordercolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)],
                  lightcolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)],
                  darkcolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)])

        combo = ttk.Combobox(container, textvariable=variable, state="readonly", values=values, style='Borderless.TCombobox', font=(FONT_FAMILY, 12))
        
        # Window in Canvas
        win_id = container.create_window(15, 20, window=combo, anchor="w", width=200)
        
        # Draw Rounded Rect background
        def _draw_bg(e):
            container.delete("bg")
            w, h = e.width, e.height
            
            # Draw Rounded Rect
            import PIL.ImageDraw as ImageDraw
            import PIL.Image as Image
            import PIL.ImageTk as ImageTk
            
            # Use same bg_color for image background to avoid white corners
            # Tkinter color to RGB
            try:
                # Basic hex handling or default to white if complex
                if bg_color.startswith("#"):
                    bg_fill_outer = bg_color
                else:
                    # simpler fallback
                    bg_fill_outer = POS_BG_WHITE 
                    # If we really want to match system colors (like 'systemWindowBody'), PIL needs RGB.
                    # For now only hex works reliably with this manual method. 
                    # If it's a named color, it might be white.
                    pass
            except:
                bg_fill_outer = "white"
                
            img = Image.new("RGBA", (w, h), (0,0,0,0)) # Transparent base
            draw = ImageDraw.Draw(img)
            
            # Draw Rounded Rect (White inside, Gray Outline)
            draw.rounded_rectangle((0, 0, w-1, h-1), radius=15, fill=POS_BG_WHITE, outline="#cccccc", width=1)
            
            bg_img = ImageTk.PhotoImage(img)
            container._bg_img_ref = bg_img 
            container.create_image(0,0, image=bg_img, anchor="nw", tags="bg")
            container.tag_lower("bg")
            
            # Resize Combo
            new_w = max(50, w - 30)
            container.itemconfigure(win_id, width=new_w)
            
        container.bind("<Configure>", _draw_bg)
        return combo

    def _create_rounded_entry(self, parent, variable, bg_color=None):
        # Determine background color logic if not provided
        if bg_color is None:
            bg_color = self._get_real_bg(parent)

        container = tk.Canvas(parent, bg=bg_color, height=40, highlightthickness=0)
        container.pack(fill="x", pady=5)
        
        # Ensure Borderless Style for Entry
        style = ttk.Style.get_instance()
        style.configure('Borderless.TEntry', fieldbackground=POS_BG_WHITE, foreground=POS_TEXT_COLOR, borderwidth=0, relief='flat', highlightthickness=0)
        style.map('Borderless.TEntry', 
                  fieldbackground=[('focus',POS_BG_WHITE), ('!disabled', POS_BG_WHITE)],
                  foreground=[('focus',POS_TEXT_COLOR), ('!disabled', POS_TEXT_COLOR)],
                  bordercolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)],
                  lightcolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)],
                  darkcolor=[('focus', POS_BG_WHITE), ('!disabled', POS_BG_WHITE)])

        entry = ttk.Entry(container, textvariable=variable, font=(FONT_FAMILY, 12), style='Borderless.TEntry')
        
        # Window in Canvas
        win_id = container.create_window(15, 20, window=entry, anchor="w", width=200)
        
        def _draw_bg(e):
            container.delete("bg")
            w, h = e.width, e.height
            
            # Draw Rounded Rect
            import PIL.ImageDraw as ImageDraw
            import PIL.Image as Image
            import PIL.ImageTk as ImageTk
            
            img = Image.new("RGBA", (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            # Gray Outline, White fill
            draw.rounded_rectangle((0, 0, w-1, h-1), radius=15, fill=POS_BG_WHITE, outline="#cccccc", width=1)
            
            bg_img = ImageTk.PhotoImage(img)
            container._bg_img_ref = bg_img 
            container.create_image(0,0, image=bg_img, anchor="nw", tags="bg")
            container.tag_lower("bg")
            
            # Resize
            new_w = max(50, w - 30)
            container.itemconfigure(win_id, width=new_w)
            
        container.bind("<Configure>", _draw_bg)
        return entry

    def setup_right_pane(self):
        # Right Pane Container
        right_frame = ttk.Frame(self, style='Sidebar.TFrame', padding=15)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Ensure it doesn't expand indefinitely
        right_frame.pack_propagate(False) 
        right_frame.grid_propagate(False) 
        
        right_frame.rowconfigure(2, weight=1) # Cart area expands
        right_frame.columnconfigure(0, weight=1)
        
        # --- Header Info (Empresa + Arqueo) ---
        header_row = ttk.Frame(right_frame, style='Sidebar.TFrame')
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        # "Empresa" Label
        ttk.Label(header_row, text="Empresa", font=(FONT_FAMILY, 12, "bold"), foreground=POS_TEXT_COLOR, background=POS_BG_WHITE, style='Sidebar.TLabel').pack(side="left")
        
        # "ARQUEO DE CAJA" Button
        arqueo_btn = GradientButton(header_row, text="ARQUEO DE CAJA", width=150, height=35, 
                                    color1="#0a2240", color2="#003366", 
                                    command=self.open_cash_count, corner_radius=15)
        arqueo_btn.pack(side="right")
        
        # Config Section (Dropdowns)
        config_frame = ttk.Frame(right_frame, style='Sidebar.TFrame')
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Issuer Combo (Rounded)
        self.issuer_combo = self._create_rounded_combobox(config_frame, self.issuer_var)
        self.issuer_combo.bind("<<ComboboxSelected>>", self.on_issuer_select)
        
        # Address Combo (Rounded)
        self.address_combo = self._create_rounded_combobox(config_frame, self.address_var)
        self.address_combo.bind("<<ComboboxSelected>>", self.on_address_select)
        
        # --- Cart (Treeview) ---
        # Container
        cart_container = tk.Frame(right_frame, bg=POS_BG_WHITE, bd=0) 
        cart_container.grid(row=2, column=0, sticky="nsew")
        cart_container.rowconfigure(0, weight=1)
        cart_container.columnconfigure(0, weight=1)
        
        # Configure Interleaved Rows
        style = ttk.Style()
        style.configure("Cart.Treeview.Heading", background=POS_PRIMARY_DARK, foreground="white", font=(FONT_FAMILY, 9, "bold"), relief="flat")
        style.configure("Cart.Treeview", font=(FONT_FAMILY, 10), rowheight=30, borderwidth=0)
        style.map("Cart.Treeview", background=[('selected', '#2c3e50')], foreground=[('selected', 'white')])
        
        self.cart_tree = ttk.Treeview(cart_container, columns=("producto", "cantidad", "precio", "subtotal"), show="headings", style="Cart.Treeview")
        self.cart_tree.heading("producto", text="Producto")
        self.cart_tree.heading("cantidad", text="Cant.")
        self.cart_tree.heading("precio", text="P.Unit.")
        self.cart_tree.heading("subtotal", text="Total")
        
        # Tags for colors
        if POS_BG_WHITE == "#ffffff":
            self.cart_tree.tag_configure('oddrow', background='#f2f2f2', foreground='black')
            self.cart_tree.tag_configure('evenrow', background='white', foreground='black')
        else:
            # Dark Mode
            self.cart_tree.tag_configure('oddrow', background='#32383E', foreground='white')
            self.cart_tree.tag_configure('evenrow', background='#252A2E', foreground='white')
        
        # Fix column widths to prevent automatic expansion affecting layout
        self.cart_tree.column("producto", width=140, minwidth=100, stretch=True) # Product creates width
        self.cart_tree.column("cantidad", width=50, minwidth=40, anchor="center", stretch=False)
        self.cart_tree.column("precio", width=70, minwidth=60, anchor="e", stretch=False)
        self.cart_tree.column("subtotal", width=70, minwidth=60, anchor="e", stretch=False)
        
        self.cart_tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        
        # Scrollbar
        cart_scroll = ttk.Scrollbar(cart_container, orient="vertical", command=self.cart_tree.yview)
        cart_scroll.grid(row=0, column=1, sticky="ns")
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)

        self.cart_tree.bind("<Double-1>", self.on_cart_double_click)

        
        # --- Totals & Actions ---
        bottom_frame = ttk.Frame(right_frame, style='Sidebar.TFrame')
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)
        
        # Totals Row
        footer_container = ttk.Frame(bottom_frame, style='Sidebar.TFrame')
        footer_container.pack(fill="x", pady=10)
        
        # 1. Totals Row (Grid Layout: Items | Dscto/Recargo | Total)
        totals_row = ttk.Frame(footer_container, style='Sidebar.TFrame')
        totals_row.pack(fill="x", pady=(0, 15), padx=5)
        
        totals_row.columnconfigure(0, weight=1) # Items
        totals_row.columnconfigure(1, weight=1) # Dscto
        totals_row.columnconfigure(2, weight=1) # Total
        
        # --- ITEMS ---
        items_frame = ttk.Frame(totals_row, style='Sidebar.TFrame')
        items_frame.grid(row=0, column=0, sticky="w")
        ttk.Label(items_frame, text="ITEMS:", font=(FONT_FAMILY, 10, "bold"), foreground="#aaa", style='Sidebar.TLabel').pack(side="left")
        self.total_items_value = ttk.Label(items_frame, text="0", font=(FONT_FAMILY, 11, "bold"), foreground=POS_TEXT_COLOR, style='Sidebar.TLabel')
        self.total_items_value.pack(side="left", padx=(5, 0))

        # --- DISCOUNT / SURCHARGE ---
        # We will share this spot. Static "DSCTO" usually.
        self.frame_discount = ttk.Frame(totals_row, style='Sidebar.TFrame')
        self.frame_discount.grid(row=0, column=1, sticky="ew") # Center alignment
        
        # We'll use a single visible frame, and toggle text/color if it's a Surcharge?
        # User asked specifically for "DSCTO". I will show "DSCTO" always.
        # If there is a surcharge, maybe show it here too?
        # Construct specific labels.
        self.discount_label_title = ttk.Label(self.frame_discount, text="DSCTO:", font=(FONT_FAMILY, 10, "bold"), foreground="#aaa", style='Sidebar.TLabel')
        self.discount_label_title.pack(side="left")
        self.discount_value = ttk.Label(self.frame_discount, text="S/ 0.00", font=(FONT_FAMILY, 11, "bold"), foreground=POS_TEXT_COLOR, style='Sidebar.TLabel')
        self.discount_value.pack(side="left", padx=(5, 0))
        
        # Keep reference to surcharge widget just in case logic needs it, but maybe repack it?
        # Current logic expects self.frame_surcharge and self.surcharge_value.
        # I'll keep them but usually hidden, or repurpose spacing?
        # User didn't ask for Surcharge. I will hide Surcharge by default.
        self.frame_surcharge = ttk.Frame(totals_row, style='Sidebar.TFrame')
        # self.frame_surcharge.grid(row=0, column=1) # Don't grid initially. Logic handles it?
        # Logic packs it. I need to change logic to GRID it if I use grid.
        # For now, I'll ensure Discount is visible.
        
        # --- TOTAL ---
        total_frame = ttk.Frame(totals_row, style='Sidebar.TFrame')
        total_frame.grid(row=0, column=2, sticky="e")
        ttk.Label(total_frame, text="TOTAL:", font=(FONT_FAMILY, 14, "bold"), foreground=POS_TEXT_COLOR, style='Sidebar.TLabel').pack(side="left", padx=(0, 5))
        self.total_value = ttk.Label(total_frame, text="S/ 0.00", font=(FONT_FAMILY, 18, "bold"), foreground=POS_TEXT_COLOR, style='Sidebar.TLabel')
        self.total_value.pack(side="left")

        # Keep surcharge value ref for safety (updates won't crash)
        self.surcharge_value = ttk.Label(self.frame_surcharge, text="S/ 0.00")

        self.stock_label = ttk.Label(self) # Unused or keeping reference

        # 2. Action Buttons Row
        actions_row = ttk.Frame(footer_container, style='Sidebar.TFrame')
        actions_row.pack(fill="x", pady=(0, 10))
        
        # Use Grid for even spacing
        actions_row.columnconfigure(0, weight=1)
        actions_row.columnconfigure(1, weight=1)
        
        # Eliminar: Red Gradient, Red Border, White Text
        btn_del = GradientButton(actions_row, text="ELIMINAR", command=self.remove_from_cart,
                                 color1="#dc3545", color2="#bd2130", text_color="white",
                                 border_color="#dc3545", corner_radius=10, height=40, icon="🗑️")
        btn_del.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Limpiar: Dark Gray Gradient, Gray Border, White Text
        btn_clear = GradientButton(actions_row, text="LIMPIAR TODO", command=self.reset_system,
                                   color1="#5a6268", color2="#4e555b", text_color="white",
                                   border_color="#545b62", corner_radius=10, height=40, icon="🧹")
        btn_clear.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        # 3. Big Pay Button (Gradient Green/Blue)
        # Font increased +1 (logic level) -> 12
        pay_btn = GradientButton(footer_container, text="COBRAR", command=self.show_payment_modal,
                                 color1="#28a745", color2="#218838", text_color="white",
                                 corner_radius=15, height=60, icon="💳", font_size=12)
        pay_btn.pack(fill="x", pady=(10, 0))

    def load_products_from_db(self, issuer_name=None, issuer_address=None):
        all_products_rows = database.get_all_products(issuer_name, issuer_address)
        # row: id, name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category
        
        self.products = {}
        self.products_by_category = {}
        # Clear cache for polling
        self._id_to_product_map = {}
        
        for row in all_products_rows:
            p_id, name, price, stock, code, um, op_type, i_name, i_addr, category, image, is_active = row
            category = category or "General"
            
            product_data = {
                'id': p_id, 'name': name, 'price': price, 'stock': stock, 
                'code': code, 'unit_of_measure': um, 'category': category,
                'image': image
            }
            self.products[name] = product_data
            
            if category not in self.products_by_category:
                self.products_by_category[category] = []
            self.products_by_category[category].append(product_data)
            
        # --- CRITICAL FIX: Sync Local Memory Stock with Current Cart ---
        # When reloading from DB, we get raw stock. We must subtract what is currently in OUR cart.
        if hasattr(self, 'cart') and self.cart:
            for item in self.cart:
                p_name = item.get('name')
                if p_name and p_name in self.products:
                    qty = item.get('quantity', 0)
                    self.products[p_name]['stock'] -= qty
        
        # Also Check Persistent State if Cart is Empty (Initial Load Case)
        # If this is a fresh window, self.cart might be empty, but sales_state.json has data.
        # We should logically restore the cart here if needed, OR relies on another loader.
        # To be safe for "Stock Sync", we look at state file to see if WE have items.
        # But populating self.cart has side effects (UI treeview). We shouldn't do it implicitly here unless standard.
        # Assuming User's "Cart has items" means 'self.cart' is populated.
        
        self.refresh_category_buttons()
        self.refresh_category_buttons()
        # User requested NO pre-selected group in Touch Mode
        self.show_products_for_category(None)
        
        # --- Create Code Map for Scanning ---
        self.product_code_map = {}
        for name, data in self.products.items():
            code = data.get('code')
            if code:
                code_str = str(code).strip()
                if code_str:
                     self.product_code_map[code_str] = name

        # Start Polling for Stock Updates (Auto-Sync)
        if hasattr(self, 'start_stock_polling'):
            self.start_stock_polling()
            
        # Ensure focus returns to scan entry after reload
        if hasattr(self, 'scan_entry'):
             self.scan_entry.focus_set()

    def refresh_category_buttons(self):
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()
            
        categories = sorted(list(self.products_by_category.keys()))
        
        # Apply saved order
        ordered_categories = []
        # First add categories that are in the saved order and exist in current products
        for cat in self.group_order:
            if cat in categories:
                ordered_categories.append(cat)
        
        # Then add any new categories that are not in the saved order
        for cat in categories:
            if cat not in ordered_categories:
                ordered_categories.append(cat)
        
        # Update self.group_order to reflect current reality (including new categories)
        self.group_order = ordered_categories
        
        # Assign styles to categories
        for i, cat in enumerate(ordered_categories):
             # We just need the index to determine the style
             pass
        
        self.save_group_order()
        
        total_pages = (len(ordered_categories) + self.categories_per_page - 1) // self.categories_per_page
        
        # Ensure current page is valid
        if self.current_category_page >= total_pages:
            self.current_category_page = 0
            
        start_index = self.current_category_page * self.categories_per_page
        end_index = start_index + self.categories_per_page
        current_categories = ordered_categories[start_index:end_index]
        
        # Grid layout for categories (2 rows, 7 columns)
        columns_per_row = 7
        for i, cat in enumerate(current_categories):
            row = i // columns_per_row
            col = i % columns_per_row
            
            # Determine global index for color consistency and gradient style
            try:
                cat_global_idx = self.group_order.index(cat)
            except ValueError:
                cat_global_idx = i
            
            custom_color = getattr(self, 'group_colors', {}).get(cat)
            if custom_color:
                 base_color = custom_color
                 # Auto-adjust text color for custom background if needed?
                 # For now assume white text for custom colors as they are usually dark/vibrant
            else:
                 # Decouple color from order: Use Name Hash for consistent color
                 # style_idx = cat_global_idx % len(POS_GRP_COLORS) 
                 # Use sum of chars for stable determinism
                 style_idx = sum(ord(c) for c in cat) % len(POS_GRP_COLORS)
                 base_color = POS_GRP_COLORS[style_idx]
            
            # Create GradientButton for Group
            # Darken base color slightly for gradient effect
            def darken(hex_c, factor=0.8):
                # Basic mapping if needed, or just let GradientButton auto-darken if we pass same color
                # But GradientButton takes color1, color2.
                # Let's pass the same color and let it auto-manage or just pass something compatible.
                # We can try to darken custom.
                return hex_c
            
            btn = GradientButton(
                self.category_frame,
                text=cat,
                command=lambda c=cat: self.show_products_for_category(c),
                color1=base_color,
                color2=base_color, # It will look flat-ish or we can improve logic. GradientButton._draw handles hover/press.
                width=100, # Approx
                height=50,
                corner_radius=10,
                text_color="white"
            )

            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            
            # Bind Drag and Drop events
            btn.bind("<ButtonPress-1>", lambda e, c=cat, b=btn: self.start_drag(e, c, b, "category"))
            # Note: Motion and Release are bound globally in start_drag
            
            # Context Menu
            btn.bind("<Button-3>", lambda e, c=cat: self.show_group_context_menu(e, c))
            
            self.category_frame.columnconfigure(col, weight=1)

        # Pagination Controls
        if total_pages > 1:
            page_container = ttk.Frame(self.pagination_frame)
            page_container.pack(anchor="center")
            
            for p in range(total_pages):
                is_active = (p == self.current_category_page)
                
                # Active: Blue gradient
                # Inactive: White/Gray gradient with border
                # Active: Gradient matched to headers (#0a2240 -> #007bff)
                # Inactive: White/Gray with Navy border
                if is_active:
                    c1 = "#0a2240"
                    c2 = "#007bff"
                    txt_color = "white"
                    border = None
                else:
                    if POS_BG_WHITE == "#ffffff":
                        c1 = "white"
                        c2 = "#e0e0e0" 
                        txt_color = "#333333" 
                        border = "#666666" 
                    else:
                        # Dark Mode Inactive
                        c1 = POS_BG_WHITE # Dark Gray
                        c2 = POS_PRIMARY_LIGHT # Slightly different dark
                        txt_color = "white"
                        border = "#666666"

                btn = GradientButton(
                    page_container,
                    text=str(p + 1),
                    command=lambda page=p: self.change_category_page(page),
                    color1=c1,
                    color2=c2,
                    text_color=txt_color,
                    border_color=border,
                    width=40,
                    height=40,
                    corner_radius=20 # Fully rounded
                )
                btn.pack(side="left", padx=2)
                
                # Bind hover event for page switching during drag
                btn.bind("<Enter>", lambda e, page=p: self.on_page_hover(e, page))

    def change_category_page(self, page):
        if self.current_category_page == page:
            return
        self.current_category_page = page
        self.refresh_category_buttons()


    def _on_grid_configure(self, event):
        # Update scrollregion
        try:
            self.products_canvas.configure(scrollregion=self.products_canvas.bbox("all"))
        except: return

        # Debounced reflow
        width = event.width
        if width < 100: return
        
        new_cols = max(4, int(width / 185))
        
        if not hasattr(self, 'last_cols'):
            self.last_cols = -1
        
        if new_cols != self.last_cols:
             self.last_cols = new_cols
             # Trigger reload if category selected
             if hasattr(self, 'current_category') and self.current_category:
                 if hasattr(self, '_reflow_job') and self._reflow_job:
                     self.after_cancel(self._reflow_job)
                 
                 self._reflow_job = self.after(200, lambda: self.show_products_for_category(self.current_category))

    def show_group_context_menu(self, event, category):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Cambiar Color", command=lambda: self.change_group_color(category))
        menu.post(event.x_root, event.y_root)

    def change_group_color(self, category):
        color = askcolor(title=f"Color para {category}", parent=self)[1]
        if color:
            if not hasattr(self, 'group_colors'):
                self.group_colors = {}
            self.group_colors[category] = color
            self.save_group_order()
            self.refresh_category_buttons()

    def show_product_context_menu(self, event, product_data):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Cambiar Color", command=lambda: self.change_product_color(product_data))
        menu.post(event.x_root, event.y_root)

    def change_product_color(self, product_data):
        p_id = str(product_data['id'])
        color = askcolor(title=f"Color para {product_data['name']}", parent=self)[1]
        if color:
            self.product_colors[p_id] = color
            self.save_product_order()
            # Refresh current category view
            current_cat = product_data.get('category')
            self.show_products_for_category(current_cat)

    # --- Drag and Drop Logic ---
    def start_drag(self, event, item_data, widget, item_type="category"):
        # Cleanup any existing drag window
        if hasattr(self, 'drag_window') and self.drag_window:
            self.drag_window.destroy()
            
        # Initialize drag data but don't start visual drag yet (wait for threshold)
        self.drag_data = {
            "item_data": item_data, 
            "widget": widget, 
            "item_type": item_type,
            "start_x": event.x_root, 
            "start_y": event.y_root,
            "is_dragging": False
        }
        
        # Bind global drag events to toplevel
        root = self.winfo_toplevel()
        self._drag_motion_id = root.bind("<B1-Motion>", self.on_drag, add='+')
        self._drag_release_id = root.bind("<ButtonRelease-1>", self.end_drag, add='+')

    def on_drag(self, event):
        if not hasattr(self, 'drag_data'):
            return

        # Check threshold if not yet dragging
        if not self.drag_data["is_dragging"]:
            if abs(event.x_root - self.drag_data["start_x"]) > 5 or abs(event.y_root - self.drag_data["start_y"]) > 5:
                self.drag_data["is_dragging"] = True
                # Create visual feedback now
                self.drag_window = tk.Toplevel(self)
                self.drag_window.overrideredirect(True)
                self.drag_window.attributes("-alpha", 0.7)
                
                text = self.drag_data["item_data"] if self.drag_data["item_type"] == "category" else self.drag_data["item_data"]["name"]
                lbl = ttk.Label(self.drag_window, text=text, bootstyle="inverse-primary", padding=5)
                lbl.pack()
                self.drag_window.geometry(f"+{event.x_root}+{event.y_root}")
            else:
                return # Still within threshold, treat as potential click

        # Update drag window position
        if hasattr(self, 'drag_window'):
            self.drag_window.geometry(f"+{event.x_root}+{event.y_root}")
            
            # Check for page switching
            x, y = self.category_frame.winfo_pointerxy()
            # winfo_containing might return the label inside the button, so we need to be careful
            widget_under_mouse = self.winfo_containing(x, y)
            
            # Check if we are hovering over a pagination button
            # We need a way to identify pagination buttons. 
            # We can check if their parent is self.pagination_frame or a child of it.
            if widget_under_mouse:
                # Traverse up to find if it belongs to pagination_frame
                parent = widget_under_mouse
                is_pagination = False
                page_number = -1
                
                # Limit traversal depth
                for _ in range(4):
                    if not parent: break
                    if parent == self.pagination_frame:
                         # Mouse is inside the pagination frame hierarchy (e.g. over a button)
                         # Iterate all buttons to match coordinates (Robust Check)
                         x_root, y_root = event.x_root, event.y_root
                         # Collect potential buttons (including those in containers)
                         candidates = []
                         # Direct children
                         candidates.extend(self.pagination_frame.winfo_children())
                         # Grandchildren (assuming 1 level of nesting works for page_container)
                         for child in self.pagination_frame.winfo_children():
                             if isinstance(child, (tk.Frame, ttk.Frame)):
                                 candidates.extend(child.winfo_children())
                         
                         for btn in candidates:
                             if not isinstance(btn, (tk.Widget, tk.Canvas)): continue
                             try:
                                 # Expand hit area by 10 pixels for easier interaction
                                 bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                                 bw, bh = btn.winfo_width(), btn.winfo_height()
                                 pad = 10 
                                 if (bx - pad) <= x_root <= (bx + bw + pad) and (by - pad) <= y_root <= (by + bh + pad):
                                      txt = btn.cget("text")
                                      if txt and str(txt).isdigit():
                                          page_number = int(txt) - 1
                                          is_pagination = True
                                          break
                             except:
                                 pass
                         break
                    # Also check if the widget itself is the button in the page_container
                    # The structure is pagination_frame -> page_container -> buttons
                    if isinstance(parent, ttk.Frame) and parent.master == self.pagination_frame:
                         # This is likely the page_container
                         pass
                    
                    parent = parent.master
                
                if is_pagination and page_number != -1:
                    if self.current_category_page != page_number:
                        self.change_category_page(page_number)
                        
                        # Auto-select first category of new page to show products immediately
                        # This allows user to drop on a product right after page switch
                        try:
                            if hasattr(self, 'categories_per_page') and hasattr(self, 'group_order'):
                                start_idx = page_number * self.categories_per_page
                                if start_idx < len(self.group_order):
                                    first_cat = self.group_order[start_idx]
                                    self.show_products_for_category(first_cat)
                        except: pass
                
                # --- Category Hover Switch (For Product Drag) ---
                if self.drag_data["item_type"] == "product":
                     # Check if hovering a Category Button
                     x_root, y_root = event.x_root, event.y_root
                     hovered_cat = None
                     
                     if hasattr(self, 'category_frame'):
                         for btn in self.category_frame.winfo_children():
                              if not isinstance(btn, (tk.Widget, tk.Canvas)): continue
                              if not btn.winfo_viewable(): continue
                              try:
                                  bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                                  bw, bh = btn.winfo_width(), btn.winfo_height()
                                  pad = 5
                                  if (bx - pad) <= x_root <= (bx + bw + pad) and (by - pad) <= y_root <= (by + bh + pad):
                                      hovered_cat = btn.cget("text")
                                      break
                              except: pass
                     
                     if hovered_cat:
                          # Only switch if not already current
                          if getattr(self, 'current_category', '') != hovered_cat:
                              current_hover = getattr(self, '_hover_cat_target', None)
                              if current_hover != hovered_cat:
                                   self._hover_cat_target = hovered_cat
                                   if hasattr(self, '_hover_cat_job') and self._hover_cat_job: 
                                       self.after_cancel(self._hover_cat_job)
                                   
                                   def switch_cat():
                                        if getattr(self, '_hover_cat_target', None) == hovered_cat:
                                             self.show_products_for_category(hovered_cat)
                                   
                                   self._hover_cat_job = self.after(500, switch_cat)
                     else:
                          self._hover_cat_target = None
                          if hasattr(self, '_hover_cat_job') and self._hover_cat_job:
                               self.after_cancel(self._hover_cat_job)
                               self._hover_cat_job = None

    def on_page_hover(self, event, page):
        # Deprecated: Logic moved to on_drag for better reliability
        pass

    def end_drag(self, event):
        # Unbind global events
        root = self.winfo_toplevel()
        if hasattr(self, '_drag_motion_id'):
            root.unbind("<B1-Motion>", self._drag_motion_id)
            del self._drag_motion_id
        if hasattr(self, '_drag_release_id'):
            root.unbind("<ButtonRelease-1>", self._drag_release_id)
            del self._drag_release_id

        # Check if it was a click (not dragging)
        if hasattr(self, 'drag_data') and not self.drag_data["is_dragging"]:
            # It was a click!
            # Actions are handled by the button's native command event (GradientButton._on_release).
            # We don't need to call them here to avoid double execution.
            # if self.drag_data["item_type"] == "category":
            #    self.show_products_for_category(self.drag_data["item_data"])
            # elif self.drag_data["item_type"] == "product":
            #    self.add_product_to_cart(self.drag_data["item_data"])
            
            # Clean up
            if hasattr(self, 'drag_window'):
                self.drag_window.destroy()
                del self.drag_window
            del self.drag_data
            
            # FORCE FOCUS AWAY after click
            if hasattr(self, 'scan_entry'):
                 self.scan_entry.focus_set()
            return

        if hasattr(self, 'drag_window'):
            self.drag_window.destroy()
            del self.drag_window
            
            # Finalize the drop
            item_type = self.drag_data["item_type"]
            
            if item_type == "category":
                x, y = self.category_frame.winfo_pointerxy()
                target_category = None
                
                # Robust geometric check over current visible buttons - CLOSEST MATCH
                min_dist = 100000
                closest_cat = None
                cat_threshold = 100
                
                for btn in self.category_frame.winfo_children():
                     if not isinstance(btn, (tk.Widget, tk.Canvas)): continue
                     if not btn.winfo_viewable(): continue
                     
                     try:
                         bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                         bw, bh = btn.winfo_width(), btn.winfo_height()
                         cx, cy = bx + bw/2, by + bh/2
                         
                         dist = ((x - cx)**2 + (y - cy)**2)**0.5
                         if dist < min_dist and dist < cat_threshold:
                             min_dist = dist
                             closest_cat = btn.cget("text")
                     except: pass
                
                target_category = closest_cat
                
                if target_category and target_category != self.drag_data["item_data"]:
                     # Swap/Move
                    try:
                        # Move element (Pop first ensures insertion BEFORE target)
                        item_val = self.drag_data["item_data"]
                        if item_val in self.group_order:
                            self.group_order.remove(item_val)
                            
                            if target_category in self.group_order:
                                idx2 = self.group_order.index(target_category)
                                self.group_order.insert(idx2, item_val)
                            else:
                                self.group_order.append(item_val)
                        
                        self.save_group_order()
                        self.refresh_category_buttons()
                    except ValueError:
                        pass # Category not found?
            
            elif item_type == "product":
                start_x, start_y = x, y = self.winfo_pointerxy() # Global pointer
                target_p_id = None
                
                # 1. Try to find Target Product (Reorder/Insert)
                # Robust geometric check over known product buttons
                # 1. Try to find Target Product (Reorder/Insert) - EXPANDED RECT MATCH
                min_dist = 100000
                closest_p = None
                
                for p_id, btn in self.product_buttons.items():
                    try:
                         if not btn.winfo_viewable(): continue
                         bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                         bw, bh = btn.winfo_width(), btn.winfo_height()
                         
                         # Check "Generous" Rectangle (50% expansion) matches user intent better than circle
                         pad_x = bw * 0.5
                         pad_y = bh * 0.5
                         
                         if (bx - pad_x) <= x <= (bx + bw + pad_x) and (by - pad_y) <= y <= (by + bh + pad_y):
                             # Valid Candidate. Check distance to center for tie-breaking.
                             cx, cy = bx + bw/2, by + bh/2
                             dist = ((x - cx)**2 + (y - cy)**2)**0.5
                             
                             if dist < min_dist:
                                 min_dist = dist
                                 closest_p = str(p_id)
                    except: pass
                
                target_p_id = closest_p
                
                # 2. If NO Product target found, Check Category Buttons (Move to Category) - CLOSEST MATCH
                target_cat_drop = None
                if target_p_id is None and hasattr(self, 'category_frame'):
                     min_dist_cat = 100000
                     closest_cat = None
                     cat_threshold = 100
                     
                     for btn in self.category_frame.winfo_children():
                          if not isinstance(btn, (tk.Widget, tk.Canvas)): continue
                          if not btn.winfo_viewable(): continue
                          try:
                              bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                              bw, bh = btn.winfo_width(), btn.winfo_height()
                              
                              # Expanded Rectangle
                              pad_x = bw * 0.5
                              pad_y = bh * 0.5
                              
                              if (bx - pad_x) <= x <= (bx + bw + pad_x) and (by - pad_y) <= y <= (by + bh + pad_y):
                                  cx, cy = bx + bw/2, by + bh/2
                                  dist = ((x - cx)**2 + (y - cy)**2)**0.5
                                  if dist < min_dist_cat:
                                      min_dist_cat = dist
                                      closest_cat = btn.cget("text")
                          except: pass
                     target_cat_drop = closest_cat
                
                current_p_id = str(self.drag_data["item_data"]['id'])
                source_cat = self.drag_data["item_data"]['category']
                
                # Identify Target Category
                target_cat = source_cat
                if target_cat_drop:
                    target_cat = target_cat_drop
                elif hasattr(self, 'current_category') and self.current_category:
                     target_cat = self.current_category

                if target_cat != source_cat:
                     # Check for Cross-Category Move
                     try:
                         # 1. Update internal data structures
                         # Remove from source
                         if source_cat in self.product_order and current_p_id in self.product_order[source_cat]:
                              self.product_order[source_cat].remove(current_p_id)
                         
                         if source_cat in self.products_by_category:
                              self.products_by_category[source_cat] = [p for p in self.products_by_category[source_cat] if str(p['id']) != current_p_id]

                         # Add to target
                         if target_cat not in self.product_order: self.product_order[target_cat] = []
                         
                         t_list = self.product_order[target_cat]
                         if target_p_id and target_p_id in t_list:
                              t_list.insert(t_list.index(target_p_id), current_p_id)
                         else:
                              # Append if dropped on Category Button or empty space in new cat
                              t_list.append(current_p_id)
                         
                         # Update Object
                         p_data = self.drag_data["item_data"]
                         p_data['category'] = target_cat
                         
                         if target_cat not in self.products_by_category: self.products_by_category[target_cat] = []
                         self.products_by_category[target_cat].append(p_data)
                         
                         # Update Main Dict
                         if p_data['name'] in self.products:
                              self.products[p_data['name']]['category'] = target_cat

                         # 2. Persist Order
                         self.save_product_order()
                         
                         # 3. Persist Category Change to DB (Best Effort)
                         try:
                             import database
                             # Assuming update_product_category exists or executing update
                             conn = database.create_connection()
                             cur = conn.cursor()
                             cur.execute("UPDATE products SET category = ? WHERE id = ?", (target_cat, current_p_id))
                             conn.commit()
                             conn.close()
                         except: pass

                         self.show_products_for_category(target_cat)
                         messagebox.showinfo("Movido", f"Producto movido a {target_cat}", parent=self)
                     except Exception as e:
                         print(f"Error moving product: {e}")

                else:
                    # Same Category Reorder (target_cat == source_cat)
                    if source_cat in self.product_order:
                        order_list = self.product_order[source_cat]
                        try:
                            item = current_p_id
                            if item in order_list:
                                 # Determine indices BEFORE removal
                                 curr_idx = order_list.index(item)
                                 
                                 if target_p_id and target_p_id in order_list:
                                     tgt_idx_orig = order_list.index(target_p_id)
                                     
                                     order_list.remove(item)
                                     
                                     # Determine insertion point
                                     # Find target again (index might shift)
                                     tgt_idx_new = order_list.index(target_p_id)
                                     
                                     if curr_idx < tgt_idx_orig:
                                         # Moving Right/Down: Insert AFTER target
                                         order_list.insert(tgt_idx_new + 1, item)
                                     else:
                                         # Moving Left/Up: Insert BEFORE target
                                         order_list.insert(tgt_idx_new, item)
                                 else:
                                     # Drop in empty space -> Append to end
                                     order_list.remove(item)
                                     order_list.append(item)
                            
                            self.save_product_order()
                            self.show_products_for_category(source_cat)
                        except ValueError:
                            pass
        
        if hasattr(self, 'drag_data'):
            del self.drag_data

    def on_cart_double_click(self, event):
        item_id = self.cart_tree.identify_row(event.y)
        column = self.cart_tree.identify_column(event.x)
        
        if not item_id:
            return
            
        # Column #2 is Quantity (columns are #1, #2, #3, #4 in treeview logic usually, but let's check)
        # Treeview columns are 1-indexed in identify_column returns "#1", "#2" etc.
        # Our columns are ("producto", "cantidad", "precio", "subtotal")
        # Display columns: #1=Product, #2=Quantity, #3=Price, #4=Total
        
        if column == "#2": # Quantity
            current_values = self.cart_tree.item(item_id)['values']
            product_name = current_values[0]
            current_qty = float(current_values[1])
            
            # Find item in self.cart
            cart_item = next((item for item in self.cart if item['name'] == product_name), None)
            
            if cart_item:
                self.ask_quantity(cart_item, item_id)
        
        elif column == "#3": # Price
            current_values = self.cart_tree.item(item_id)['values']
            product_name = current_values[0]
            
            # Find item in self.cart
            cart_item = next((item for item in self.cart if item['name'] == product_name), None)
            
            if cart_item:
                self.ask_price(cart_item, item_id)

    def ask_quantity(self, cart_item, tree_item_id):
        d = tk.Toplevel(self)
        d.title("Editar Cantidad")
        d.attributes("-toolwindow", True) # Disable min/max buttons
        d.resizable(False, False)
        
        # Center the window
        width = 400
        height = 250
        screen_width = d.winfo_screenwidth()
        screen_height = d.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        d.geometry(f"{width}x{height}+{x}+{y}")
        
        ttk.Label(d, text=f"Cantidad para {cart_item['name']}:", font=(FONT_FAMILY, 14)).pack(pady=20)
        qty_var = tk.DoubleVar(value=cart_item['quantity'])
        e = ttk.Entry(d, textvariable=qty_var, font=(FONT_FAMILY, 14), width=10, justify='center')
        e.pack(pady=10)
        e.focus_set()
        e.select_range(0, 'end')
        
        # Close on click outside
        # We bind to the main window. If a click occurs there, we close this dialog.
        main_window = self.winfo_toplevel()
        
        def close_on_outside_click(event):
            d.destroy()
            
        # Add the binding and store the id to unbind later
        bind_id = main_window.bind("<Button-1>", close_on_outside_click, add="+")
        
        def on_destroy(event):
            if event.widget == d:
                main_window.unbind("<Button-1>", bind_id)
        
        d.bind("<Destroy>", on_destroy)
        
        def confirm(event=None):
            try:
                new_qty = float(qty_var.get())
                if new_qty <= 0:
                    messagebox.showerror("Error", "La cantidad debe ser mayor a 0", parent=self)
                    return
                
                # Update cart
                cart_item['quantity'] = new_qty
                cart_item['subtotal'] = new_qty * cart_item['price']
                
                # Update tree
                self.cart_tree.item(tree_item_id, values=(
                    cart_item['name'], 
                    f"{new_qty:.2f}", 
                    f"{cart_item['price']:.2f}", 
                    f"{cart_item['subtotal']:.2f}"
                ))
                
                self.update_total()
                d.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingrese un número válido", parent=self)
        
        # Custom style for larger button if needed, or just use width/padding
        confirm_btn = ttk.Button(d, text="Aceptar", command=confirm, width=15, bootstyle="success")
        confirm_btn.pack(pady=20, ipady=5) # ipady for taller button
        d.bind('<Return>', confirm)

    def ask_price(self, cart_item, tree_item_id):
        d = tk.Toplevel(self)
        d.title("Editar Precio")
        d.attributes("-toolwindow", True) # Disable min/max buttons
        d.resizable(False, False)
        
        # Center the window
        width = 400
        height = 250
        screen_width = d.winfo_screenwidth()
        screen_height = d.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        d.geometry(f"{width}x{height}+{x}+{y}")
        
        ttk.Label(d, text=f"Precio para {cart_item['name']}:", font=(FONT_FAMILY, 14)).pack(pady=20)
        price_var = tk.DoubleVar(value=cart_item['price'])
        e = ttk.Entry(d, textvariable=price_var, font=(FONT_FAMILY, 14), width=10, justify='center')
        e.pack(pady=10)
        e.focus_set()
        e.select_range(0, 'end')
        
        # Close on click outside
        main_window = self.winfo_toplevel()
        
        def close_on_outside_click(event):
            d.destroy()
            
        bind_id = main_window.bind("<Button-1>", close_on_outside_click, add="+")
        
        def on_destroy(event):
            if event.widget == d:
                main_window.unbind("<Button-1>", bind_id)
        
        d.bind("<Destroy>", on_destroy)
        
        def confirm(event=None):
            try:
                new_price = float(price_var.get())
                if new_price < 0:
                    messagebox.showerror("Error", "El precio no puede ser negativo", parent=self)
                    return
                
                # Update cart
                cart_item['price'] = new_price
                cart_item['subtotal'] = cart_item['quantity'] * new_price
                
                # Update tree
                self.cart_tree.item(tree_item_id, values=(
                    cart_item['name'], 
                    f"{cart_item['quantity']:.2f}", 
                    f"{new_price:.2f}", 
                    f"{cart_item['subtotal']:.2f}"
                ))
                
                self.update_total()
                d.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingrese un precio válido", parent=self)
        
        confirm_btn = ttk.Button(d, text="Aceptar", command=confirm, width=15, bootstyle="success")
        confirm_btn.pack(pady=20, ipady=5)
        d.bind('<Return>', confirm)

    def show_products_for_category(self, category):
        # Clear previous buttons and references
        for widget in self.product_grid_frame.winfo_children():
            widget.destroy()
        self.product_buttons = {}
        self.product_image_refs = [] # Clear image refs
            
        self.current_category = category # Store for responsive update
        if not category or category not in self.products_by_category:
            return
            
        products = self.products_by_category[category]
        
        # Apply saved order
        ordered_products = []
        saved_order = self.product_order.get(category, [])
        
        # Add products in saved order
        for p_id in saved_order:
            # Find product data
            p_data = next((p for p in products if str(p['id']) == str(p_id)), None)
            if p_data:
                ordered_products.append(p_data)
        
        # Add remaining products
        for p in products:
            if p not in ordered_products:
                ordered_products.append(p)
                
        # Update self.product_order to reflect current reality
        self.product_order[category] = [str(p['id']) for p in ordered_products]
        self.save_product_order()
        
        products = ordered_products
        
        # Grid layout
        # Calculate columns dynamically
        width = self.product_grid_frame.winfo_width()
        if width <= 100: 
             # Approximation if not rendered yet
             s_width = self.winfo_screenwidth()
             # Left pane is approx 70% or split? 
             # SalesTouchView usually is full screen. Paned layout.
             width = s_width * 0.65 
        
        # Target button width approx 160-180px + padding
        columns = max(4, int(width / 185)) 

        for i, prod in enumerate(products):
            row = i // columns
            col = i % columns
            
            # Button content
            current_stock_mem = prod.get('stock', 0)
            p_id = str(prod['id'])
            
            # --- VISUAL SYNC: Subtract reservations from OTHER registers ---
            # We want to see what is TRULY available.
            # current_stock_mem already has MY cart items subtracted (if local logic works).
            # Now subtract what others have.
            reserved_others = state_manager.get_global_reserved_quantity(str(prod['id']), exclude_caja_id=self.caja_id)
            effective_visual_stock = current_stock_mem - reserved_others
            
            # Wrap product name to ensure it fits (e.g., 20 chars per line)
            wrapped_name = textwrap.fill(prod['name'], width=20)
            
            text = f"{wrapped_name}\nS/ {prod['price']:.2f}\nStock: {effective_visual_stock:.2f}"
            
            # Determine style based on stock or custom color
            custom_color = self.product_colors.get(p_id)
            
            if custom_color:
                style_name = f"CustomProduct_{p_id}.TButton"
                style = ttk.Style.get_instance()
                # Create dynamic style
            # Old styling/button code removed

            
            # Prepare Image argument
            photo_for_btn = None
            if prod.get('image'):
                try:
                    img = Image.open(io.BytesIO(prod['image']))
                    # Resize to fit button height (e.g. 50-60px)
                    img.thumbnail((50, 50)) # Smaller to fit on right
                    photo = ImageTk.PhotoImage(img)
                    
                    # Store reference to prevent GC
                    if not hasattr(self, 'product_image_refs'):
                        self.product_image_refs = []
                    self.product_image_refs.append(photo)
                    
                    photo_for_btn = photo
                except Exception as e:
                    print(f"Error loading image for {prod['name']}: {e}")

            # Determine style/color based on stock
            custom_color = self.product_colors.get(p_id)
            
            # Default Colors
            c1 = "#e0e0e0" # Light Gray
            c2 = "#bdbdbd" # Darker Gray (Gradient)
            txt_col = "#333333" # Dark Text
            
            if custom_color:
                c1 = custom_color
                c2 = custom_color # Flat color for custom
                # White text for custom colors (likely dark) - simplified assumption or check brightness
                txt_col = "white" 
            # GradientButton for Product
            btn = GradientButton(
                self.product_grid_frame,
                text=text,
                command=lambda p=prod: self.add_product_to_cart(p), 
                color1=c1,
                color2=c2,
                text_color=txt_col,
                width=160,
                height=80,
                corner_radius=10,
                border_color=None,
                image=photo_for_btn # Pass image
            )
            
            # Bind Drag
            btn.bind("<ButtonPress-1>", lambda e, p=prod, b=btn: self.start_drag(e, p, b, "product"))
            # Context Menu
            btn.bind("<Button-3>", lambda e, p=prod: self.show_product_context_menu(e, p))
            
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Store button reference
            try:
                self.product_buttons[int(prod['id'])] = btn
            except:
                self.product_buttons[prod['id']] = btn
            
            # Configure grid weights
            self.product_grid_frame.columnconfigure(col, weight=1)
            self.product_grid_frame.rowconfigure(row, weight=1)

        # Start Polling IF not started
        if not hasattr(self, '_polling_active'):
             self.start_stock_polling()

    def start_stock_polling(self):
        self._polling_active = True
        self._poll_stock_updates()

    def _poll_stock_updates(self):
        if not hasattr(self, '_polling_active') or not self._polling_active:
            return
            
        try:
            # Check visible buttons
            if hasattr(self, 'product_buttons') and self.product_buttons:
                # Load all states ONCE
                all_states = state_manager.load_all_states()
                
                # Build quick ID map if needed
                if not hasattr(self, '_id_to_product_map') or not self._id_to_product_map:
                     self._id_to_product_map = {str(p['id']): p for p in self.products.values()}

                for p_id_key, btn in self.product_buttons.items():
                    # Check if button still exists
                    if not btn.winfo_exists(): continue

                    p_data = self._id_to_product_map.get(str(p_id_key))
                    if p_data:
                        current_mem = p_data.get('stock', 0)
                        
                        # Calculate Reserved
                        reserved_others = 0.0
                        for c_id, data in all_states.items():
                            if str(c_id) == str(self.caja_id): continue
                            for item in data.get('cart', []):
                                if str(item.get('id')) == str(p_id_key):
                                    reserved_others += float(item.get('quantity', 0))
                        
                        effective = current_mem - reserved_others
                        
                        # Reconstruct text
                        wrapped = textwrap.fill(p_data['name'], width=20)
                        price = p_data['price']
                        expected_text = f"{wrapped}\nS/ {price:.2f}\nStock: {effective:.2f}"
                        
                        if btn.cget('text') != expected_text:
                             btn.configure(text=expected_text)
                             
                             stock_warning_limit = config_manager.load_setting('stock_warning_limit', 0)
                             custom_color = self.product_colors.get(str(p_id_key))
                             
                             if not custom_color:
                                 if stock_warning_limit > 0 and effective <= stock_warning_limit:
                                     try:
                                         if btn.cget('style') != "ProductLowStock.TButton":
                                            btn.configure(style="ProductLowStock.TButton")
                                     except: pass
                                 # (Reseting normal style omitted for brevity/stability)
            
        except Exception as e:
            pass
            
        # Schedule next poll (Faster: 0.5s to 1s for better UX)
        self.after(1000, self._poll_stock_updates)

    def update_total(self):
        self.total = sum(item['subtotal'] for item in self.cart)
        
        # Calculate Base Total (Original Price * Quantity)
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        
        difference = self.total - base_total
        
        # Update Labels
        # Update Labels
        # Update Items Count
        total_qty = sum(item['quantity'] for item in self.cart)
        if float(total_qty).is_integer():
             self.total_items_value.config(text=f"{int(total_qty)}")
        else:
             self.total_items_value.config(text=f"{total_qty:.2f}")

        # Update Discount/Surcharge visibility
        # We need to pack them into 'totals_row'. Access parent of items_frame or store totals_row ref.
        # items_frame is packed left. total_frame is packed right.
        # We want discount in between.
        
        # Update Discount/Surcharge visibility (Now Static)
        
        # We removed pack_forget/pack logic because structure is grid now.
        
        # Logic for Discount Label
        if difference < -0.001: # Discount
             # Show absolute value
             if hasattr(self, 'discount_label_title'):
                 self.discount_label_title.config(text="DSCTO:")
             self.discount_value.config(text=f"S/ {abs(difference):.2f}", foreground=POS_ACCENT_RED)
             
        elif difference > 0.001: # Surcharge (Adicional)
             # User requested "ADIC." label
             if hasattr(self, 'discount_label_title'):
                 self.discount_label_title.config(text="ADIC.:")
             self.discount_value.config(text=f"S/ {difference:.2f}", foreground=POS_ACCENT_BLUE)
             
        else:
             if hasattr(self, 'discount_label_title'):
                 self.discount_label_title.config(text="DSCTO:")
             self.discount_value.config(text="S/ 0.00", foreground=POS_TEXT_COLOR)

        # Total Label
        self.total_value.config(text=f"S/ {self.total:.2f}", foreground=POS_TEXT_COLOR)

        # Apply Shading (Interleaved)
        for i, item_id in enumerate(self.cart_tree.get_children()):
            if i % 2 == 0:
                self.cart_tree.item(item_id, tags=('evenrow',))
            else:
                self.cart_tree.item(item_id, tags=('oddrow',))


        # Save persistence
        self._persist_state()


    def add_product_to_cart(self, product_data):
        # Check stock?
        # Add 1 unit
        quantity = 1.0
        price = product_data['price']
        product_name = product_data['name']
        product_id = product_data['id']
        um = product_data['unit_of_measure']
        stock = product_data.get('stock', 0)
        # Calculate potential new stock
        # Check if already in cart to add that quantity
        existing_qty_in_cart = 0
        existing_item = next((item for item in self.cart if item['id'] == product_id), None)
        if existing_item:
            existing_qty_in_cart = existing_item['quantity']
            
        # Check stock control configuration
        allow_negative_stock = config_manager.load_setting('allow_negative_stock', 'No')
        
        if allow_negative_stock == "No":
            # BUG FIX: Use REAL-TIME DATABASE stock + RESERVED stock from other Cajas
            # 1. Get Confirmable DB Stock (Committed Sales)
            db_stock = database.get_product_stock(product_id)
            
            # 2. Get Reserved Stock (In other carts)
            reserved_others = state_manager.get_global_reserved_quantity(product_id, exclude_caja_id=self.caja_id)
            
            # 3. Calculate Available
            # Current logic compares (Available - Request). 
            # Note: We must also count what WE already have in cart if request is incremental?
            # The 'quantity' argument is the amount TO ADD.
            # 'existing_qty_in_cart' is what we already have.
            # So Total Request = existing_qty_in_cart + quantity
            # Available = db_stock - reserved_others
            
            available_global = db_stock - reserved_others
            total_after_add = existing_qty_in_cart + quantity
            
            if total_after_add > available_global:
                 messagebox.showwarning("Stock Insuficiente (Multicaja)", 
                                        f"No hay stock disponible.\n\n"
                                        f"Stock Global: {db_stock:.2f}\n"
                                        f"Reservado en otras cajas: {reserved_others:.2f}\n"
                                        f"Disponible: {available_global:.2f}\n\n"
                                        f"Tu Cantidad Actual: {existing_qty_in_cart:.2f}\n"
                                        f"Intentas Agregar: {quantity:.2f}", parent=self)
                 return
        
        # Check if already in cart
        existing_item = next((item for item in self.cart if item['id'] == product_id), None)
        
        if existing_item:
            existing_item['quantity'] += quantity # Fix: Add quantity, not just 1 (though usually 1 in touch)
            existing_item['subtotal'] = existing_item['quantity'] * existing_item['price']
            
            # Update Treeview
            for item_id in self.cart_tree.get_children():
                if self.cart_tree.item(item_id)['values'][0] == product_name:
                    self.cart_tree.item(item_id, values=(product_name, f"{existing_item['quantity']:.2f}", f"{existing_item['price']:.2f}", f"{existing_item['subtotal']:.2f}"))
                    break
        else:
            subtotal = price * quantity
            # original_price is the same as price in Touch mode (unless edited, which is not yet implemented)
            original_price = price 
            self.cart.append({"id": product_id, "name": product_name, "quantity": quantity, "price": price, "subtotal": subtotal, "unit_of_measure": um, "original_price": original_price})
            self.cart_tree.insert("", "end", values=(product_name, f"{quantity:.2f}", f"{price:.2f}", f"{subtotal:.2f}"))
            
        self.update_total()
        
        # --- SAVE STATE FOR MULTI-BOX SYNC ---
        state_manager.save_box_state(self.caja_id, {'cart': self.cart})
        
        # --- Update Stock UI ---
        # 1. Update memory (self.products) ALWAYS
        if product_name in self.products:
            # Note: We update local memory to reflect "My View" of stock remaining.
            # Even though we validated against global, the visual countdown is local-centric usually.
            # BUT, if we want to show (Global - Reserved) to user?
            # It's complex. Standard POS reduces stock locally as visual feedback.
            # We will stick to reducing local count for visual consistency.
            self.products[product_name]['stock'] -= quantity
            new_stock = self.products[product_name]['stock']
            
            # 2. Update Visuals (Button) if visible
            # Ensure product_id is int for lookup
            try:
                p_id_int = int(product_id)
                if p_id_int in self.product_buttons:
                    btn = self.product_buttons[p_id_int]
                    
                    # --- VISUAL SYNC: Subtract reservations from OTHER registers ---
                    reserved_others = state_manager.get_global_reserved_quantity(str(product_id), exclude_caja_id=self.caja_id)
                    effective_visual_stock = new_stock - reserved_others
                    
                    wrapped_name = textwrap.fill(product_name, width=20)
                    text = f"{wrapped_name}\nS/ {price:.2f}\nStock: {effective_visual_stock:.2f}"
                    btn.config(text=text)
                    
                    # Update Style based on new stock
                    # Update Style based on new stock, ONLY if not custom
                    custom_color = self.product_colors.get(str(p_id_int))
                    if not custom_color:
                        stock_warning_limit = config_manager.load_setting('stock_warning_limit', 0)
                        if stock_warning_limit > 0 and new_stock <= stock_warning_limit:
                             btn.configure(style="ProductLowStock.TButton")
                        else:
                             # Restore Default Gray Gradient
                             btn.configure(color1="#f8f9fa", color2="#e0e0e0", text_color="black")
            except Exception as e:
                print(f"Error updating button UI: {e}")
        
        # FORCE FOCUS AWAY FROM BUTTON to Scan Entry
        if hasattr(self, 'scan_entry'):
            self.scan_entry.focus_set()

    def remove_from_cart(self):
        selected_item = self.cart_tree.focus()
        if not selected_item:
            # Fallback to selection if focus is empty
            selection = self.cart_tree.selection()
            if selection:
                selected_item = selection[0]
            else:
                messagebox.showwarning("Sin Selección", "Seleccione un producto del carrito para eliminar.", parent=self)
                return
            
        try:
            item_index = self.cart_tree.index(selected_item)
            item_data = self.cart[item_index]
            product_id = item_data['id']
            quantity = item_data['quantity']
            product_name = item_data['name']
            
            # --- SYNCHRONIZED DELETE ---
            # 1. Fetch TRUE STOCK from DB
            if product_id:
                real_db_stock = database.get_product_stock(product_id)
                new_stock = real_db_stock
                
                # 2. Update Memory
                if product_name in self.products:
                    self.products[product_name]['stock'] = new_stock
                    
                # 3. Update products_by_category
                cat = self.products[product_name].get('category')
                if cat and cat in self.products_by_category:
                     for p in self.products_by_category[cat]:
                          if str(p.get('id')) == str(product_id):
                              p['stock'] = new_stock
                              break
                
                # 4. Update UI Button
                try:
                    p_id_int = int(product_id)
                    btn = self.product_buttons.get(p_id_int)
                    if btn:
                        # --- VISUAL SYNC: Subtract reservations from OTHER registers ---
                        reserved_others = state_manager.get_global_reserved_quantity(str(product_id), exclude_caja_id=self.caja_id)
                        effective_visual_stock = new_stock - reserved_others
                        
                        price = item_data['price']
                        wrapped_name = textwrap.fill(product_name, width=20)
                        text = f"{wrapped_name}\nS/ {price:.2f}\nStock: {effective_visual_stock:.2f}"
                        btn.configure(text=text)
                        
                        custom_color = self.product_colors.get(str(p_id_int))
                        if not custom_color:
                            warning_limit = config_manager.load_setting('stock_warning_limit', 0)
                            if warning_limit > 0 and new_stock <= warning_limit:
                                btn.configure(style="ProductLowStock.TButton")
                            else:
                                btn.configure(color1="#f8f9fa", color2="#e0e0e0", text_color="black")
                        
                        btn.update_idletasks()
                except Exception as e_ui:
                     print(f"UI update error: {e_ui}")

            # 3. Remove local cart item
            del self.cart[item_index]
            self.cart_tree.delete(selected_item)
            self.update_total()
            self.update_ticket_preview()
            self.clear_inputs(clear_customer=False)
            self.editing_item_index = None
            
            # --- SAVE STATE FOR MULTI-BOX SYNC ---
            state_manager.save_box_state(self.caja_id, {'cart': self.cart})

            
        except Exception as e:
            messagebox.showerror("Error", f"Hubo un error al eliminar el producto: {e}", parent=self)
            print(f"Delete Error: {e}")

    def reset_system(self):
        try:
            # Capture context
            saved_issuer = self.issuer_var.get()
            saved_address = self.address_var.get()
            
            # Save category for restore
            saved_category = None
            if hasattr(self, 'current_category'):
                saved_category = self.current_category

            # 1. Clear Cart
            self.cart = []
            
            # --- CLEAR STATE FOR MULTI-BOX SYNC ---
            # Ensure we clear state before reloading
            state_manager.clear_box_state(self.caja_id)
            
            # 2. Call Parent Reset
            super().reset_system()
             
            # 4. Restore Context
            self.issuer_var.set(saved_issuer)
            self.address_var.set(saved_address)
            
            # Clear Customer Data Explicitly
            self.customer_doc_var.set("")
            self.customer_name_var.set("")
            self.customer_address_var.set("")

            # 4. FULL RE-SYNC FROM DATABASE (Delayed slightly to ensure file write)
            # Use 50ms delay to allow OS file flush if needed
            self.after(50, lambda: self._finish_reset_system(saved_issuer, saved_address, saved_category))
        except Exception as e:
            messagebox.showerror("Error Reset", f"Error al resetear sistema: {e}", parent=self)

    def _finish_reset_system(self, saved_issuer, saved_address, saved_category):
        try:
            # This fetches the latest stock from ALL registers
            self.load_products_from_db(saved_issuer, saved_address)
            
            # 5. Restore View
            if saved_category:
                 self.show_products_for_category(saved_category)
            
            # Restore focus
            if hasattr(self, 'scan_entry'):
                self.scan_entry.focus_set()
                
            # Ensure polling is active
            if hasattr(self, 'start_stock_polling'):
                 self.start_stock_polling()
        except Exception as e:
            messagebox.showerror("Error Reset (Finish)", f"Error al finalizar reset: {e}", parent=self)

    def show_payment_modal(self):
        if not self.cart:
            messagebox.showinfo("Carrito Vacío", "No hay productos para cobrar.", parent=self)
            return
            
        # Modal for payment
        modal = tk.Toplevel(self)
        modal.title("Emitir")
        
        modal.attributes("-toolwindow", True) # Disable min/max
        modal.resizable(True, True)
        
        modal.withdraw()
        
        modal.withdraw()
        
        # User requested: "Emitir" window should NOT close. 
        # Removing aggressive "click outside" bind to prevent accidental closing during interaction with child dialogs.
        # modal.protocol("WM_DELETE_WINDOW", modal.destroy) # Default behavior is fine


        # Content Frame
        content_frame = ttk.Frame(modal, padding=20)
        content_frame.pack(fill="both", expand=True)

        ttk.Label(content_frame, text=f"Total a Pagar: S/ {self.total:.2f}", font=(FONT_FAMILY, 16, "bold")).pack(pady=(0, 10))
        
        # Payment Method
        ttk.Label(content_frame, text="Medio de Pago:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        self.payment_method_var.set("EFECTIVO")
        # Use Rounded Combobox
        cb = self._create_rounded_combobox(content_frame, self.payment_method_var)
        cb['values'] = ["EFECTIVO", "YAPE", "BCP", "BBVA", "INTERBANK"]
        
        # Amount Paid
        ttk.Label(content_frame, text="Monto Recibido:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        # Use Rounded Entry
        amount_entry = self._create_rounded_entry(content_frame, self.amount_paid_var)
        
        # Select All on focus
        def select_all(event):
            amount_entry.select_range(0, 'end')
            return "break"
        amount_entry.bind("<FocusIn>", select_all)
        # Also set focus immediately
        # amount_entry.focus_set() # Removed to prefer Payment Method focus
        
        # Change
        # Change Frame (Button + Label)
        # Fix background to match parent's real background
        real_bg = self._get_real_bg(content_frame)
        change_frame = tk.Frame(content_frame, bg=real_bg) 
        change_frame.pack(pady=10, fill="x")
        
        # Variable for Void Amount
        self.void_amount_var = tk.DoubleVar(value=0.0)

        def finish_sale():
            self.process_sale_touch(modal)

        def open_void_dialog_local():
            # Get Context
            issuer_name = self.issuer_var.get()
            address = self.address_var.get()
            
            # Resolve ID
            issuer_id = None
            if issuer_name in self.issuers:
                for i in self.issuers[issuer_name]:
                    if i['address'] == address:
                        issuer_id = i['id']; break
                        
            if not issuer_id:
                messagebox.showerror("Error", "Emisor no válido", parent=modal)
                return

            def on_void_complete(amount):
                 # Update Void Amount instead of Paid Amount
                 print(f"DEBUG: on_void_complete triggered with amount: {amount}")
                 try:
                    # 1. Update Variable
                    current_void = self.void_amount_var.get()
                    new_void = current_void + amount
                    self.void_amount_var.set(new_void)
                    print(f"DEBUG: Set void_amount_var to {new_void}")
                    
                    # 2. Update Label Directly (Backup if trace fails)
                    if hasattr(self, 'current_void_label') and self.current_void_label.winfo_exists():
                        self.current_void_label.config(text=f"Anulado: S/ {new_void:.2f}")
                    
                    # Force visibility of parent modal
                    try:
                        modal.deiconify()
                        modal.lift()
                    except: pass
                        
                 except Exception as e:
                     print(f"ERROR in on_void_complete: {e}")

            TouchMovementDialog(modal, "ANULADO", issuer_id, address, on_complete=on_void_complete)

        # Void Label
        # Use instance variable to ensure access from callback
        self.current_void_label = ttk.Label(change_frame, text="Anulado: S/ 0.00", font=(FONT_FAMILY, 10, "bold"), foreground="orange")
        self.current_void_label.pack(side="left", padx=(0, 5))
        
        # Update Void Label Text via Trace
        def update_void_label(*args):
            try:
                if hasattr(self, 'current_void_label') and self.current_void_label.winfo_exists():
                    v = self.void_amount_var.get()
                    self.current_void_label.config(text=f"Anulado: S/ {v:.2f}")
                update_change() # Trigger recalc
            except: pass
            
        self.void_amount_var.trace("w", update_void_label)

        # Anulado Button (Solid Color - No Gradient)
        # Use same color for start and end to strictly remove gradient effect
        anulado_btn = GradientButton(change_frame, "ANULADO", color1="#fd7e14", color2="#fd7e14", command=open_void_dialog_local, height=35, width=100)
        anulado_btn.pack(side="left", padx=(0, 10))
        
        # Change Label Container (removed pastel bg)
        # Revert to simple text label without specific bg
        change_label = tk.Label(change_frame, text="Vuelto: S/ 0.00", font=(FONT_FAMILY, 14, "bold"), padx=10, pady=5)
        # Ensure it matches parent bg? tk.Label defaults to system gray if not set.
        # Ideally use ttk.Label for transparency but updating text color is easier with tk.Label or style.
        # Let's use ttk.Label and configure foreground.
        change_label.destroy() # Destroy previous tk.Label
        change_label = ttk.Label(change_frame, text="Vuelto: S/ 0.00", font=(FONT_FAMILY, 14, "bold"))
        change_label.pack(side="left", fill="y")
        
        def update_change(*args):
            try:
                if not change_label.winfo_exists(): return
                
                paid_str = self.amount_paid_var.get()
                if not paid_str:
                    paid = 0.0
                else:
                    paid = float(paid_str)
                
                void_amt = self.void_amount_var.get()
                
                # Total Covered = Paid + Void
                total_covered = paid + void_amt
                
                diff = total_covered - self.total
                
                if diff < -0.001: # Use epsilon for float comparison
                    # Falta (Red Text only)
                    missing = abs(diff)
                    change_label.config(text=f"Falta: S/ {missing:.2f}", foreground="#dc3545") 
                else:
                    # Vuelto (Blue Text default or specific)
                    if abs(diff) < 0.001: diff = 0.0
                    change_label.config(text=f"Vuelto: S/ {diff:.2f}", foreground="#0d6efd")
            except: pass
            
        self.amount_paid_var.trace("w", update_change)
        
        # Initial call
        update_change()

        # Document Type
        ttk.Label(content_frame, text="Tipo Comprobante:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        doc_values = ["NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA", "FACTURA ELECTRÓNICA"]
        self.doc_type_var.set("NOTA DE VENTA")
        # Use Rounded Combobox
        doc_combo = self._create_rounded_combobox(content_frame, self.doc_type_var)
        doc_combo['values'] = doc_values
        
        # Series and Number Display
        correlative_frame = ttk.Frame(content_frame)
        correlative_frame.pack(fill="x", pady=2)
        
        self.series_label = ttk.Label(correlative_frame, text="Serie: -", font=(FONT_FAMILY, 10, "bold"))
        self.series_label.pack(side="left", padx=(0, 10))
        
        self.number_label = ttk.Label(correlative_frame, text="Número: -", font=(FONT_FAMILY, 10, "bold"))
        self.number_label.pack(side="left")
        
        def update_correlative(*args):
            doc_type_full = self.doc_type_var.get()
            doc_type_mapping = {
                "NOTA DE VENTA": "NOTA DE VENTA", "BOLETA DE VENTA ELECTRÓNICA": "BOLETA", "FACTURA ELECTRÓNICA": "FACTURA",
                "NOTA DE CRÉDITO (BOLETA)": "NOTA_CREDITO_BOLETA", "NOTA DE CRÉDITO (FACTURA)": "NOTA_CREDITO_FACTURA",
                "GUÍA DE REMISIÓN ELECTRÓNICA": "GUIA_REMISION"
            }
            internal_doc_type = doc_type_mapping.get(doc_type_full, "UNKNOWN")
            
            issuer_name = self.issuer_var.get()
            selected_address = self.address_var.get()
            
            issuer_id = None
            if issuer_name in self.issuers:
                for issuer_data in self.issuers[issuer_name]:
                    if issuer_data['address'] == selected_address:
                        issuer_id = issuer_data['id']
                        break
            
            if issuer_id:
                # Use get_correlative (read-only) to preview the next number
                row = database.get_correlative(issuer_id, internal_doc_type)
                if row and row[0]:
                    series = row[0]
                    current_number = row[1]
                    next_number = current_number + 1
                    if self.series_label.winfo_exists():
                        self.series_label.config(text=f"Serie: {series}")
                    if self.number_label.winfo_exists():
                        self.number_label.config(text=f"Número: {next_number}")
                else:
                    if self.series_label.winfo_exists(): self.series_label.config(text="Serie: -")
                    if self.number_label.winfo_exists(): self.number_label.config(text="Número: -")
            else:
                if self.series_label.winfo_exists(): self.series_label.config(text="Serie: -")
                if self.number_label.winfo_exists(): self.number_label.config(text="Número: -")

        self.doc_type_var.trace_add('write', update_correlative)
        # Initial update
        update_correlative()
        
        # Client Section
        ttk.Label(content_frame, text="DNI/RUC Cliente:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        client_frame = ttk.Frame(content_frame)
        client_frame.pack(fill="x", pady=2)
        
        # Search Button (Right Side for Visibility)
        search_btn = ttk.Button(client_frame, text="🔍", command=lambda: self.search_customer_touch(modal), bootstyle="info", width=3)
        search_btn.pack(side="right", padx=(5, 0), anchor="center") # Align vertically
        
        # Use Rounded Entry for Client
        # We need the entry reference for binding, create_rounded_entry returns the entry widget
        client_entry = self._create_rounded_entry(client_frame, self.customer_doc_var)
        
        # Let's repack the container created by _create_rounded_entry?
        # The container is client_entry.master (the canvas).
        container = client_entry.master
        container.pack_configure(side="left", fill="x", expand=True) # Change pack to side left
        
        # Modified binding to focus Search Button after Return
        client_entry.bind("<Return>", lambda e: (self.search_customer_touch(modal), search_btn.focus_set()))
        
        # Name / Reason Social
        ttk.Label(content_frame, text="Nombre / Razón Social:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        name_entry = self._create_rounded_entry(content_frame, self.customer_name_var)
        
        # Address
        ttk.Label(content_frame, text="Dirección:", font=(FONT_FAMILY, 10, "bold")).pack(pady=2, anchor="w")
        address_entry = self._create_rounded_entry(content_frame, self.customer_address_var)
            
        # Buttons Frame
        btns_frame = ttk.Frame(content_frame)
        btns_frame.pack(fill="x", pady=(20, 0))
        
        # Use Grid for EQUAL width (1:1)
        btns_frame.columnconfigure(0, weight=1) # Cancelar
        btns_frame.columnconfigure(1, weight=1) # Cobrar

        # Cancelar Button (Solid Gray/Red)
        cancel_btn = GradientButton(btns_frame, "CANCELAR", color1="#6c757d", color2="#6c757d", command=modal.destroy, height=45)
        cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # Cobrar Button (Solid Green)
        pay_btn = GradientButton(btns_frame, "EMITIR", color1="#198754", color2="#198754", command=finish_sale, height=45)
        pay_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        # Auto-size
        modal.update_idletasks()
        width = 450
        height = modal.winfo_reqheight()
        screen_width = modal.winfo_screenwidth()
        screen_height = modal.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")
        
        # --- Focus Order & Bindings ---
        # Order: Payment Method -> Amount -> Doc Type -> Client -> Search -> Name -> Address -> Emitir
        
        # 1. Tab Order (Fixing Search/Client reversed creation)
        # By default Search (created first) is visited before Client.
        # We want Client -> Search. So Search must be "after" Client.
        # client_entry is inside a container frame (master).
        try:
            search_btn.lift(client_entry.master)
        except: pass

        # 2. Return Bindings (Focus Shift)
        cb.bind("<Return>", lambda e: amount_entry.focus_set())
        amount_entry.bind("<Return>", lambda e: doc_combo.focus_set())
        doc_combo.bind("<Return>", lambda e: client_entry.focus_set())
        # client_entry handled above
        search_btn.bind("<Return>", lambda e: name_entry.focus_set())
        name_entry.bind("<Return>", lambda e: address_entry.focus_set())
        address_entry.bind("<Return>", lambda e: pay_btn.focus_set())
        
        # 3. Initial Focus
        self.after(100, cb.focus_set) # Small delay to ensure modality doesn't steal back
        modal.deiconify()

    def _get_real_bg(self, widget):
        """Find the real background color by checking style and hierarchy."""
        try:
            # 1. Try current widget's style (for ttk widgets)
            style = ttk.Style()
            widget_style = ""
            try:
                widget_style = widget.cget("style")
            except: pass
            
            if not widget_style:
                widget_style = widget.winfo_class() # e.g. TFrame
            
            bg = style.lookup(widget_style, "background")
            if bg and bg != "":
                r, g, b = widget.winfo_rgb(bg)
                return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
                
            # 2. Try cget (for standard tk widgets)
            if hasattr(widget, "cget"):
                bg = widget.cget("background")
                if bg and bg != "":
                    r, g, b = widget.winfo_rgb(bg)
                    return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
        except: pass
        
        # 3. Fallback to TFrame or Root style
        try:
            bg = ttk.Style().lookup("TFrame", "background")
            if bg:
                r, g, b = widget.winfo_rgb(bg)
                return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
        except: pass

        # 4. Ultimate fallback: Check toplevel
        try:
            bg = widget.winfo_toplevel().cget("bg")
            if bg:
                r, g, b = widget.winfo_rgb(bg)
                return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
        except: pass

        return "white" # Ultimate fallback


    def search_customer_touch(self, modal_parent):
        doc = self.customer_doc_var.get().strip()
        if not doc:
            return

        import api_client
        
        try:
            self.customer_name_var.set("Buscando...")
            
            # Run in thread to avoid freezing UI? 
            # For simplicity in this edit, we'll run synchronously or use the existing async pattern if possible.
            # But api_client might be blocking. 
            # Let's just call it directly for now as per previous pattern, but handle UI updates.
            
            result = api_client.get_person_data(doc)
            
            if result and result.get("success"):
                data = result.get("data", {})
                
                # Name Logic
                full_name = ""
                if len(doc) == 8:
                     nombres = data.get('nombre', '')
                     ap_paterno = data.get('apellido_paterno', '')
                     ap_materno = data.get('apellido_materno', '')
                     full_name = f"{nombres} {ap_paterno} {ap_materno}".strip()
                
                if not full_name:
                    full_name = data.get("nombre", "")
                    if not full_name:
                        full_name = f"{data.get('nombres', '')} {data.get('apellido_paterno', '')} {data.get('apellido_materno', '')}".strip()
                
                self.customer_name_var.set(full_name)

                # Logic to suppress address for DNI (8 digits) or RUC 10 (11 digits, starts with 10)
                is_dni = len(doc) == 8
                is_ruc10 = len(doc) == 11 and doc.startswith("10")
                
                if not is_dni and not is_ruc10:
                    address = data.get("domicilio", {}).get("direccion", "")
                    self.customer_address_var.set(address)
                else:
                    self.customer_address_var.set("") # Explicitly clear
                
            else:
                self.customer_name_var.set("")
                msg = result.get("message", "No se encontraron datos.") if result else "Error desconocido."
                messagebox.showwarning("Búsqueda sin resultados", msg, parent=modal_parent)

        except Exception as e:
            self.customer_name_var.set("")
            messagebox.showerror("Error Inesperado", f"Ocurrió un error: {e}", parent=modal_parent)

    def update_ticket_preview(self):
        pass

    def process_sale_touch(self, modal):
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
            messagebox.showerror("Error", "Debe seleccionar un emisor y una dirección.", parent=modal)
            return
            
        if not self.cart:
            messagebox.showinfo("Información", "El carrito está vacío.", parent=modal)
            return
            
        if internal_doc_type == "FACTURA" and (not self.customer_doc_var.get() or len(self.customer_doc_var.get()) != 11):
             messagebox.showerror("Error de Validación", "Para FACTURA, el cliente debe tener un RUC de 11 dígitos.", parent=modal)
             return

        issuer_id = None
        if issuer_name in self.issuers:
            for issuer_data in self.issuers[issuer_name]:
                if issuer_data['address'] == selected_address:
                    issuer_id = issuer_data['id']
                    break
        
        if not issuer_id:
            messagebox.showerror("Error Crítico", "El emisor seleccionado ya no es válido.", parent=modal)
            return

        series, number = database.get_next_correlative(issuer_id, internal_doc_type)
        
        # Only apply fallback if the correlative row doesn't exist at all (series is None)
        if series is None and internal_doc_type == "NOTA DE VENTA":
            # Row doesn't exist in correlatives table - insert default
            try:
                import database as db_module
                conn = db_module.create_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO correlatives (issuer_id, doc_type, series, current_number) VALUES (?, ?, ?, ?)",
                           (issuer_id, "NOTA DE VENTA", "NV01", 0))
                conn.commit()
                conn.close()
                # Now try again
                series, number = database.get_next_correlative(issuer_id, internal_doc_type)
            except Exception as e:
                print(f"Error insertando correlativo NOTA DE VENTA: {e}")
                pass

        if not series or number == -1:
            messagebox.showerror("Error de Configuración", f"No se ha configurado un correlativo para '{doc_type_full}'.\nPor favor, configúrelo en el módulo de Configuración.", parent=modal)
            return
            
        # --- Validaciones de Monto ---
        customer_doc = self.customer_doc_var.get().strip()
        customer_name = self.customer_name_var.get().strip()
        customer_address = self.customer_address_var.get().strip()
        
        # 1. Ventas > 700 Soles
        if self.total > 700:
            if not customer_doc or not customer_name:
                messagebox.showerror("Error de Validación", "Para ventas mayores a S/ 700, el DNI/RUC y Nombre son obligatorios.", parent=modal)
                return
            if len(customer_doc) == 11 and not customer_address:
                 messagebox.showerror("Error de Validación", "Para ventas con RUC mayores a S/ 700, la dirección es obligatoria.", parent=modal)
                 return

        # 2. Ventas > 2000 Soles (Bancarización)
        if self.total > 2000 and internal_doc_type in ["BOLETA", "FACTURA"]:
             if not messagebox.askyesno("Advertencia de Bancarización", "Esta seguro de emitir el comprobante electrónico ya que supera los 2000 soles y necesita ser bancarizado?", parent=modal):
                 return

        customer_phone = "" 
        observations = ""
        
        # Ensure customer exists
        customer_id = database.get_or_create_customer(customer_doc, customer_name, customer_phone, customer_address)
        
        sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sale_document_number = f"{series}-{number}"
        
        payment_method = self.payment_method_var.get()
        try:
            amount_paid = float(self.amount_paid_var.get())
        except ValueError:
            amount_paid = 0.0
            
        payment_method2 = None
        amount_paid2 = 0.0
        payment_destination = "CAJA"
        
        # --- Capture Variables for Printing (Parity with SalesView) ---
        self.last_payment_method = payment_method
        self.last_amount_received = amount_paid
        self.last_change = amount_paid - self.total if amount_paid >= self.total else 0.0
        self.last_sale_document_number = sale_document_number
        self.last_doc_type = doc_type_full
        
        # Discount logic
        base_total = sum(item.get('original_price', item['price']) * item['quantity'] for item in self.cart)
        difference = self.total - base_total
        self.last_discount_text = ""
        if difference > 0.001:
            self.last_discount_text = f"ADIC.: S/ {difference:.2f}"
        elif difference < -0.001:
            self.last_discount_text = f"DSCTO.: S/ {abs(difference):.2f}"
            
        try:
            sale_id = database.record_sale(issuer_id, customer_id, self.total, self.cart, sale_date, observations, internal_doc_type, sale_document_number, payment_method, amount_paid, payment_method2, amount_paid2, payment_destination, customer_address)
            
            if internal_doc_type in ["BOLETA", "FACTURA", "NOTA DE VENTA"]:
                for item in self.cart: database.decrease_product_stock(item['id'], item['quantity'])
            elif internal_doc_type in ["NOTA_CREDITO_BOLETA", "NOTA_CREDITO_FACTURA"]:
                for item in self.cart: database.increase_product_stock(item['id'], item['quantity'])
            
            config_manager.save_setting('last_issuer_id', issuer_id)
            
            # Check Print Configuration
            confirm_print = config_manager.load_setting('confirm_print', 'Si')
            should_print = False
            
            if confirm_print == 'Si':
                if messagebox.askyesno("Imprimir", f"Se generó el documento '{sale_document_number}' por un total de S/ {self.total:.2f}. ¿Desea Imprimir?", parent=modal):
                    should_print = True
            else:
                should_print = True # Auto-print

            if should_print:
                try:
                    if not hasattr(self, 'datetime_var'):
                        self.datetime_var = tk.StringVar(value=sale_date)
                    else:
                        self.datetime_var.set(sale_date)
                        
                    self.print_ticket()
                except Exception as print_error:
                    print(f"Printing error: {print_error}")

            # --- JSON Generation for Electronic Invoicing ---
            json_config = config_manager.load_setting('json_generation', 'Si')
            print(f"DEBUG: JSON Config: '{json_config}', Internal Doc Type: '{internal_doc_type}'")
            if json_config == 'Si' and internal_doc_type != "NOTA DE VENTA":
                try:
                    # Re-find issuer data to get RUC
                    issuer_ruc = ""
                    current_issuer_data = {}
                    if issuer_name in self.issuers:
                        for i_data in self.issuers[issuer_name]:
                            if i_data['id'] == issuer_id:
                                current_issuer_data = i_data
                                issuer_ruc = i_data.get('ruc', '20000000001')
                                establishment_code = i_data.get('establishment_code', '0000')
                                commercial_name = i_data.get('commercial_name', '')
                                break
                    if not issuer_ruc: issuer_ruc = "20000000001"
                    if not establishment_code: establishment_code = "0000"
                    
                    json_sale_data = {
                        "issuer": {
                            "ruc": issuer_ruc,
                            "name": issuer_name,
                            "commercial_name": commercial_name,
                            "address": selected_address,
                            "establishment_code": establishment_code
                        },
                        "customer": {
                            "doc_type": "6" if len(customer_doc) == 11 else "1",
                            "doc_number": customer_doc,
                            "name": customer_name,
                            "address": customer_address
                        },
                        "document": {
                            "type_name": doc_type_full,
                            "series": series,
                            "number": number,
                            "issue_date": datetime.strptime(sale_date, "%Y-%m-%d %H:%M:%S"),
                            "currency": "PEN",
                            "total": self.total
                        },
                        "items": [],
                        "totals": {} 
                    }
                    
                    # Map Items
                    for item in self.cart: 
                        json_sale_data["items"].append({
                            "description": item['name'],
                            "quantity": item['quantity'],
                            "price_unit_inc_igv": item['price'],
                            "unit_code": item.get('unit_of_measure', 'NIU')
                        })

                    # Generate
                    # Generate
                    base_project_dir = r"c:\Users\USUARIO\Mi unidad (eddiejhersson1@gmail.com)\Proyecto tkinter"
                    json_dir = os.path.join(base_project_dir, "SEE Electronica", "JSON Apisunat")
                    
                    gen = json_generator.JSONGenerator(json_dir)
                    json_path = gen.generate_invoice_json(json_sale_data)
                    print(f"JSON Generated: {json_path}")
                    
                    # --- XML Generation, Signing & Sending ---
                    try:
                        import xml_generator
                        base_see_dir = os.path.join(base_project_dir, "SEE Electronica")
                        xml_gen = xml_generator.XMLGenerator(base_see_dir)
                        xml_result = xml_gen.generate_and_send(json_sale_data, current_issuer_data)
                        print(f"XML Process: {xml_result}")
                        
                        status = "PENDIENTE"
                        note = ""
                        cdr_path = None

                        if not xml_result.get('success'):
                            status = "ERROR_LOCAL"
                            note = xml_result.get('error', 'Error desconocido')
                            # messagebox.showwarning("Alerta Facturación", f"Error en envío XML: {note}", parent=modal)
                        else:
                            # Parse SOAP Response
                            xml_resp = xml_result.get('response', '')
                            try:
                                # Simplistic parsing to find status
                                if "Fault" in xml_resp:
                                    status = "RECHAZADO"
                                    if "<faultstring>" in xml_resp:
                                        note = xml_resp.split("<faultstring>")[1].split("</faultstring>")[0]
                                    elif ":faultstring>" in xml_resp: # ns handling
                                        note = xml_resp.split(":faultstring>")[1].split("</")[0]
                                    else:
                                        note = "Error SOAP desconocido"
                                    
                                    # Show Msg
                                    messagebox.showerror("RECHAZADO", f"SUNAT Rechazó el comprobante:\n{note}", parent=modal)

                                    # WhatsApp Alert
                                    alert_receivers = current_issuer_data.get('cpe_alert_receivers')
                                    # Note: current_issuer_data comes from self.issuers cache. 
                                    # If DB updated but cache not, it might missing.
                                    # Safe look up from DB directly if critical?
                                    # For now assume cache is okay after restart context.
                                    if alert_receivers:
                                        try:
                                            import whatsapp_manager
                                            msg = f"⚠ *Alerta CPE Rechazado*\n📄 *{doc_type_full}*: {series}-{number}\n❌ *Error*: {note}"
                                            for receiver in alert_receivers.split(','):
                                                r = receiver.strip()
                                                if r:
                                                    whatsapp_manager.baileys_manager.send_message(r, msg)
                                        except Exception as e_wa:
                                            print(f"WA Alert Error: {e_wa}")

                                elif "ticket" in xml_resp:
                                    status = "PENDIENTE"
                                    if "<ticket>" in xml_resp:
                                        note = "Ticket: " + xml_resp.split("<ticket>")[1].split("</ticket>")[0]
                                    messagebox.showwarning("PENDIENTE", f"Envío procesado. Estado: PENDIENTE\n{note}", parent=modal)

                                elif "applicationResponse" in xml_resp:
                                    status = "ACEPTADO"
                                    note = "Aceptado correctamente"
                                    
                                    # Extract CDR?
                                    # Saving CDR is done via checking getStatusCdr later usually, but getStatus returns CDR.
                                    # If we have applicationResponse (CDR), we should save it.
                                    # It's base64 inside <applicationResponse>.
                                    # For now, just mark status.
                                    messagebox.showinfo("ACEPTADO", "Documento ACEPTADO por SUNAT.", parent=modal)

                                else:
                                    # Unknown response
                                    status = "ERROR_RESPUESTA"
                                    note = "Respuesta SOAP no reconocida."

                            except Exception as e_parse:
                                status = "ERROR_PARSEO"
                                note = str(e_parse)

                        # Update DB
                        database.update_sale_sunat_status(sale_id, status, note, cdr_path)
                            
                    except Exception as e_xml:
                        print(f"Critical XML Error: {e_xml}")
                    
                except Exception as e_json:
                    print(f"Error generating JSON: {e_json}")
                    # We do not block the sale for this error, just log/notify
            
            modal.destroy()
            self.reset_system()
            self.load_products_from_db()
            
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error al procesar la venta.\n{e}", parent=modal)

    def clear_inputs(self, clear_customer=True):
        # Override to avoid AttributeError with observations_text which doesn't exist in Touch View
        self.amount_paid_var.set("0.0")
        # self.amount_paid_var2.set(0.0) 
        self.payment_method_var.set("EFECTIVO")
        # self.payment_method_var2.set("NINGUNO") 
        
        if clear_customer:
            self.customer_doc_var.set("")
            self.customer_name_var.set("")
            self.customer_address_var.set("")

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

    def _setup_placeholder(self, entry, placeholder_text):
        entry.insert(0, placeholder_text)
        entry.configure(foreground='grey')

        def on_focus_in(event):
            if entry.get() == placeholder_text:
                entry.delete(0, tk.END)
            # User requested black text on focus
            entry.configure(foreground="black")
            # Ensure no blue border - force highlight color to match bg or be neutral
            try:
                entry.configure(highlightcolor="white", highlightbackground="white")
            except: pass

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

        # 1. Search Product
        product_name = self.product_code_map.get(code)
        
        if not product_name:
            # Not found
            self.scan_entry.delete(0, tk.END)
            # Optional: Visual feedback
            print(f"Code {code} not found")
            return

        if product_name in self.products:
            product_data = self.products[product_name]
            self.add_product_to_cart(product_data)
        
        # 3. Cleanup
        self.scan_entry.delete(0, tk.END)
        # Keep focus
        self.scan_entry.focus_set()

    def _on_scan_input(self, *args):
        try:
            code = self.scan_var.get().strip()
            if not code or code == self.scan_placeholder:
                # Search cleared: Restore current category view
                if hasattr(self, 'current_category'):
                    self.show_products_for_category(self.current_category)
                else:
                    # Fallback to None or default
                    self.show_products_for_category(None)
                return
                
            if not hasattr(self, 'product_code_map'):
                return

            # Check for Exact Match
            if code in self.product_code_map:
                # Found! Trigger add.
                self.handle_scan()
                return

            # Fuzzy Search
            # Filter products by name or code
            search_query = code.lower()
            filtered_products = []
            
            for p in self.products.values():
                if search_query in p['name'].lower() or search_query in str(p.get('code', '')).lower():
                    filtered_products.append(p)
            
            # Display Results
            self._display_search_results(filtered_products)

        except Exception as e:
            print(f"Search Error: {e}")

    def _display_search_results(self, products):
        # Clear grid
        for widget in self.product_grid_frame.winfo_children():
            widget.destroy()
        self.product_buttons = {}
        
        # Grid layout logic (Copying from show_products_for_category)
        width = self.product_grid_frame.winfo_width()
        if width <= 100: width = self.winfo_screenwidth() * 0.65 
        columns = max(4, int(width / 185)) 

        for i, prod in enumerate(products):
            row = i // columns
            col = i % columns
            
            # Button content
            current_stock_mem = prod.get('stock', 0)
            p_id = str(prod['id'])
            
            # --- VISUAL SYNC ---
            reserved_others = state_manager.get_global_reserved_quantity(str(prod['id']), exclude_caja_id=self.caja_id)
            effective_visual_stock = current_stock_mem - reserved_others
            
            wrapped_name = textwrap.fill(prod['name'], width=20)
            text = f"{wrapped_name}\nS/ {prod['price']:.2f}\nStock: {effective_visual_stock:.2f}"
            
            # Style
            custom_color = self.product_colors.get(p_id)
            c1 = "#e0e0e0"
            c2 = "#bdbdbd"
            txt_col = "#333333"
            
            if custom_color:
                c1 = custom_color
                c2 = custom_color
                txt_col = "white" 
            else:
                stock_warning_limit = config_manager.load_setting('stock_warning_limit', 0)
                if stock_warning_limit > 0 and effective_visual_stock <= stock_warning_limit:
                    c1 = POS_ACCENT_RED
                    c2 = POS_ACCENT_RED
                    txt_col = "white"
                else:
                    c1 = "#f8f9fa" 
                    c2 = "#e0e0e0"
                    txt_col = "black"

            # Prepare Image (simplified, no cache list mgmt for now to be safe/fast, or rely on GC? cache list is safer)
            # We must manage self.product_image_refs!
            if i == 0: self.product_image_refs = [] # Reset on start of render loop? No, this function runs once per search.
            
            photo_for_btn = None
            if prod.get('image'):
                try:
                    img = Image.open(io.BytesIO(prod['image']))
                    img.thumbnail((50, 50))
                    photo = ImageTk.PhotoImage(img)
                    self.product_image_refs.append(photo)
                    photo_for_btn = photo
                except: pass

            btn = GradientButton(
                self.product_grid_frame,
                text=text,
                command=lambda p=prod: self.add_product_to_cart(p), 
                color1=c1,
                color2=c2,
                text_color=txt_col,
                width=160,
                height=80,
                corner_radius=10,
                image=photo_for_btn
            )
            
            # Rebind Drag/Context
            btn.bind("<ButtonPress-1>", lambda e, p=prod, b=btn: self.start_drag(e, p, b, "product"))
            btn.bind("<Button-3>", lambda e, p=prod: self.show_product_context_menu(e, p))
            
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            try:
                self.product_buttons[int(prod['id'])] = btn
            except:
                self.product_buttons[prod['id']] = btn
            
            self.product_grid_frame.columnconfigure(col, weight=1)
            self.product_grid_frame.rowconfigure(row, weight=1)



    def _persist_state(self):
        state = {
            "cart": self.cart,
            "total": self.total,
            "doc_type": self.doc_type_var.get(),
            "payment_method": self.payment_method_var.get(),
            "amount_paid": self.amount_paid_var.get(),
            "customer": {
                "doc": self.customer_doc_var.get(),
                "name": self.customer_name_var.get(),
                "address": self.customer_address_var.get(),
                "phone": self.customer_phone_var.get()
            },
            "issuer": str(self.issuer_var.get()),
            "address": str(self.address_var.get())
        }
        state_manager.save_box_state(self.caja_id, state)

    def load_state_from_disk(self):
        saved = state_manager.load_all_states().get(str(self.caja_id))
        if saved:
            self.cart = saved.get("cart", [])
            self.total = saved.get("total", 0.0)
            
            self.doc_type_var.set(saved.get("doc_type", "BOLETA DE VENTA ELECTRÓNICA"))
            self.payment_method_var.set(saved.get("payment_method", "EFECTIVO"))
            self.amount_paid_var.set(saved.get("amount_paid", "0.0"))
            
            cust = saved.get("customer", {})
            self.customer_doc_var.set(cust.get("doc", ""))
            self.customer_name_var.set(cust.get("name", ""))
            self.customer_address_var.set(cust.get("address", ""))
            self.customer_phone_var.set(cust.get("phone", ""))
            
            # Rebuild Cart UI
            self.refresh_cart_tree()
            self.update_total() # Updates footer UI
            
            # --- SYNC STOCK MEMORY (CRITICAL FIX) ---
            # If products are loaded, update their stock based on restored cart
            if hasattr(self, 'products') and self.products:
                for item in self.cart:
                    p_name = item.get('name')
                    if p_name and p_name in self.products:
                        qty = item.get('quantity', 0)
                        self.products[p_name]['stock'] -= qty
                        
                # Update visible buttons if they exist
                if hasattr(self, 'show_products_for_category') and hasattr(self, 'current_category'):
                     # We might need to refresh view? No, poll will catch it?
                     # Polling reads self.products. So if we update self.products, Polling will fix UI in 1s.
                     pass

    def refresh_cart_tree(self):
        # Clear existing
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Re-populate
        for item in self.cart:
             values = (
                item['name'],
                f"{item['quantity']:.2f}",
                # Product order in treeview columns might differ in SalesTouchView vs SalesView?
                # SalesTouchView setup_right_pane: columns=("producto", "cantidad", "precio", "subtotal")
                # But cart item helper might have more keys.
                # Let's match setup_right_pane columns.
                # "precio" is column 2
                f"{item['price']:.2f}",
                f"{item['subtotal']:.2f}"
            )
             self.cart_tree.insert("", "end", values=values)



    def open_cash_count(self):
        try:
            # Check for pending items (globally)
            # Relaxed constraint: Warn but allow proceeding if user confirms
            if state_manager.has_pending_items():
                messagebox.showerror("Acción Bloqueada", "No se puede realizar el Arqueo de Caja mientras existan productos en el carrito de venta o en operaciones pendientes.\n\nPor favor, vacíe el carrito o complete las ventas pendientes.", parent=self.winfo_toplevel())
                return
            
            # Call base method
            super().open_cash_count()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"No se pudo abrir el Arqueo de Caja.\n{e}", parent=self.winfo_toplevel())
