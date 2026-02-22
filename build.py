import PyInstaller.__main__
import os
import customtkinter

# Locate the graphics library to include it in the package
ctk_path = os.path.dirname(customtkinter.__file__)

print("--- INICIANDO COMPILACIÓN: UNIMET ANALYTICS ---")

PyInstaller.__main__.run([
    'src/app.py',                       # GUI
    '--name=UNIMET_Indicadores_ETL',    # .exe name
    '--onefile',                        
    '--windowed',                       
    '--noconsole',                      
    '--icon=assets/app_icon.ico',       
    '--add-data', f'{ctk_path};customtkinter/',
    '--add-data', 'assets/app_icon.ico;assets/',
    '--clean',                          # Clear cache
    '--noconfirm',                      
])

print("\n--- COMPILACIÓN FINALIZADA ---")
print("El ejecutable está en la carpeta 'dist/'")