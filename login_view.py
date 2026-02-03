import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import custom_messagebox as messagebox
import database
import hashlib
import theme_manager

class LoginView(ttk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Iniciar Sesión")
        
        # Center window
        width = 420 # Slightly wider for cleaner layout
        height = 600 # Increased significantly to prevent cutting off the button
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        
        # self.transient(master) # Set as transient window of master
        self.grab_set() # Modal
        
        # Force visibility
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        
        # Disable topmost after a moment to allow switching
        self.after(1000, lambda: self.attributes("-topmost", False))
        
        self.user_data = None # Will hold user data if login successful
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # UI
        # Enforce Light/White Card Style regardless of theme
        bg_color = "#FFFFFF" 
        text_color = "#333333"
        secondary_text = "#666666"
        input_bg = "#FFFFFF"
        border_color = "#E0E0E0"
        
        main_frame = tk.Frame(self, bg=bg_color)
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)

        # 1. Header: "Bienvenido" (Centered, Bold, Dark)
        lbl_welcome = tk.Label(main_frame, text="Bienvenido", font=("Segoe UI", 32, "bold"), 
                       bg=bg_color, fg="#2c3e50")
        lbl_welcome.pack(pady=(10, 5))
        
        # Subtitle
        lbl_sub = tk.Label(main_frame, text="Inicie sesión para continuar", font=("Segoe UI", 11), 
                           bg=bg_color, fg=secondary_text)
        lbl_sub.pack(pady=(0, 40))

        # Helper: Create Modern Entry with Icon
        def create_modern_entry(parent, label_text, variable, icon_char, show=None):
            # 1. Label (Small, Uppercase, Bold, Dark Gray)
            tk.Label(parent, text=label_text.upper(), font=("Segoe UI", 9, "bold"), 
                     bg=bg_color, fg="#444444").pack(anchor="w", pady=(0, 8))
            
            # 2. Container (Canvas for rounded pill shape)
            h = 50
            container = tk.Canvas(parent, height=h, bg=bg_color, highlightthickness=0)
            container.pack(fill="x", pady=(0, 20))
            
            def draw_entry_bg(event):
                w = event.width
                if w < 20: return
                container.delete("all")
                r = 25 # Full pill radius
                
                outline = "#BDBDBD" # Light gray border like image
                
                # Draw Outline (Rounded Pill)
                w_line = 1.5
                
                # Left Arc
                container.create_arc(0, 0, h, h, start=90, extent=180, style="arc", outline=outline, width=w_line)
                # Right Arc
                container.create_arc(w-h, 0, w, h, start=270, extent=180, style="arc", outline=outline, width=w_line)
                
                # Top/Bottom Lines
                container.create_line(h/2, 0, w-h/2, 0, fill=outline, width=w_line)
                container.create_line(h/2, h, w-h/2, h, fill=outline, width=w_line)
                
                # Icon (Larger, Dark)
                container.create_text(25, h//2, text=icon_char, fill="#555555", font=("Segoe UI Symbol", 14))

            container.bind("<Configure>", draw_entry_bg)
            
            # Entry Widget
            # Force flat and white to match container
            entry = tk.Entry(container, textvariable=variable, show=show, 
                             bg=bg_color, fg=text_color, font=("Segoe UI", 12),
                             bd=0, highlightthickness=0, relief="flat")
            entry.place(x=55, y=12, relwidth=0.8, height=26)
            return entry

        # Username Field
        self.username_var = tk.StringVar()
        self.username_entry = create_modern_entry(main_frame, "Usuario", self.username_var, "👤")
        self.username_entry.focus_set()

        # Password Field
        self.password_var = tk.StringVar()
        self.password_entry = create_modern_entry(main_frame, "Contraseña", self.password_var, "🔒", show="*")
        
        # Navigation Logic
        def focus_password(event):
            self.password_entry.focus_set()
            return "break"
            
        def focus_button(event):
            self.btn_canvas.focus_set()
            # Visual feedback for focus could be handled in focus in/out
            return "break"

        self.username_entry.bind("<Return>", focus_password)
        self.password_entry.bind("<Return>", focus_button)

        # 3. Modern Button (Gradient Pill + Shadow)
        btn_h = 55
        # takefocus=1 allows tab navigation to this canvas
        self.btn_canvas  = tk.Canvas(main_frame, height=btn_h+10, bg=bg_color, highlightthickness=0, cursor="hand2", takefocus=1)
        self.btn_canvas.pack(pady=30, fill="x")
        
        self.btn_hover = False
        self.btn_focused = False
        
        def draw_btn(event=None):
            w = self.btn_canvas.winfo_width()
            # Fallback width logic
            if w <= 1:
                w = self.btn_canvas.winfo_reqwidth()
                if w <= 1: w = 300
            
            self.btn_canvas.delete("all")
            
            # Width limits
            btn_w = 280
            if w < btn_w: btn_w = w - 20
            x_off = (w - btn_w) // 2
            
            # Colors
            c1 = "#00C9A7"
            c2 = "#009E86"
            
            # Change color on hover OR focus
            is_active = self.btn_hover or self.btn_focused
            
            if is_active:
                 c1 = "#00E0BA"
                 c2 = "#00B59A"
            
            # Fill Color
            fill_color = "#10B981" if not is_active else "#34D399"
            
            # Draw Focus Ring if focused (Optional but good for accessibility)
            if self.btn_focused:
                 # Draw outer ring
                 focus_color = "#81C784"
                 fh = btn_h + 6
                 fw = btn_w + 6
                 fx = x_off - 3
                 # Simple rect focus ring or rounded
                 self.btn_canvas.create_rectangle(fx, -3, fx+fw, fh-3, outline=focus_color, width=2)

            # Pill Shape
            y_start = 2
            
            # Left Arc
            self.btn_canvas.create_arc(x_off, y_start, x_off+btn_h, y_start+btn_h, start=90, extent=180, fill=fill_color, outline=fill_color)
            # Right Arc
            self.btn_canvas.create_arc(x_off+btn_w-btn_h, y_start, x_off+btn_w, y_start+btn_h, start=270, extent=180, fill=fill_color, outline=fill_color)
            # Center Rect
            self.btn_canvas.create_rectangle(x_off+btn_h/2, y_start, x_off+btn_w-btn_h/2, y_start+btn_h, fill=fill_color, outline=fill_color)
            
            # Text
            self.btn_canvas.create_text(w//2, y_start+btn_h//2, text="INGRESAR", fill="white", font=("Segoe UI", 12, "bold"))

        def on_enter(e):
            self.btn_hover = True
            draw_btn()
            
        def on_leave(e):
            self.btn_hover = False
            draw_btn()
            
        def on_focus_in(e):
            self.btn_focused = True
            draw_btn()
            
        def on_focus_out(e):
            self.btn_focused = False
            draw_btn()

        self.btn_canvas.bind("<Configure>", draw_btn)
        self.btn_canvas.bind("<Enter>", on_enter)
        self.btn_canvas.bind("<Leave>", on_leave)
        self.btn_canvas.bind("<FocusIn>", on_focus_in)
        self.btn_canvas.bind("<FocusOut>", on_focus_out)
        
        # Click / Enter Trigger
        self.btn_canvas.bind("<Button-1>", lambda e: self.login())
        self.btn_canvas.bind("<Return>", lambda e: self.login())
        self.btn_canvas.bind("<space>", lambda e: self.login())
        
        # Initial draw trigger
        self.after(100, lambda: draw_btn())
        
        # Force focus on username after window is stable
        self.after(200, lambda: self.username_entry.focus_force())
        
        # Original button removed
        # ttk.Button(main_frame, text="Ingresar", command=self.login, bootstyle="success", width=15).pack()

    def login(self, event=None):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username:
            messagebox.showwarning("Error", "Ingrese usuario", parent=self)
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = database.get_user_by_credentials(username, password_hash)
        
        if user:
            print(f"DEBUG: Login successful for {username}")
            self.user_data = user # (id, username, permissions)
            self.destroy()
        else:
            print(f"DEBUG: Login failed for {username}. Hash: {password_hash}")
            messagebox.showerror("Error", "Credenciales incorrectas", parent=self)

    def on_close(self):
        self.master.destroy()

if __name__ == "__main__":
    # Test only
    root = ttk.Window(themename="darkly")
    database.setup_database()
    app = LoginView(root)
    root.mainloop()
