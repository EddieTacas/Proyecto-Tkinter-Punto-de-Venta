import json
import os

CONFIG_FILE = 'config.json'
POS_CONFIG_FILE = 'pos_config.json'

def load_config():
    """Carga la configuración desde el archivo JSON."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {} # Retorna un diccionario vacío si el archivo está corrupto o vacío
    return {}

def save_config(data):
    """Guarda la configuración en el archivo JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_setting(key, value):
    """Guarda un ajuste específico en la configuración."""
    config = load_config()
    config[key] = value
    save_config(config)

def load_setting(key, default=None):
    """Carga un ajuste específico de la configuración."""
    config = load_config()
    return config.get(key, default)

def get_db_version():
    """Obtiene la versión actual del esquema de la base de datos."""
    return load_setting('db_version', 0)

def set_db_version(version):
    """Establece la versión actual del esquema de la base de datos."""
    save_setting('db_version', version)

# --- POS Config (Per-Caja Persistence) ---

def load_pos_config():
    """Carga la configuración específica del POS (por caja)."""
    if os.path.exists(POS_CONFIG_FILE):
        with open(POS_CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_pos_config(data):
    """Guarda la configuración específica del POS."""
    with open(POS_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_caja_setting(caja_id, key, value):
    """Guarda un ajuste específico para una caja."""
    config = load_pos_config()
    if str(caja_id) not in config:
        config[str(caja_id)] = {}
    config[str(caja_id)][key] = value
    save_pos_config(config)

def load_caja_setting(caja_id, key, default=None):
    """Carga un ajuste específico de una caja."""
    config = load_pos_config()
    caja_data = config.get(str(caja_id), {})
    return caja_data.get(key, default)
