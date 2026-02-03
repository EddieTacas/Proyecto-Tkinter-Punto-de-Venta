import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
from tkinter import simpledialog
import database
import api_client
import threading
from PIL import Image, ImageTk, ImageDraw # Added for custom styles
import tkinter as tk

# --- Constantes de Estilo (Theme Manager) ---
from theme_manager import FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HEADER

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
            c1 = c2
        elif self._is_hovering:
            pass

        # Create Image with PIL
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
        
        base.paste(top, (0, 0), mask)
        gradient_img = base
        
        if self.corner_radius > 0:
            mask_img = Image.new('L', (width, height), 0)
            draw_mask = ImageDraw.Draw(mask_img)
            draw_mask.rounded_rectangle((0, 0, width, height), radius=self.corner_radius, fill=255)
            
            final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            final_img.paste(gradient_img, (0, 0), mask_img)
        else:
            final_img = gradient_img
        
        self.image_ref = ImageTk.PhotoImage(final_img)
        self.delete("all")
        self.create_image(0, 0, image=self.image_ref, anchor='nw')
        
        # Text/Icon
        full_text = f"{self.icon} {self.text}"
        self.create_text(width//2, height//2, text=full_text, fill=self._text_color, font=self._font_args)

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

class CustomersSuppliersView(ttk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Gestión de Clientes y Proveedores")
        self.state('zoomed')
        
        # Import Colors from HTML spec
        HTML_NAVY = '#0a2240'
        HTML_BG = '#f0f2f5'
        HTML_WHITE = '#ffffff'
        HTML_BLUE = '#007bff'
        HTML_RED = '#dc3545'
        HTML_BORDER = '#999999' # Dark gray
        
        self.configure(background=HTML_BG)
        
        style = ttk.Style.get_instance()
        
        # --- HTML-Like Styles ---
        # Header styles not needed for GradientFrame but keeping for labels if any
        style.configure('HtmlCard.TFrame', background=HTML_WHITE)
        style.configure('HtmlCard.TLabel', background=HTML_WHITE, foreground='#333333', font=(FONT_FAMILY, 10, 'bold'))
        
        # Helper for rounded borders
        def create_rounded_element(name, color, border_color, width=150, height=30, radius=10, image_name=None):
            w, h = 60, 30
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((0, 0, w-1, h-1), radius=radius, fill=color, outline=border_color, width=1)
            
            if image_name:
                 return ImageTk.PhotoImage(img, name=image_name)
            return ImageTk.PhotoImage(img)

        self.img_rounded_field = create_rounded_element("field", HTML_WHITE, HTML_BORDER, image_name="img_rounded_field_common")
        self.img_rounded_focus = create_rounded_element("focus", HTML_WHITE, HTML_BLUE, image_name="img_rounded_focus_common")
        
        try:
             style.element_create("Rounded.field", "image", self.img_rounded_field,
                                  ('focus', self.img_rounded_focus),
                                  border=10, sticky="ewns")
        except tk.TclError:
             pass 

        # Configure Entry Style
        style.layout('HtmlEntry.TEntry', [
            ('Rounded.field', {'sticky': 'nswe', 'children': [
                ('Entry.padding', {'sticky': 'nswe', 'children': [
                    ('Entry.textarea', {'sticky': 'nswe'})
                ]})
            ]})
        ])
        style.configure('HtmlEntry.TEntry', padding=5)
        
        # Configure Combobox Style
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
                  fieldbackground=[('readonly', HTML_WHITE)],
                  selectbackground=[('readonly', '#007bff')],
                  selectforeground=[('readonly', 'white')],
                  foreground=[('readonly', 'black')])

        # Table (Borderless)
        style.configure("Html.Treeview.Heading", background=HTML_NAVY, foreground="white", font=(FONT_FAMILY, 9, "bold"))
        style.map("Html.Treeview.Heading", background=[('active', HTML_NAVY)])
        style.configure("Html.Treeview", font=(FONT_FAMILY, 9), rowheight=28, borderwidth=0, relief="flat")
        style.layout("Html.Treeview", [('Html.Treeview.treearea', {'sticky': 'nswe'})])

        # --- LAYOUT ---
        
        # 1. Header Bar (Gradient)
        header = GradientFrame(self, HTML_NAVY, HTML_BLUE, height=60)
        header.pack(fill='x')
        header.create_text(20, 30, text="Gestión de Clientes y Proveedores", fill="white", anchor="w", font=(FONT_FAMILY, 20, 'bold'))
        
        # 2. Main Wrapper (Gray BG, Padding)
        main_wrapper = ttk.Frame(self, style='TFrame')
        style.configure('TFrame', background=HTML_BG)
        main_wrapper.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 3. White Card Container
        card = ttk.Frame(main_wrapper, style='HtmlCard.TFrame')
        card.pack(fill='both', expand=True)

        # --- FORM SECTION ---
        # We will use two columns: Left (Fields) and Right (Search/Info or just spread fields)
        # Based on original UI, we had Type, DNI/RUC+Search, Name, Phone, Address, Alias.
        
        form_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=20)
        form_frame.pack(fill='x')
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)
        
        # Row 0: Tipo, DNI/RUC
        ttk.Label(form_frame, text="Tipo:", style='HtmlCard.TLabel', anchor='e').grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.type_var = ttk.StringVar(value="Cliente")
        self.type_combo = ttk.Combobox(form_frame, textvariable=self.type_var, values=["Cliente", "Proveedor"], state="readonly", style='HtmlEntry.TCombobox')
        self.type_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(form_frame, text="DNI/RUC:", style='HtmlCard.TLabel', anchor='e').grid(row=0, column=2, sticky="e", padx=15, pady=5)
        
        doc_frame = ttk.Frame(form_frame, style='HtmlCard.TFrame')
        doc_frame.grid(row=0, column=3, sticky="ew", padx=5, pady=5)
        doc_frame.columnconfigure(0, weight=1)
        
        self.doc_number_var = ttk.StringVar()
        self._trace_uppercase(self.doc_number_var)
        self.doc_number_entry = ttk.Entry(doc_frame, textvariable=self.doc_number_var, style='HtmlEntry.TEntry')
        self.doc_number_entry.grid(row=0, column=0, sticky="ew")
        self.doc_number_entry.bind("<Return>", self.search_person_api)
        self.after(100, lambda: self.doc_number_entry.focus_set())
        
        # Special small button for Search
        # We can't use GradientButton easily inside grid with small size unless adjusted.
        # Use standard button styled? Or tiny GradientButton.
        # Let's use a tiny GradientButton.
        self.search_btn = GradientButton(doc_frame, text="", icon="🔍", color1=HTML_BLUE, color2='#0056b3', command=self.search_person_api, height=30, width=40, corner_radius=5)
        self.search_btn.grid(row=0, column=1, padx=(5, 0))

        # Row 1: Nombre (Full Width)
        ttk.Label(form_frame, text="Nombre/Razón Social:", style='HtmlCard.TLabel', anchor='e').grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.name_var = ttk.StringVar()
        self._trace_uppercase(self.name_var)
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, style='HtmlEntry.TEntry')
        self.name_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=5)

        # Row 2: Teléfono, Dirección
        ttk.Label(form_frame, text="Teléfono:", style='HtmlCard.TLabel', anchor='e').grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.phone_var = ttk.StringVar()
        self._trace_uppercase(self.phone_var)
        self.phone_entry = ttk.Entry(form_frame, textvariable=self.phone_var, style='HtmlEntry.TEntry')
        self.phone_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form_frame, text="Dirección:", style='HtmlCard.TLabel', anchor='e').grid(row=2, column=2, sticky="e", padx=15, pady=5)
        self.address_var = ttk.StringVar()
        self._trace_uppercase(self.address_var)
        self.address_entry = ttk.Entry(form_frame, textvariable=self.address_var, style='HtmlEntry.TEntry')
        self.address_entry.grid(row=2, column=3, sticky="ew", padx=5, pady=5)

        # Row 3: Alias (And Search Filter in original? No, Search Filter was below)
        ttk.Label(form_frame, text="Alias (Opcional):", style='HtmlCard.TLabel', anchor='e').grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.alias_var = ttk.StringVar()
        self._trace_uppercase(self.alias_var)
        self.alias_entry = ttk.Entry(form_frame, textvariable=self.alias_var, style='HtmlEntry.TEntry')
        self.alias_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # --- ACTION BUTTONS (Row) ---
        actions_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=(20, 10))
        actions_frame.pack(fill='x')
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        actions_frame.columnconfigure(2, weight=1)
        actions_frame.columnconfigure(3, weight=1)
        
        BLUE_START = '#007bff'
        BLUE_END = '#0056b3'
        RED_START = '#dc3545'
        RED_END = '#bd2130'
        GRAY_START = '#6c757d'
        GRAY_END = '#545b62'
        INFO_START = '#17a2b8'
        INFO_END = '#138496'

        self.add_btn = GradientButton(actions_frame, text="Añadir Nuevo", icon="✚", color1=BLUE_START, color2=BLUE_END, command=self.add_party, height=40)
        self.add_btn.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        
        self.update_btn = GradientButton(actions_frame, text="Actualizar", icon="💾", color1=INFO_START, color2=INFO_END, command=self.update_party, height=40)
        self.update_btn.grid(row=0, column=1, sticky='ew', padx=5)
        
        self.delete_btn = GradientButton(actions_frame, text="Eliminar", icon="❌", color1=RED_START, color2=RED_END, command=self.delete_party, height=40)
        self.delete_btn.grid(row=0, column=2, sticky='ew', padx=5)
        
        self.clear_btn = GradientButton(actions_frame, text="Limpiar", icon="✨", color1=GRAY_START, color2=GRAY_END, command=self.clear_fields, height=40)
        self.clear_btn.grid(row=0, column=3, sticky='ew', padx=(5, 0))

        # --- SEARCH FILTER (New Row) ---
        search_frame = ttk.Frame(card, style='HtmlCard.TFrame', padding=(20, 5))
        search_frame.pack(fill='x')
        ttk.Label(search_frame, text="Filtrar Lista:", style='HtmlCard.TLabel').pack(side='left', padx=(0, 5))
        self.search_var = ttk.StringVar()
        self._trace_uppercase(self.search_var)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, style='HtmlEntry.TEntry', width=40)
        self.search_entry.pack(side='left', fill='x', expand=True)
        self.search_entry.bind("<KeyRelease>", self.filter_parties)

        # --- TABLE ---
        tree_container = ttk.Frame(card, style='HtmlCard.TFrame', padding=20)
        tree_container.pack(fill='both', expand=True)
        
        # Table Header Styling (Rounded Extremes)
        img_h = 35
        img_w = 40
        def hex_to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        c_nav = hex_to_rgb(HTML_NAVY)

        def create_header_img(radius_corners=[]):
            img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            grad = Image.new('RGBA', (img_w, img_h), c_nav + (255,))
            
            if not radius_corners:
                return grad
            
            mask = Image.new('L', (img_w, img_h), 255)
            m_draw = ImageDraw.Draw(mask)
            r = 10
            
            if 'tl' in radius_corners:
                 m_draw.rectangle((0, 0, r, r), fill=0)
                 m_draw.pieslice((0, 0, r*2, r*2), 180, 270, fill=255)
            if 'tr' in radius_corners:
                 m_draw.rectangle((img_w-r, 0, img_w, 0+r), fill=0)
                 m_draw.pieslice((img_w-2*r, 0, img_w, r*2), 270, 360, fill=255)
                 
            grad.putalpha(mask)
            return grad

        self.img_header_center_pil = create_header_img([])
        self.img_header_left_pil = create_header_img(['tl'])
        self.img_header_right_pil = create_header_img(['tr'])
        
        self.img_header_center = ImageTk.PhotoImage(self.img_header_center_pil)
        self.img_header_left = ImageTk.PhotoImage(self.img_header_left_pil)
        self.img_header_right = ImageTk.PhotoImage(self.img_header_right_pil)

        style.configure("Html.Treeview.Heading", image=self.img_header_center, background=HTML_NAVY, foreground="white", font=(FONT_FAMILY, 9, "bold"), borderwidth=0)
        style.map("Html.Treeview.Heading", background=[('active', HTML_NAVY)], relief=[('pressed', 'flat'), ('active', 'flat')])
        
        self.tree = ttk.Treeview(tree_container, columns=("ID", "Tipo", "DNI/RUC", "Nombre", "Teléfono", "Dirección", "Alias"), show="headings", style="Html.Treeview", displaycolumns=("Tipo", "DNI/RUC", "Nombre", "Teléfono", "Dirección", "Alias"))
        
        headers = [("ID", 40), ("Tipo", 70), ("DNI/RUC", 100), ("Nombre", 200), ("Teléfono", 90), ("Dirección", 200), ("Alias", 100)]
        
        # Configure columns (width/anchor)
        for col, width in headers:
            self.tree.column(col, width=width)
            if col in ["ID", "Tipo", "DNI/RUC", "Teléfono"]: 
                self.tree.column(col, anchor='center')

        # Configure visible headings (images)
        visible_cols = ["Tipo", "DNI/RUC", "Nombre", "Teléfono", "Dirección", "Alias"]
        for i, col in enumerate(visible_cols):
            if i == 0: img = self.img_header_left
            elif i == len(visible_cols) - 1: img = self.img_header_right
            else: img = self.img_header_center
            self.tree.heading(col, text=col, image=img)

        scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.tree.tag_configure('evenrow', background='#f8f9fa')
        self.tree.tag_configure('oddrow', background='#ffffff')
        
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_party)
        
        self.populate_parties_list()
        self.name_entry.focus_set()

    def _trace_uppercase(self, string_var):
        def to_uppercase(*args):
            s = string_var.get()
            if s != s.upper():
                string_var.set(s.upper())
        string_var.trace_add('write', to_uppercase)

    def populate_parties_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        parties = database.get_all_parties()
        for i, row in enumerate(parties):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=row, tags=(tag,))

    def filter_parties(self, event=None):
        search_term = self.search_var.get().strip().upper()
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        all_parties = database.get_all_parties()
        filtered_parties = [
            row for row in all_parties 
            if search_term in str(row[1]).upper() or # Type
               search_term in str(row[2]).upper() or # DNI/RUC
               search_term in str(row[3]).upper() or # Name
               search_term in str(row[4]).upper() or # Phone
               search_term in str(row[5]).upper() or # Address
               search_term in str(row[6]).upper()    # Alias
        ]
        
        if not filtered_parties:
            self.tree.insert("", "end", values=("", "", "No hay coincidencias", "", "", "", ""), tags=('placeholder',))
            self.tree.tag_configure('placeholder', foreground='gray')
        else:
            for i, row in enumerate(filtered_parties):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.tree.insert("", "end", values=row, tags=(tag,))

    def search_person_api(self, event=None):
        doc = self.doc_number_var.get().strip()
        if not doc:
            messagebox.showwarning("Aviso", "Ingrese un DNI o RUC para buscar.", parent=self)
            return
        
        self.name_var.set("BUSCANDO...")
        self.address_var.set("BUSCANDO...")
        
        def run_search():
            result = api_client.get_person_data(doc)
            self.after(0, lambda: self._handle_search_result(result))

        thread = threading.Thread(target=run_search)
        thread.daemon = True
        thread.start()

    def _handle_search_result(self, result):
        if result and result.get("success"):
            data = result.get("data", {})
            
            # Nombre / Razón Social
            full_name = ""
            doc_num = self.doc_number_var.get().strip()
            
            if len(doc_num) == 8:
                 # Para DNI, forzar formato: Nombres ApellidoP ApellidoM
                 nombres = data.get('nombre', '')
                 ap_paterno = data.get('apellido_paterno', '')
                 ap_materno = data.get('apellido_materno', '')
                 full_name = f"{nombres} {ap_paterno} {ap_materno}".strip()

            if not full_name:
                full_name = data.get("nombre", "")
            
            if not full_name:
                # Fallback general
                full_name = f"{data.get('nombres', '')} {data.get('apellido_paterno', '')} {data.get('apellido_materno', '')}".strip()
            
            self.name_var.set(full_name)

            # Dirección
            address = ""
            domicilio = data.get("domicilio", {})
            if domicilio:
                address = f"{domicilio.get('direccion', '')} {domicilio.get('distrito', '')} {domicilio.get('provincia', '')} {domicilio.get('departamento', '')}".strip()
            elif "direccion" in data: # A veces viene directo
                 address = data.get("direccion", "")
            
            self.address_var.set(address)
            
            # Alias (Opcional: usar nombre comercial si existe, pero la API usualmente no lo da separado)
            # self.alias_var.set(...) 
        else:
            self.name_var.set("")
            self.address_var.set("")
            msg = result.get("message", "No se encontraron datos.") if result else "Error desconocido."
            messagebox.showwarning("Sin Resultados", msg, parent=self)

    def add_party(self):
        doc_number = self.doc_number_var.get().strip()
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        address = self.address_var.get().strip()
        party_type = self.type_var.get()
        alias = self.alias_var.get().strip()

        if not name:
            messagebox.showerror("Datos Incompletos", "El campo 'Nombre/Razón Social' es obligatorio.", parent=self)
            return

        try:
            database.add_party(doc_number, name, phone, address, party_type, alias)
            messagebox.showinfo("Éxito", "Cliente/Proveedor añadido correctamente.", parent=self)
            self.populate_parties_list()
            self.clear_fields()
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo añadir el Cliente/Proveedor.\n\nError: {e}", parent=self)

    def update_party(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Sin Selección", "Por favor, seleccione un Cliente/Proveedor para actualizar.", parent=self)
            return
        
        party_id = self.tree.item(selected_item)[ "values" ][0]
        doc_number = self.doc_number_var.get().strip()
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        address = self.address_var.get().strip()
        party_type = self.type_var.get()
        alias = self.alias_var.get().strip()

        if not name:
            messagebox.showerror("Datos Incompletos", "El campo 'Nombre/Razón Social' es obligatorio.", parent=self)
            return

        try:
            database.update_party(party_id, doc_number, name, phone, address, party_type, alias)
            messagebox.showinfo("Éxito", "Cliente/Proveedor actualizado correctamente.", parent=self)
            self.populate_parties_list()
            self.clear_fields()
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo actualizar el Cliente/Proveedor.\n\nError: {e}", parent=self)

    def delete_party(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Sin Selección", "Por favor, seleccione un Cliente/Proveedor para eliminar.", parent=self)
            return

        values = self.tree.item(selected_item)["values"]
        if not values or values[0] == "": return

        party_id = values[0]
        party_name = values[3]
        
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar a '{party_name}'?", parent=self):
            try:
                database.delete_party(party_id)
                messagebox.showinfo("Éxito", "Cliente/Proveedor eliminado correctamente.", parent=self)
                self.populate_parties_list()
                self.clear_fields()
            except Exception as e:
                messagebox.showerror("Error de Base de Datos", f"No se pudo eliminar el Cliente/Proveedor.\n\nError: {e}", parent=self)

    def load_selected_party(self, event):
        selected_item = self.tree.focus()
        if selected_item and 'placeholder' not in self.tree.item(selected_item, 'tags'):
            values = self.tree.item(selected_item)[ "values" ]
            # ID, Tipo, DNI/RUC, Nombre, Teléfono, Dirección, Alias
            # 0   1     2        3       4         5          6
            self.type_var.set(values[1])
            self.doc_number_var.set(values[2])
            self.name_var.set(values[3])
            self.phone_var.set(values[4])
            self.address_var.set(values[5])
            # Handle potential missing alias in old records if not migrated properly (though DB handles it)
            if len(values) > 6:
                self.alias_var.set(values[6])
            else:
                self.alias_var.set("")

    def clear_fields(self):
        self.type_var.set("Cliente")
        self.doc_number_var.set("")
        self.name_var.set("")
        self.phone_var.set("")
        self.address_var.set("")
        self.alias_var.set("")
        if self.tree.focus():
            self.tree.selection_remove(self.tree.focus())
        self.name_entry.focus_set()
