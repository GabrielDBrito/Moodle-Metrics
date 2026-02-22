import os
import threading
import configparser
import time
import re
from datetime import datetime
import customtkinter as ctk

# Import the ETL logic
from etl_pipeline import run_pipeline

# --- Colors ---
UNIMET_NAVY       = "#003087"
UNIMET_ORANGE     = "#F68629"
UNIMET_LIGHT_BLUE = "#1859A9"
UNIMET_WHITE      = "#FFFFFF"
BG_COLOR          = "#F8F9FA"  

LOG_OK            = "#059669"
LOG_ERROR         = "#DC2626"
LOG_WARN          = "#D97706"
LOG_INFO          = "#1859A9"
LOG_TIMESTAMP     = "#9CA3AF"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.ini')

class ETLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")

        # --- Window Setup ---
        self.title("UNIMET Virtual - ETL Manager")
        w, h = 800, 650
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        # --- State Control ---
        self.stop_event = threading.Event()
        self.start_time = 0
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load Config
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_PATH)
        self.current_start = self.config.get('FILTERS', 'start_date', fallback='2024-08-01')
        self.current_end = self.config.get('FILTERS', 'end_date', fallback='2025-10-15')

        # --- Build UI ---
        self._build_header()
        self._build_filters_area()
        self._build_progress_area()
        self._build_console_area()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=UNIMET_NAVY, corner_radius=0, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="Actualización de Indicadores Académicos", 
                     font=ctk.CTkFont(size=22, weight="bold"), text_color=UNIMET_WHITE).pack(pady=25)

    def _build_filters_area(self):
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=50, pady=(30, 10))

        instr = ctk.CTkLabel(grid, text="Rango de Fechas de Extracción (Año-Mes-Día)", 
                             font=ctk.CTkFont(size=14, weight="bold"), text_color="#333")
        instr.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # --- Start date ---
        ctk.CTkLabel(grid, text="Desde:", text_color="#555").grid(row=1, column=0, sticky="w")
        self.entry_start = ctk.CTkEntry(grid, width=150, height=35, fg_color="white", 
                                        border_color="#D1D5DB", placeholder_text="YYYY-MM-DD")
        self.entry_start.insert(0, self.current_start)
        self.entry_start.grid(row=2, column=0, sticky="w", padx=(0, 30))
        self.entry_start.bind("<KeyRelease>", lambda e: self._auto_format_date(self.entry_start))

        # --- End date ---
        ctk.CTkLabel(grid, text="Hasta:", text_color="#555").grid(row=1, column=1, sticky="w")
        self.entry_end = ctk.CTkEntry(grid, width=150, height=35, fg_color="white", 
                                      border_color="#D1D5DB", placeholder_text="YYYY-MM-DD")
        self.entry_end.insert(0, self.current_end)
        self.entry_end.grid(row=2, column=1, sticky="w")
        self.entry_end.bind("<KeyRelease>", lambda e: self._auto_format_date(self.entry_end))
        
        # Start Button
        self.btn_run = ctk.CTkButton(
            grid, text="INICIAR PROCESO", 
            fg_color=UNIMET_ORANGE, hover_color="#d97017",
            text_color="white", font=ctk.CTkFont(weight="bold", size=14), 
            height=45, width=200, command=self.start_extraction)
        self.btn_run.grid(row=1, column=2, rowspan=2, sticky="e")
        
        grid.columnconfigure(2, weight=1)

    def _auto_format_date(self, entry):
        """Añade guiones automáticamente y valida el formato mientras se escribe."""
        text = entry.get().replace("-", "")
        new_text = ""
        
        # Only numbers
        text = "".join(filter(str.isdigit, text))
        
        if len(text) > 0:
            new_text = text[:4] # Año
        if len(text) > 4:
            new_text += "-" + text[4:6] # month
        if len(text) > 6:
            new_text += "-" + text[6:8] # day
            
        entry.delete(0, "end")
        entry.insert(0, new_text[:10]) # 10 char limit

        # Visual validation
        if len(entry.get()) == 10:
            try:
                datetime.strptime(entry.get(), "%Y-%m-%d")
                entry.configure(border_color=UNIMET_LIGHT_BLUE)
            except ValueError:
                entry.configure(border_color=LOG_ERROR)
        else:
            entry.configure(border_color="#D1D5DB")

    def _build_progress_area(self):
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=50, pady=(20, 10))
        
        status_row = ctk.CTkFrame(prog_frame, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 5))
        
        self.status_label = ctk.CTkLabel(status_row, text="Estado: En espera", 
                                        text_color=UNIMET_NAVY, font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="left")
        
        self.timer_label = ctk.CTkLabel(status_row, text="Tiempo: 00:00", text_color=LOG_TIMESTAMP)
        self.timer_label.pack(side="right")

        self.progressbar = ctk.CTkProgressBar(prog_frame, progress_color=UNIMET_LIGHT_BLUE, height=12)
        self.progressbar.pack(fill="x")
        self.progressbar.set(0)

    def _build_console_area(self):
        ctk.CTkLabel(self, text="Registro de Actividad", font=ctk.CTkFont(weight="bold", size=13), 
                     text_color="#555").pack(anchor="w", padx=55, pady=(10, 5))
        
        log_frame = ctk.CTkFrame(self, fg_color=UNIMET_WHITE, border_width=1, border_color="#D1D5DB", corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=50, pady=(0, 30))
        
        self.textbox = ctk.CTkTextbox(log_frame, fg_color="transparent", state="disabled", 
                                      font=ctk.CTkFont(family="Consolas", size=11))
        self.textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.textbox.tag_config("timestamp", foreground=LOG_TIMESTAMP)
        self.textbox.tag_config("ok", foreground=LOG_OK)
        self.textbox.tag_config("error", foreground=LOG_ERROR)
        self.textbox.tag_config("warn", foreground=LOG_WARN)
        self.textbox.tag_config("info", foreground=LOG_INFO)

    def write_log(self, message: str):
        ts = f"[{datetime.now().strftime('%H:%M:%S')}] "
        msg_upper = message.upper()
        if "OK" in msg_upper: tag = "ok"
        elif "ERROR" in msg_upper or "ERR" in msg_upper: tag = "error"
        elif "OMITIR" in msg_upper or "SKIP" in msg_upper: tag = "warn"
        else: tag = "info"
        
        self.textbox.configure(state="normal")
        self.textbox.insert("end", ts, "timestamp")
        self.textbox.insert("end", f"{message}\n", tag)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def safe_log(self, message: str):
        self.after(0, lambda: self.write_log(message))
        
    def safe_progress(self, current, total):
        self.after(0, lambda: self.progressbar.set(current / total))
        self.after(0, lambda: self.status_label.configure(text=f"Procesando curso {current} de {total}..."))

    def update_timer(self):
        if self.btn_run.cget("state") == "disabled" and not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.timer_label.configure(text=f"Tiempo: {mins:02d}:{secs:02d}")
            self.after(1000, self.update_timer)

    def start_extraction(self):
        # Date validation
        try:
            datetime.strptime(self.entry_start.get(), "%Y-%m-%d")
            datetime.strptime(self.entry_end.get(), "%Y-%m-%d")
        except ValueError:
            self.write_log("ERROR: Una de las fechas tiene un formato o valor inválido.")
            return

        # Save in config.ini
        self.config.set('FILTERS', 'start_date', self.entry_start.get())
        self.config.set('FILTERS', 'end_date', self.entry_end.get())
        with open(CONFIG_PATH, 'w') as f: self.config.write(f)

        self.btn_run.configure(state="disabled", text="EN PROCESO...", fg_color="#9CA3AF")
        self.entry_start.configure(state="disabled")
        self.entry_end.configure(state="disabled")
        self.progressbar.set(0)
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        
        self.stop_event.clear()
        self.start_time = time.time()
        self.update_timer()
        threading.Thread(target=self.run_etl_worker, daemon=True).start()

    def run_etl_worker(self):
        try:
            run_pipeline(progress_callback=self.safe_progress, log_callback=self.safe_log, stop_event=self.stop_event)
            if not self.stop_event.is_set():
                self.after(0, lambda: self.status_label.configure(text="Estado: ¡Finalizado con éxito!", text_color=LOG_OK))
                self.after(0, lambda: self.progressbar.set(1.0))
        except Exception as e:
            self.safe_log(f"ERROR CRÍTICO: {e}")
            self.after(0, lambda: self.status_label.configure(text="Estado: Error en ejecución", text_color=LOG_ERROR))
        finally:
            if not self.stop_event.is_set():
                self.after(0, self.reset_ui)

    def reset_ui(self):
        self.btn_run.configure(state="normal", text="INICIAR PROCESO", fg_color=UNIMET_ORANGE)
        self.entry_start.configure(state="normal")
        self.entry_end.configure(state="normal")

    def on_closing(self):
        if self.btn_run.cget("state") == "disabled":
            self.stop_event.set()
            self.safe_log("⚠️ Deteniendo procesos. Cerrando...")
            self.after(1500, lambda: os._exit(0))
        else:
            self.destroy()
            os._exit(0)

if __name__ == "__main__":
    app = ETLApp()
    app.mainloop()