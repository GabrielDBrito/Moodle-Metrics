import sys
import os
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Callable, Optional

# --- Internal Imports ---
from utils.db import save_analytics_data_to_db 
from utils.config_loader import load_config
from utils.filters import CourseFilter 
from api.services import process_course_analytics
from api.client import get_target_courses, call_moodle_api
from utils.period_parser import get_academic_period 
from utils.period_parser import get_academic_period, is_term_ready_for_analysis

# --- Path Configuration ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- Global Settings ---
MAX_WORKERS = 4 

# --- Category Helpers ---
def build_category_map(categories: list) -> Dict[int, str]:
    """Builds a full path mapping for Moodle categories."""
    by_id = {c["id"]: c for c in categories}
    result = {}
    def resolve(cat):
        names = [cat["name"]]
        parent = cat.get("parent", 0)
        while parent and parent in by_id:
            cat = by_id[parent]
            names.append(cat["name"])
            parent = cat.get("parent", 0)
        return "/".join(reversed(names))
    for c in categories:
        result[c["id"]] = resolve(c)
    return result

def extract_departamento(category_path: str) -> str | None:
    """Extracts the department level from the category path."""
    if not category_path: return None
    parts = [p.strip() for p in category_path.split("/") if p.strip()]
    if len(parts) < 2: return "Otros"
    return parts[1]

# --- WORKER ---
def execute_course_task(course: Dict[str, Any], config: Dict[str, Any], category_map: Dict[int, str]) -> Dict[str, Any]:
    try:
        # 1. Extraction & Calculation
        data = process_course_analytics(config, course)
        
        if not data:
            return {"status": "skipped", "id": course["id"], "reason": "Datos insuficientes o filtrados por calidad"}

        # 2. Enrichment
        category_id = data["categoria_id"]
        category_path = category_map.get(category_id, "")
        data["departamento"] = extract_departamento(category_path) or "OTRO"
        
        ts_reference = data.get("startdate") or data.get("timecreated") or 0
        course_name = data.get("nombre_curso", "")
        
        id_tiempo, period_name, year, term = get_academic_period(course_name, ts_reference)
        
        data.update({
            "id_tiempo": id_tiempo,
            "nombre_periodo": period_name,
            "anio": year,
            "trimestre": term,
            "nombre_materia": data["nombre_curso"] 
        })

        # 3. Persistence
        save_analytics_data_to_db(data)

        return {
            "status": "success", 
            "data": data
        }
    except Exception as e:
        return {"status": "error", "id": course["id"], "error": str(e)}

# --- MAIN PIPELINE ---
def run_pipeline(
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None 
    ):
    
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log("--- UNIMET Analytics: Iniciando Pipeline ETL ---")
    if stop_event and stop_event.is_set(): return

    config = load_config()

    try:
        start_str = config['FILTERS']['start_date']
        min_ts = datetime.strptime(start_str, "%Y-%m-%d").timestamp()
        end_str = config['FILTERS']['end_date']
        max_ts = datetime.strptime(end_str, "%Y-%m-%d").timestamp() + 86399
    except Exception as e:
        log(f" [!] Error en configuración de fechas: {e}")
        return

    log(" [1/3] Descargando metadatos de categorías...")
    categories = call_moodle_api(config["MOODLE"], "core_course_get_categories")
    if not categories:
        log(" [!] Error: Categorías no encontradas.")
        return
    category_map = build_category_map(categories)

    if stop_event and stop_event.is_set(): return

    log(" [2/3] Descargando catálogo de cursos...")
    raw_courses = get_target_courses(config)
    if not raw_courses:
        log(" [!] Error: Catálogo de cursos vacío.")
        return

    # --- FILTERING LOGIC (Centralized) ---
    courses_queue = []
    for c in raw_courses:
        # A. Calculate the term for this specific course
        ts_ref = c.get("startdate") or c.get("timecreated") or 0
        term_id, _, _, _ = get_academic_period(c["fullname"], ts_ref)

        # B. TEMPORAL SAFETY FILTER: Skip if the term is not ready for analysis yet
        if not is_term_ready_for_analysis(term_id):
            # This ignores courses from the "current" or "future" terms
            continue

        # C. Metadata & Administrative Filters
        cat_path = category_map.get(c.get("categoryid"), "")
        c_start = c.get("startdate", 0)
        
        if CourseFilter.is_valid_metadata(
            course_fullname=c["fullname"],
            course_shortname=c.get("shortname", ""),
            category_path=cat_path,
            course_start_ts=c_start,
            min_ts=min_ts,
            max_ts=max_ts
        ):
            courses_queue.append(c)

    total_courses = len(courses_queue)
    if total_courses == 0:
        log(" [!] No se encontraron cursos válidos para el rango seleccionado.")
        if progress_callback: progress_callback(1, 1)
        return

    log(f" [3/3] Procesando {total_courses} cursos...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(execute_course_task, c, config, category_map): c for c in courses_queue}
        
        for i, future in enumerate(as_completed(futures), 1):
            if stop_event and stop_event.is_set():
                log(" Proceso detenido por el usuario.")
                executor.shutdown(wait=False, cancel_futures=True)
                break

            result = future.result()
            progress_pct = (i / total_courses) * 100
            course_id = result.get('id') or result.get('data', {}).get('id_curso')

            if result["status"] == "success":
                name = result["data"]["nombre_curso"][:30]
                log(f" {progress_pct:.1f}% OK | ID: {course_id} | {name}")
            elif result["status"] == "skipped":
                log(f" {progress_pct:.1f}% OMITIR | ID: {course_id} | {result.get('reason')}")
            else:
                log(f" {progress_pct:.1f}% ERR | ID: {course_id} | {result.get('error')}")

            if progress_callback:
                progress_callback(i, total_courses)

    if stop_event and stop_event.is_set():
        log("--- Proceso CANCELADO ---")
    else:
        log("--- Proceso Finalizado con Éxito ---")

if __name__ == "__main__":
    run_pipeline()