import os
import threading
import configparser
import time
import sys
from datetime import datetime
import customtkinter as ctk

from utils.paths import get_config_path
from etl_pipeline import run_pipeline
from utils.paths import get_resource_path 

# --- Colors & Styles ---
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

CONFIG_PATH = get_config_path('config.ini')
ENV_PATH = get_config_path('bdd.env')

class ETLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")

        # --- Window Configuration ---
        self.title("UNIMET Virtual - ETL Manager")
        w, h = 850, 700 
        
        # Center window logic
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        # --- Set Window Icon ---
        icon_path = get_resource_path("assets/app_icon.ico")
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(icon_path))
        
        # --- State & Control ---
        self.stop_event = threading.Event()
        self.start_time = 0
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load Configuration
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_PATH)
        
        # Ensure default sections exist
        if 'FILTERS' not in self.config: self.config['FILTERS'] = {}
        if 'THRESHOLDS' not in self.config: self.config['THRESHOLDS'] = {}

        self.current_start = self.config.get('FILTERS', 'start_date', fallback='2024-08-01')
        self.current_end = self.config.get('FILTERS', 'end_date', fallback='2025-10-15')

        # --- UI Structure ---
        self._build_header()
        
        # Tab view creation
        self.tabview = ctk.CTkTabview(self, width=800, height=550, fg_color="transparent")
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_run = self.tabview.add("Ejecución")
        self.tab_config = self.tabview.add("Parámetros")

        self._build_run_tab()
        self._build_config_tab()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=UNIMET_NAVY, corner_radius=0, height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="Actualización de Indicadores Académicos", 
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=UNIMET_WHITE).pack(pady=20)

    # -------------------------------------------------------------------------
    # TAB 1: EXECUTION (RUN)
    # -------------------------------------------------------------------------
    def _build_run_tab(self):
        tab = self.tab_run
        
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="x", padx=30, pady=(10, 10))

        instr = ctk.CTkLabel(grid, text="Rango de Fechas de Extracción (Año-Mes-Día)", 
                             font=ctk.CTkFont(size=14, weight="bold"), text_color="#333")
        instr.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # Start Date
        ctk.CTkLabel(grid, text="Desde:", text_color="#555").grid(row=1, column=0, sticky="w")
        self.entry_start = ctk.CTkEntry(grid, width=150, height=35, fg_color="white", border_color="#D1D5DB")
        self.entry_start.insert(0, self.current_start)
        self.entry_start.grid(row=2, column=0, sticky="w", padx=(0, 30))
        self.entry_start.bind("<KeyRelease>", lambda e: self._auto_format_date(self.entry_start))

        # End Date
        ctk.CTkLabel(grid, text="Hasta:", text_color="#555").grid(row=1, column=1, sticky="w")
        self.entry_end = ctk.CTkEntry(grid, width=150, height=35, fg_color="white", border_color="#D1D5DB")
        self.entry_end.insert(0, self.current_end)
        self.entry_end.grid(row=2, column=1, sticky="w")
        self.entry_end.bind("<KeyRelease>", lambda e: self._auto_format_date(self.entry_end))
        
        # Run Button (Right aligned)
        self.btn_run = ctk.CTkButton(grid, text="INICIAR PROCESO", fg_color=UNIMET_ORANGE, hover_color="#d97017",
                                     text_color="white", font=ctk.CTkFont(weight="bold", size=14), height=45, width=200, 
                                     command=self.start_extraction)
        self.btn_run.grid(row=1, column=2, rowspan=2, sticky="e")
        grid.columnconfigure(2, weight=1)

        # Progress Section
        prog_frame = ctk.CTkFrame(tab, fg_color="transparent")
        prog_frame.pack(fill="x", padx=30, pady=(10, 10))
        
        status_row = ctk.CTkFrame(prog_frame, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 5))
        self.status_label = ctk.CTkLabel(status_row, text="Estado: En espera", text_color=UNIMET_NAVY, font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="left")
        
        self.timer_label = ctk.CTkLabel(status_row, text="Tiempo: 00:00", text_color=LOG_TIMESTAMP)
        self.timer_label.pack(side="right")

        self.progressbar = ctk.CTkProgressBar(prog_frame, progress_color=UNIMET_LIGHT_BLUE, height=12)
        self.progressbar.pack(fill="x")
        self.progressbar.set(0)

        # Log Console
        ctk.CTkLabel(tab, text="Registro de Actividad", font=ctk.CTkFont(weight="bold", size=13), text_color="#555").pack(anchor="w", padx=35, pady=(5, 5))
        log_frame = ctk.CTkFrame(tab, fg_color=UNIMET_WHITE, border_width=1, border_color="#D1D5DB", corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10))
        
        self.textbox = ctk.CTkTextbox(log_frame, fg_color="transparent", state="disabled", font=ctk.CTkFont(family="Consolas", size=11))
        self.textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.textbox.tag_config("timestamp", foreground=LOG_TIMESTAMP)
        self.textbox.tag_config("ok", foreground=LOG_OK)
        self.textbox.tag_config("error", foreground=LOG_ERROR)
        self.textbox.tag_config("warn", foreground=LOG_WARN)
        self.textbox.tag_config("info", foreground=LOG_INFO)

    # -------------------------------------------------------------------------
    # TAB 2: PARAMETERS (SETTINGS)
    # -------------------------------------------------------------------------
    def _build_config_tab(self):
        tab = self.tab_config
        container = ctk.CTkFrame(tab, fg_color=UNIMET_WHITE, corner_radius=10, border_width=1, border_color="#D1D5DB")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        grid = ctk.CTkFrame(container, fg_color="transparent")
        grid.pack(pady=30, padx=30)

        # Centered title
        ctk.CTkLabel(grid, text="Ajuste de Parámetros", 
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=UNIMET_NAVY).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 1. Min Students
        ctk.CTkLabel(grid, text="Mínimo Estudiantes (Curso):", text_color="#333", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="e", padx=15, pady=15)
        self.entry_min_students = ctk.CTkEntry(grid, width=120, height=35)
        self.entry_min_students.insert(0, self.config['THRESHOLDS'].get('min_students', '5'))
        self.entry_min_students.grid(row=1, column=1, sticky="w")

        # 2. Excellence Score
        ctk.CTkLabel(grid, text="Nota Excelencia (Escala 0-20):", text_color="#333", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="e", padx=15, pady=15)
        self.entry_excellence = ctk.CTkEntry(grid, width=120, height=35)
        self.entry_excellence.insert(0, self.config['THRESHOLDS'].get('excellence_score', '18.0'))
        self.entry_excellence.grid(row=2, column=1, sticky="w")

        # 3. Active Density
        ctk.CTkLabel(grid, text="Densidad Activa (% 0.0-1.0):", text_color="#333", font=ctk.CTkFont(size=13)).grid(row=3, column=0, sticky="e", padx=15, pady=15)
        self.entry_active = ctk.CTkEntry(grid, width=120, height=35)
        self.entry_active.insert(0, self.config['THRESHOLDS'].get('active_density', '0.40'))
        self.entry_active.grid(row=3, column=1, sticky="w")

        # Save Button
        self.btn_save_config = ctk.CTkButton(container, text="GUARDAR CAMBIOS", fg_color=UNIMET_NAVY, hover_color="#002470",
                                             font=ctk.CTkFont(weight="bold"), height=40, width=200, command=self.save_settings)
        self.btn_save_config.pack(pady=20)
        
        self.lbl_config_status = ctk.CTkLabel(container, text="", text_color=LOG_OK, font=ctk.CTkFont(weight="bold"))
        self.lbl_config_status.pack()

    # -------------------------------------------------------------------------
    # SHARED LOGIC & CONTROL
    # -------------------------------------------------------------------------
    def set_controls_state(self, state: str):
        """Disables or enables all interactive controls to prevent changes during ETL."""
        # Execution tab entries
        self.entry_start.configure(state=state)
        self.entry_end.configure(state=state)
        # Settings tab entries
        self.entry_min_students.configure(state=state)
        self.entry_excellence.configure(state=state)
        self.entry_active.configure(state=state)
        self.btn_save_config.configure(state=state)

    def save_settings(self):
        """Validates and saves thresholds to config.ini."""
        # 1. Validate Min Students
        try:
            val_students = int(self.entry_min_students.get())
            if val_students < 1: raise ValueError
        except ValueError:
            self.lbl_config_status.configure(text="Error: 'Mínimo Estudiantes' debe ser un entero positivo.", text_color=LOG_ERROR)
            return

        # 2. Validate Excellence Score
        try:
            val_score = float(self.entry_excellence.get())
            if not (0 <= val_score <= 20): raise ValueError
        except ValueError:
            self.lbl_config_status.configure(text="Error: 'Nota Excelencia' debe estar en rango 0-20.", text_color=LOG_ERROR)
            return

        # 3. Validate Active Density
        try:
            val_density = float(self.entry_active.get())
            if not (0.0 <= val_density <= 1.0): raise ValueError
        except ValueError:
            self.lbl_config_status.configure(text="Error: 'Densidad Activa' debe estar en rango 0.0-1.0.", text_color=LOG_ERROR)
            return

        # Update and save to disk
        self.config['THRESHOLDS']['min_students'] = str(val_students)
        self.config['THRESHOLDS']['excellence_score'] = str(val_score)
        self.config['THRESHOLDS']['active_density'] = str(val_density)
        
        try:
            with open(CONFIG_PATH, 'w') as f: self.config.write(f)
            self.lbl_config_status.configure(text="¡Configuración guardada exitosamente!", text_color=LOG_OK)
            self.write_log("Configuración de parámetros actualizada.")
            self.after(3000, lambda: self.lbl_config_status.configure(text=""))
        except Exception as e:
            self.lbl_config_status.configure(text=f"Error al guardar archivo: {e}", text_color=LOG_ERROR)

    def _auto_format_date(self, entry):
        text = "".join(filter(str.isdigit, entry.get().replace("-", "")))
        new_text = ""
        if len(text) > 0: new_text = text[:4]
        if len(text) > 4: new_text += "-" + text[4:6]
        if len(text) > 6: new_text += "-" + text[6:8]
        entry.delete(0, "end")
        entry.insert(0, new_text[:10])
        if len(entry.get()) == 10:
            try:
                datetime.strptime(entry.get(), "%Y-%m-%d")
                entry.configure(border_color=UNIMET_LIGHT_BLUE)
            except ValueError:
                entry.configure(border_color=LOG_ERROR)
        else:
            entry.configure(border_color="#D1D5DB")

    def write_log(self, message: str):
        ts = f"[{datetime.now().strftime('%H:%M:%S')}] "
        u = message.upper()
        tag = "ok" if "OK" in u else "error" if "ERROR" in u or "ERR" in u else "warn" if "OMITIR" in u or "SKIP" in u else "info"
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
        # 1. File existence checks
        if not os.path.exists(CONFIG_PATH):
            self.write_log("ERROR CRÍTICO: No se encuentra 'config.ini' en la raíz.")
            return
        if not os.path.exists(ENV_PATH):
            self.write_log("ERROR CRÍTICO: No se encuentra 'bdd.env' en la raíz.")
            return

        # 2. Date validation
        try:
            datetime.strptime(self.entry_start.get(), "%Y-%m-%d")
            datetime.strptime(self.entry_end.get(), "%Y-%m-%d")
        except ValueError:
            self.write_log("ERROR: Formato de fecha inicial/final inválido.")
            return

        # 3. GUI Blocking (Lock parameters)
        self.set_controls_state("disabled")
        self.config.set('FILTERS', 'start_date', self.entry_start.get())
        self.config.set('FILTERS', 'end_date', self.entry_end.get())
        with open(CONFIG_PATH, 'w') as f: self.config.write(f)

        self.btn_run.configure(state="disabled", text="EN PROCESO...", fg_color="#9CA3AF")
        self.progressbar.set(0)
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        
        # 4. Threading
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
            self.after(0, self.reset_ui)

    def reset_ui(self):
        """Unlocks GUI after process ends."""
        self.set_controls_state("normal")
        self.btn_run.configure(state="normal", text="INICIAR PROCESO", fg_color=UNIMET_ORANGE, text_color="white")

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