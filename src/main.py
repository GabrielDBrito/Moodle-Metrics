import sys
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Callable, Optional

# --- Internal Imports ---
from utils.db import save_analytics_data_to_db 
from utils.config_loader import load_config
from api.services import process_course_analytics
from api.client import get_target_courses, call_moodle_api
from utils.period_parser import get_academic_period 

# --- Path Configuration ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- Global Settings (RESTAURADOS) ---
MAX_WORKERS = 4 
BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD"]
INVALID_DEPARTMENTS = {"POSTG", "DIDA", "AE", "U_V"}

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
    """Extracts the department level (2nd level) from the category path."""
    if not category_path: 
        return None
    parts = [p.strip() for p in category_path.split("/") if p.strip()]
    if len(parts) < 2: 
        return "Otros"
    return parts[1]

# --- WORKER: Process individual course ---
def execute_course_task(course: Dict[str, Any], config: Dict[str, Any], category_map: Dict[int, str]) -> Dict[str, Any]:
    """
    Orchestrates the extraction, enrichment, and persistence of a single course.
    Includes benchmarking to track Moodle API vs Database performance.
    """
    try:
        start_time = time.time()
        
        # 1. Extraction & Calculation via Moodle API
        data = process_course_analytics(config, course)
        moodle_bench = time.time() - start_time
        
        if not data:
            return {"status": "skipped", "id": course["id"], "reason": "Insufficient data"}

        # 2. Enrichment: Department & Academic Period
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

        # 3. Persistence: Database Transaction
        db_start = time.time()
        save_analytics_data_to_db(data)
        db_bench = time.time() - db_start

        return {
            "status": "success", 
            "data": data,
            "bench": f"Moodle: {moodle_bench:.1f}s | DB: {db_bench:.1f}s"
        }
    except Exception as e:
        return {"status": "error", "id": course["id"], "error": str(e)}


# --- MAIN PIPELINE: Now wrapped for GUI support ---
def run_pipeline(
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
):
    """
    Main ETL execution. Uses callbacks to communicate with the GUI.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log("--- UNIMET Analytics: ETL Pipeline Started ---")
    config = load_config()

    try:
        start_str = config['FILTERS']['start_date']
        min_ts = datetime.strptime(start_str, "%Y-%m-%d").timestamp()
        end_str = config['FILTERS']['end_date']
        max_ts = datetime.strptime(end_str, "%Y-%m-%d").timestamp() + 86399
    except Exception as e:
        log(f" [!] Error in config dates: {e}")
        return

    log(" [1/3] Fetching category metadata...")
    categories = call_moodle_api(config["MOODLE"], "core_course_get_categories")
    if not categories:
        log(" [!] Connection failed: Categories not found.")
        return
    category_map = build_category_map(categories)

    log(" [2/3] Fetching target course catalog...")
    raw_courses = get_target_courses(config)
    if not raw_courses:
        log(" [!] Connection failed: No courses retrieved.")
        return

    # --- Filtering Logic (RESTAURADA) ---
    courses_queue = []
    for c in raw_courses:
        # Filter by Blacklist Keywords
        if any(k in c["fullname"].upper() for k in BLACKLIST_KEYWORDS): 
            continue
        
        # Filter by Invalid Departments
        cat_path = category_map.get(c.get("categoryid"), "").upper()
        if any(dep in cat_path for dep in INVALID_DEPARTMENTS): 
            continue
        
        # Filter by Date Range
        c_start = c.get("startdate", 0)
        if not (min_ts <= c_start <= max_ts): 
            continue
            
        courses_queue.append(c)

    total_courses = len(courses_queue)
    if total_courses == 0:
        log(" [!] No courses found for the selected range.")
        if progress_callback: progress_callback(1, 1)
        return

    log(f" [3/3] Processing {total_courses} courses...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(execute_course_task, c, config, category_map): c for c in courses_queue}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            progress_pct = (i / total_courses) * 100
            course_id = result.get('id') or result.get('data', {}).get('id_curso')

            if result["status"] == "success":
                name = result["data"]["nombre_curso"][:30]
                bench = result.get("bench", "")
                log(f" {progress_pct:.1f}% OK | ID: {course_id} | {name} | {bench}")
            elif result["status"] == "skipped":
                log(f" {progress_pct:.1f}% SKIP | ID: {course_id} | {result.get('reason')}")
            else:
                log(f" {progress_pct:.1f}% ERR | ID: {course_id} | {result.get('error')}")

            # GUI Update
            if progress_callback:
                progress_callback(i, total_courses)

    log("--- ETL Process Finished Successfully ---")

if __name__ == "__main__":
    # Standard terminal execution
    run_pipeline()