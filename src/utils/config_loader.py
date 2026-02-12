import configparser
import os
import sys

def load_config():
    """
    Loads the configuration from the 'config.ini' file.
    It handles the path logic for both development (script) and production (executable/frozen).
    
    Returns:
        dict: A dictionary containing the configuration sections.
    """
    # 1. Determine the application path (Logic for PyInstaller compatibility)
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        application_path = os.path.dirname(sys.executable)
    else:
        # Running as a python script
        # Go up two levels from /src/utils/ to get to the root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        application_path = os.path.dirname(os.path.dirname(current_dir))

    # 2. Build the full path to config.ini
    config_path = os.path.join(application_path, 'config.ini')

    # 3. Validate existence
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    # 4. Parse the file
    config = configparser.ConfigParser()
    config.read(config_path)

    # Aseguramos que existan las secciones críticas para evitar errores en main.py
    if 'MOODLE' not in config:
        raise ValueError("El archivo config.ini no tiene la sección [MOODLE]")
    
    if 'FILTERS' not in config:
        # Si no existe, inyectamos valores por defecto para que el script no rompa
        config['FILTERS'] = {'start_date': '2023-01-01', 'end_date': '2025-12-31'}

    print(f"Configuration loaded successfully from: {config_path}")
    return config