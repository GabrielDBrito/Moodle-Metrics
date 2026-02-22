import configparser
import os
from .paths import get_config_path 

def load_config():
    """
    Loads the configuration from the 'config.ini' file.
    It uses the centralized paths utility to resolve the correct location.
    
    Returns:
        configparser.ConfigParser: The configuration object.
    """
    config_path = get_config_path('config.ini')

    # 2. Validate existence
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}\nAsegúrate de que config.ini esté en la misma carpeta que el ejecutable.")

    # 3. Parse the file
    config = configparser.ConfigParser()
    config.read(config_path)

    # 4. We ensure that critical sections exist to prevent errors
    if 'MOODLE' not in config:
        raise ValueError("El archivo config.ini no tiene la sección [MOODLE]")
    
    if 'FILTERS' not in config:
        # If it doesn't exist, we inject default values
        config['FILTERS'] = {'start_date': '2023-01-01', 'end_date': '2025-12-31'}

    print(f"Configuration loaded successfully from: {config_path}")
    return config