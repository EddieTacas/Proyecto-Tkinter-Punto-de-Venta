import config_manager
import ttkbootstrap as ttk
from PIL import Image, ImageTk, ImageDraw

# Load Theme Setting
CURRENT_THEME_NAME = config_manager.load_setting("system_theme", "Dark")

# Define Palettes
class DarkPalette:
    PRIMARY = "#181A1B"       # Background
    SECONDARY = "#252A2E"     # Frames/Cards
    ACCENT = "#00BCD4"        # Headers/Borders
    HEADER_BG = "#0D1B2A"     # Slightly darker/blueish for header? Or same as Primary? Let's use deep blue for nice contrast or maintain PRIMARY.
    # User said "Dark" options should be "current colors". Current main uses "primary" (bootstyle).
    # In darkly, primary is usually the dark bg. Let's keep it consistent.
    HEADER_BG = "primary" # Placeholder, or hex? 
    # Better: Use Hex. Darkly primary is #375a7f usually? No, that's Cosmo primary. Darkly bg is #222.
    # Let's check main.py usage. It used bootstyle="primary".
    # I'll let DarkPalette use a generic dark color or just reuse PRIMARY if no change requested.
    HEADER_BG = "#181A1B" # Match Primary
    
    TEXT = "#FFFFFF"          # Text
    BUTTON_PRIMARY = "#43A047"
    BUTTON_SECONDARY = "#444950"
    BUTTON_DANGER = "#DC3545"
    SUCCESS = "#28a745"
    INFO = "#17a2b8"
    WARNING = "#ffc107"
    
    # Dashboard
    CARD_BG = "#252A2E"
    CARD_FG = "#FFFFFF"
    CARD_PRIMARY_BG = "#0D6EFD"
    CARD_PRIMARY_FG = "#FFFFFF"
    GRADIENT_START = "#0D6EFD" # Blue
    GRADIENT_END = "#6610f2"   # Purple
    HEADER_GRADIENT_START = "#0a1931" # Deep Dark Blue
    HEADER_GRADIENT_END = "#1a3c6b"   # Vibrant Marine Blue

class LightPalette:
    # Based on Dashboard Image
    PRIMARY = "#F4F6F9"       # Main Background (Light Gray)
    SECONDARY = "#FFFFFF"     # Cards/Containers (White)
    ACCENT = "#2C3E50"        # Dark Blue used for accents
    
    HEADER_BG = "#0f172a"     # Dark Navy for Header (Image style)
    
    TEXT = "#2C3E50"          # Dark Slate Text
    
    # Custom Buttons
    BUTTON_PRIMARY = "#007BFF" # Blue (Generar/Token)
    BUTTON_SECONDARY = "#6C757D"
    BUTTON_DANGER = "#DC3545"
    SUCCESS = "#28a745"
    INFO = "#17a2b8"
    WARNING = "#FFC107"
    
    # Dashboard
    CARD_BG = "#FFFFFF"       # White Cards
    CARD_FG = "#212529"       # Dark Text
    CARD_PRIMARY_BG = "#4e73df" # Blurple/Indigo
    CARD_PRIMARY_FG = "#FFFFFF" # White Text
    GRADIENT_START = "#9C27B0" # Purple
    GRADIENT_END = "#2196F3"   # Blue
    HEADER_GRADIENT_START = "#0a1931"
    HEADER_GRADIENT_END = "#1a3c6b"

# Select Palette
if CURRENT_THEME_NAME == "Light":
    _p = LightPalette
else:
    _p = DarkPalette

# Export Constants
COLOR_PRIMARY = _p.PRIMARY
COLOR_SECONDARY = _p.SECONDARY
COLOR_ACCENT = _p.ACCENT
COLOR_TEXT = _p.TEXT
COLOR_BUTTON_PRIMARY = _p.BUTTON_PRIMARY
COLOR_BUTTON_SECONDARY = _p.BUTTON_SECONDARY
COLOR_BUTTON_DANGER = _p.BUTTON_DANGER
COLOR_HEADER_BG = _p.HEADER_BG
COLOR_CARD_BG = _p.CARD_BG
COLOR_CARD_FG = _p.CARD_FG
COLOR_CARD_PRIMARY_BG = _p.CARD_PRIMARY_BG
COLOR_CARD_PRIMARY_FG = _p.CARD_PRIMARY_FG
COLOR_GRADIENT_START = _p.GRADIENT_START
COLOR_GRADIENT_END = _p.GRADIENT_END
COLOR_HEADER_GRADIENT_START = _p.HEADER_GRADIENT_START
COLOR_HEADER_GRADIENT_START = _p.HEADER_GRADIENT_START
COLOR_HEADER_GRADIENT_END = _p.HEADER_GRADIENT_END

COLOR_BG = COLOR_PRIMARY # Alias for generic background

if CURRENT_THEME_NAME == "Light":
    POS_PRIMARY_DARK = "#1a2b4c"
    POS_PRIMARY_LIGHT = "#2a3f6b"
    POS_BG_MAIN = "#f4f6f9"
    POS_BG_WHITE = "#ffffff"
    POS_TEXT_COLOR = "#000000" # New Text Color constant
