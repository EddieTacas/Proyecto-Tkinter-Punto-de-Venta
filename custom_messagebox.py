import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox

# Wrapper to match tkinter.messagebox signature (title, message)
# vs ttkbootstrap.dialogs.Messagebox signature (message, title)

def showinfo(title, message, parent=None, **kwargs):
    Messagebox.show_info(message, title, parent=parent, **kwargs)

def showwarning(title, message, parent=None, **kwargs):
    # Try show_warning, if not exists fallback to show_info
    if hasattr(Messagebox, 'show_warning'):
        Messagebox.show_warning(message, title, parent=parent, **kwargs)
    else:
        # Fallback to info
        Messagebox.show_info(message, title, parent=parent, **kwargs)

def showerror(title, message, parent=None, **kwargs):
    Messagebox.show_error(message, title, parent=parent, **kwargs)

def askyesno(title, message, parent=None, **kwargs):
    # Returns "Yes" or "No" string usually in ttkbootstrap? 
    # Or "No" / "Yes" 
    # Actually ttkbootstrap yesno returns the button text clicked?
    # No, it returns 'Yes' or 'No'.
    # tkinter askyesno returns True/False.
    result = Messagebox.yesno(message, title, parent=parent, **kwargs)
    return result == 'Yes'

def askokcancel(title, message, parent=None, **kwargs):
    result = Messagebox.okcancel(message, title, parent=parent, **kwargs)
    return result == 'OK'

def askretrycancel(title, message, parent=None, **kwargs):
    result = Messagebox.retrycancel(message, title, parent=parent, **kwargs)
    return result == 'Retry'

def askquestion(title, message, parent=None, **kwargs):
    result = Messagebox.yesno(message, title, parent=parent, **kwargs)
    return 'yes' if result == 'Yes' else 'no'

# Compatibility alias
show_info = showinfo
show_warning = showwarning
show_error = showerror
