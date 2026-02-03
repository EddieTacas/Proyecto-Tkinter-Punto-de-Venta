import config_manager

try:
    version = config_manager.get_db_version()
    print(f"Current DB Version: {version}")
except Exception as e:
    print(f"Error: {e}")
