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

    # 1. Validate file existence
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}\n"
                                f"Asegúrate de que config.ini esté en la misma carpeta que el ejecutable.")

    # 2. Parse the file
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')

    # 3. Ensure critical Moodle section exists
    if 'MOODLE' not in config:
        raise ValueError("El archivo config.ini no tiene la sección [MOODLE]")
    
    # 4. Ensure FILTERS section exists with defaults
    if 'FILTERS' not in config:
        config['FILTERS'] = {
            'start_date': '2024-08-01', 
            'end_date': '2025-10-15'
        }

    # 5. Ensure THRESHOLDS section exists for GUI parameterization
    # These values can be updated from the new settings tab in the GUI
    if 'THRESHOLDS' not in config:
        config['THRESHOLDS'] = {
            'min_students': '5',
            'excellence_score': '18.0',
            'active_density': '0.40'
        }
    else:
        # Ensure individual keys exist even if section was present
        if 'min_students' not in config['THRESHOLDS']:
            config['THRESHOLDS']['min_students'] = '5'
        if 'excellence_score' not in config['THRESHOLDS']:
            config['THRESHOLDS']['excellence_score'] = '18.0'
        if 'active_density' not in config['THRESHOLDS']:
            config['THRESHOLDS']['active_density'] = '0.40'

    print(f"Configuration loaded successfully from: {config_path}")
    return config