else:
    # Dark Mode mappings
    POS_PRIMARY_DARK = "#1a2b4c" # Keep header blue-ish or make it dark? User likes the "Dark Navy" style usually.
    # Let's keep Primary Dark as implies the Brand color.
    POS_PRIMARY_LIGHT = "#2a3f6b"
    POS_BG_MAIN = "#181A1B" # Dark Background
    POS_BG_WHITE = "#252A2E" # Card Background (Dark Gray instead of White)
    POS_TEXT_COLOR = "#ffffff"

POS_ACCENT_GREEN_START = "#56ab2f"
POS_ACCENT_GREEN_END = "#a8e063"
POS_ACCENT_RED = "#d9534f"
POS_ACCENT_BLUE = "#5bc0de"
POS_GRP_COLORS = ["#00c2cb", "#9b59b6", "#ff4081", "#3498db", "#ff8c00", "#2ecc71"]


# Fonts
FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_HEADER = 16

# Helper for Gradient
_cached_gradient = None

def get_dashboard_gradient(width=400, height=200):
    global _cached_gradient
    if _cached_gradient:
         return _cached_gradient
         
    base = Image.new('RGB', (width, height), COLOR_GRADIENT_START)
    top = Image.new('RGB', (width, height), COLOR_GRADIENT_END)
    # Horizontal Gradient for Cards (Left to Right)
    mask = Image.new('L', (width, height))
    mask_data = []
    # Optimization: Generate one row, repeat it
    row = [int(255 * (x / width)) for x in range(width)]
    for _ in range(height):
        mask_data.extend(row)
    mask.putdata(mask_data)
    
    base.paste(top, (0, 0), mask)
    
    _cached_gradient = ImageTk.PhotoImage(base)
    return _cached_gradient

_cached_header_gradient = None
def get_header_gradient(width=1280, height=80):
    global _cached_header_gradient
    if _cached_header_gradient and _cached_header_gradient.width() == width and _cached_header_gradient.height() == height:
         return _cached_header_gradient
    
    # Create VERTICAL Gradient for Header (Top to Bottom)
    base = Image.new('RGB', (width, height), COLOR_HEADER_GRADIENT_START)
    top = Image.new('RGB', (width, height), COLOR_HEADER_GRADIENT_END)
    
    mask = Image.new('L', (width, height))
    mask_data = []
    
    # Vertical: Alpha varies by Y
    for y in range(height):
        alpha = int(255 * (y / height))
        # Entire row has same alpha
        mask_data.extend([alpha] * width)
        
    mask.putdata(mask_data)
    
    base.paste(top, (0, 0), mask)
    _cached_header_gradient = ImageTk.PhotoImage(base)
    return _cached_header_gradient

# Helper to apply global styles (Optional, can be called from main)
def apply_theme_styles(style_instance=None):
    if not style_instance:
        style_instance = ttk.Style.get_instance()
    
    # Configure Custom Header Style
    style_instance.configure('Header.TFrame', background=COLOR_HEADER_BG)
    header_fg = "#FFFFFF" if CURRENT_THEME_NAME == "Light" else COLOR_TEXT
    style_instance.configure('Header.TLabel', background=COLOR_HEADER_BG, foreground=header_fg)

    # Configure Dashboard Styles
    style_instance.configure('Dashboard.TFrame', background=COLOR_CARD_BG, relief="raised", borderwidth=1)
    style_instance.configure('Dashboard.TLabel', background=COLOR_CARD_BG, foreground=COLOR_CARD_FG)
    
    style_instance.configure('DashboardPrimary.TFrame', background=COLOR_CARD_PRIMARY_BG, relief="raised", borderwidth=1)
    style_instance.configure('DashboardPrimary.TLabel', background=COLOR_CARD_PRIMARY_BG, foreground=COLOR_CARD_PRIMARY_FG)
    
    # Configure Common Styles
    style_instance.configure('TLabel', font=("Segoe UI", 12), foreground=COLOR_TEXT, background=COLOR_PRIMARY)
    style_instance.configure('TFrame', background=COLOR_PRIMARY)
    style_instance.configure('TLabelframe', background=COLOR_SECONDARY, foreground=COLOR_TEXT, bordercolor=COLOR_ACCENT)
    style_instance.configure('TLabelframe.Label', background=COLOR_SECONDARY, foreground=COLOR_TEXT)
    style_instance.configure('TPanedwindow', background=COLOR_PRIMARY)
    
    # Treeview
    style_instance.configure('Treeview', 
                           background=COLOR_SECONDARY, 
                           fieldbackground=COLOR_SECONDARY, 
                           foreground=COLOR_TEXT, 
                           bordercolor=COLOR_ACCENT)
    
    style_instance.map('Treeview', 
                     background=[('selected', COLOR_ACCENT)], 
                     foreground=[('selected', "#FFFFFF")])
    
    style_instance.configure('Treeview.Heading', 
                           font=("Segoe UI", 12, 'bold'), 
                           background=COLOR_ACCENT, 
                           foreground="#FFFFFF") # Always white text on accent header? Or COLOR_TEXT? Best white.
