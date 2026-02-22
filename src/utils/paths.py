import sys
import os

def get_base_dir():
    """
    Returns the base directory of the application.
    
    - If running as a compiled .exe (Frozen), returns the folder containing the .exe.
    - If running as a script, returns the project root (one level up from src).
    """
    if getattr(sys, 'frozen', False):
        # We are running in a bundle (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # We are running in a normal Python environment
        # This file is in src/utils/, so we go up two levels to reach root
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_config_path(filename: str) -> str:
    """Returns the absolute path for an external configuration file."""
    return os.path.join(get_base_dir(), filename)

def get_resource_path(relative_path: str) -> str:
    """
    Returns the absolute path to an internal resource (bundled inside the EXE).
    Used for icons, images, or internal data files.
    """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as EXE, use the current absolute path
        # src/utils/ -> src/ -> root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)