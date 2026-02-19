import os
import threading
import configparser
from datetime import datetime
import customtkinter as ctk

# Import the ETL logic
from main import run_pipeline

# --- UNIMET Brand Colors ---
UNIMET_NAVY = "#003087"     # Primary dark blue
UNIMET_ORANGE = "#F68629"   # Primary orange
UNIMET_LIGHT_BLUE = "#1859A9" # Secondary blue
UNIMET_WHITE = "#FFFFFF"

# Configuration paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.ini')

class ETLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("UNIMET Virtual - Extractor de Indicadores")
        self.geometry("650x550")
        self.resizable(False, False)
        ctk.set_appearance_mode("light") 

        # --- Load Config ---
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_PATH)
        self.current_start = self.config.get('FILTERS', 'start_date', fallback='2024-08-01')
        self.current_end = self.config.get('FILTERS', 'end_date', fallback='2025-10-15')

        # --- Build UI ---
        self._build_header()
        self._build_filters()
        self._build_progress_bar()
        self._build_console()

    def _build_header(self):
        """Header area using UNIMET Navy Blue."""
        header_frame = ctk.CTkFrame(self, fg_color=UNIMET_NAVY, corner_radius=0, height=80)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header_frame, 
            text="Actualización de Indicadores Académicos", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=UNIMET_WHITE
        )
        title_label.pack(pady=25)

    def _build_filters(self):
        """Input area for dates and the start button."""
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(pady=20, padx=40, fill="x")

        # Instruction
        instr = ctk.CTkLabel(
            filter_frame, 
            text="Seleccione el rango de fechas de creación de los cursos (YYYY-MM-DD):", 
            text_color="gray30"
        )
        instr.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        # Start Date Input
        lbl_start = ctk.CTkLabel(filter_frame, text="Fecha Inicial:", font=ctk.CTkFont(weight="bold"))
        lbl_start.grid(row=1, column=0, sticky="w", pady=5)
        self.entry_start = ctk.CTkEntry(filter_frame, width=140, border_color=UNIMET_LIGHT_BLUE)
        self.entry_start.insert(0, self.current_start)
        self.entry_start.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # End Date Input
        lbl_end = ctk.CTkLabel(filter_frame, text="Fecha Final:", font=ctk.CTkFont(weight="bold"))
        lbl_end.grid(row=2, column=0, sticky="w", pady=5)
        self.entry_end = ctk.CTkEntry(filter_frame, width=140, border_color=UNIMET_LIGHT_BLUE)
        self.entry_end.insert(0, self.current_end)
        self.entry_end.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Start Button (UNIMET Orange)
        self.btn_start = ctk.CTkButton(
            filter_frame, 
            text="INICIAR PROCESO", 
            fg_color=UNIMET_ORANGE, 
            hover_color="#d97017", # Slightly darker orange
            font=ctk.CTkFont(weight="bold", size=14),
            height=40,
            command=self.start_extraction
        )
        self.btn_start.grid(row=1, column=2, rowspan=2, padx=30, sticky="e")

    def _build_progress_bar(self):
        """Progress bar and status text."""
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=40, pady=(0, 10))

        self.status_label = ctk.CTkLabel(prog_frame, text="Estado: En espera", text_color=UNIMET_NAVY, font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.progressbar = ctk.CTkProgressBar(prog_frame, progress_color=UNIMET_LIGHT_BLUE, height=15)
        self.progressbar.pack(fill="x")
        self.progressbar.set(0)

    def _build_console(self):
        """Text area to display logs."""
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self.textbox = ctk.CTkTextbox(
            log_frame, 
            fg_color="#f5f6f7", 
            text_color="black", 
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.textbox.pack(fill="both", expand=True)

    def validate_dates(self) -> bool:
        """Ensures the user entered valid dates."""
        try:
            datetime.strptime(self.entry_start.get(), "%Y-%m-%d")
            datetime.strptime(self.entry_end.get(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def write_log(self, message: str):
        """Thread-safe GUI update for logs."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end") 
        self.textbox.configure(state="disabled")

    def update_progress(self, current: int, total: int):
        """Thread-safe GUI update for progress bar."""
        progress = current / total
        self.progressbar.set(progress)
        self.status_label.configure(text=f"Estado: Procesando cursos ({current}/{total})...")

    def start_extraction(self):
        """Action triggered by the Start button."""
        if not self.validate_dates():
            self.write_log(" Formato de fecha inválido. Por favor use YYYY-MM-DD.")
            return

        # 1. Save new dates to config.ini
        self.config.set('FILTERS', 'start_date', self.entry_start.get())
        self.config.set('FILTERS', 'end_date', self.entry_end.get())
        with open(CONFIG_PATH, 'w') as configfile:
            self.config.write(configfile)

        # 2. Lock UI
        self.btn_start.configure(state="disabled", text="PROCESANDO...", fg_color="gray")
        self.entry_start.configure(state="disabled")
        self.entry_end.configure(state="disabled")
        self.progressbar.set(0)
        
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

        self.status_label.configure(text="Estado: Conectando con Moodle...", text_color=UNIMET_ORANGE)

        # 3. Run ETL in a separate thread so the window doesn't freeze
        threading.Thread(target=self.run_etl_worker, daemon=True).start()

    def run_etl_worker(self):
        """Background worker that calls the main ETL function."""
        try:
            run_pipeline(progress_callback=self.update_progress, log_callback=self.write_log)
            self.status_label.configure(text="Estado: ¡Extracción finalizada con éxito!", text_color="green")
            self.progressbar.set(1.0)
        except Exception as e:
            self.write_log(f" {str(e)}")
            self.status_label.configure(text="Estado: Proceso interrumpido por error.", text_color="red")
        finally:
            # Unlock UI
            self.btn_start.configure(state="normal", text="INICIAR PROCESO", fg_color=UNIMET_ORANGE)
            self.entry_start.configure(state="normal")
            self.entry_end.configure(state="normal")

if __name__ == "__main__":
    app = ETLApp()
    app.mainloop()