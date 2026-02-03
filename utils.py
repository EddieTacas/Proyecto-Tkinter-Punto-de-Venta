import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is primarily for ONEFILE mode.
        base_path = sys._MEIPASS
    except Exception:
        # In ONEDIR mode, or Dev mode:
        # In ONEDIR, resources are usually next to the executable.
        # In DEV, they are next to the script.
        
        if getattr(sys, 'frozen', False):
            # If frozen (exe), but not onefile (no _MEIPASS, or even if onedir has it?)
            # Usually onedir puts things next to sys.executable
            base_path = os.path.dirname(sys.executable)
        else:
            # Dev mode
            base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
