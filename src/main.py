import sys
import os
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Dict, Any

# Configure path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: 
    sys.path.insert(0, current_dir)

from utils.config_loader import load_config
from api.services import process_course_analytics
from api.client import get_target_courses 

# --- OUTPUT CONFIGURATION (SPANISH FILES) ---
FACTS_FILENAME = "hechos_curso_grupo1.csv"
DIM_PROF_FILENAME = "dim_profesores.csv"
DIM_SUBJ_FILENAME = "dim_asignaturas.csv"

# Performance settings
MAX_WORKERS = 5

# Keywords to identify and exclude testing/backup courses
BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD"]

# Lock to ensure thread-safe CSV writing
csv_lock = threading.Lock()

def initialize_storage() -> None:
    """
    Initializes CSV files with their respective SPANISH headers if they do not exist.
    """
    # 1. Facts Table (Indicators) - HEADERS IN SPANISH FOR BI TOOLS
    if not os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id_curso", 
                "id_asignatura", 
                "nombre_curso", 
                "id_profesor", 
                "categoria_id",      
                "n_estudiantes_procesados", 
                "ind_1_1_cumplimiento", 
                "ind_1_2_aprobacion",
                "ind_1_3_promedio", 
                "ind_1_3_mediana", 
                "ind_1_3_desviacion",
                "ind_1_4_activos", 
                "ind_1_5_finalizacion", 
                "fecha_extraccion"
            ])

    # 2. Professors Dimension - HEADERS IN SPANISH
    if not os.path.exists(DIM_PROF_FILENAME):
        with open(DIM_PROF_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id_profesor", "nombre_profesor"])

    # 3. Subjects Dimension - HEADERS IN SPANISH
    if not os.path.exists(DIM_SUBJ_FILENAME):
        with open(DIM_SUBJ_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id_asignatura", "nombre_materia", "categoria_id"])

def load_processed_course_ids() -> Set[int]:
    """
    Retrieves the set of course IDs that have already been processed to enable 
    execution resumption.
    """
    processed = set()
    if os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)  # Skip header
                for row in reader:
                    if row: 
                        processed.add(int(row[0]))
            except StopIteration:
                pass
    return processed

def load_existing_professor_ids() -> Set[int]:
    """
    Retrieves the set of professor IDs already recorded in the dimension file
    to prevent duplicate entries.
    """
    prof_ids = set()
    if os.path.exists(DIM_PROF_FILENAME):
        with open(DIM_PROF_FILENAME, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)  # Skip header
                for row in reader:
                    if row: 
                        try:
                            prof_ids.add(int(row[0]))
                        except ValueError: 
                            continue
            except StopIteration:
                pass
    return prof_ids

def execute_course_task(course: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function to process a single course. 
    """
    try:
        # Delegate business logic and KPI calculation
        analytics_result = process_course_analytics(config, course)
        
        if analytics_result:
            return {'status': 'success', 'data': analytics_result}
        else:
            return {
                'status': 'skipped', 
                'id': course['id'], 
                'reason': 'Insufficient data/students (<5)'
            }
            
    except Exception as e:
        return {'status': 'error', 'id': course['id'], 'error': str(e)}

def main() -> None:
    print("--- UNIMET Analytics: Pipeline de Extracción (Output en Español) ---")
    executor = None
    
    try:
        config = load_config()
        
        # --- TEMPORAL FILTER CONFIGURATION ---
        start_str = config['FILTERS']['start_date']
        min_ts = datetime.strptime(start_str, "%Y-%m-%d").timestamp()
        
        end_str = config['FILTERS']['end_date']
        # Add 23:59:59 to cover the entire end day
        max_ts = datetime.strptime(end_str, "%Y-%m-%d").timestamp() + 86399 
        
        print(f"[CONFIG] Rango de fechas: {start_str} al {end_str}")

        initialize_storage()
        
        # Load current state
        processed_ids = load_processed_course_ids()
        existing_professors = load_existing_professor_ids() 
        
        print("[INFO] Descargando catálogo de cursos desde Moodle...")
        raw_courses = get_target_courses(config)
        if not raw_courses: 
            print("[ERROR] No se encontraron cursos o falló la conexión.")
            return

        # --- PRE-PROCESSING FILTERING ---
        courses_queue = []
        for course in raw_courses:
            # 1. Resumption
            if course['id'] in processed_ids: 
                continue
            
            # 2. Blacklist (Garbage Names)
            course_name_upper = course['fullname'].upper()
            if any(keyword in course_name_upper for keyword in BLACKLIST_KEYWORDS): 
                continue
            
            # 3. Postgraduate Filter (C...)
            short_code = course.get('shortname', '').strip().upper()
            if short_code.startswith('C'): 
                continue

            # 4. Date Filter (Bidirectional)
            c_start = course.get('startdate', 0)
            if c_start < min_ts: continue # Too Old
            if c_start > max_ts: continue # Future (2026+)
            
            courses_queue.append(course)

        print(f"[INFO] Se procesarán {len(courses_queue)} cursos nuevos...")

        if not courses_queue: 
            print("[INFO] Todo al día.")
            return

        # --- PARALLEL EXECUTION ---
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        future_to_course = {
            executor.submit(execute_course_task, c, config): c 
            for c in courses_queue
        }

        completed_count = 0
        total_count = len(courses_queue)
        
        # Open files once
        with open(FACTS_FILENAME, 'a', newline='', encoding='utf-8') as f_facts, \
             open(DIM_PROF_FILENAME, 'a', newline='', encoding='utf-8') as f_prof, \
             open(DIM_SUBJ_FILENAME, 'a', newline='', encoding='utf-8') as f_subj:
            
            writer_facts = csv.writer(f_facts)
            writer_prof = csv.writer(f_prof)
            writer_subj = csv.writer(f_subj)
            
            for future in as_completed(future_to_course):
                completed_count += 1
                result = future.result()
                
                # Progress logging
                progress_pct = (completed_count / total_count) * 100
                log_prefix = f"[{completed_count}/{total_count}] {progress_pct:.1f}%"
                
                if result['status'] == 'success':
                    data = result['data']
                    
                    # Prepare rows matching the SPANISH headers defined in initialize_storage
                    # Assuming keys in 'data' dictionary from services.py are still: 
                    # 'id_curso', 'ind_1_3_promedio', etc.
                    row_fact = [
                        data['id_curso'], 
                        data['id_asignatura'], 
                        data['nombre_curso'], 
                        data['id_profesor'], 
                        data['categoria_id'],  
                        data['n_estudiantes_procesados'], 
                        data['ind_1_1_cumplimiento'], 
                        data['ind_1_2_aprobacion'], 
                        data['ind_1_3_promedio'], 
                        data['ind_1_3_mediana'], 
                        data['ind_1_3_desviacion'], 
                        data['ind_1_4_activos'], 
                        data['ind_1_5_finalizacion'], 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    
                    # Thread-safe writing
                    with csv_lock:
                        writer_facts.writerow(row_fact)
                        
                        # Professor Dimension
                        p_id = int(data['id_profesor'])
                        if p_id not in existing_professors:
                            writer_prof.writerow([p_id, data['nombre_profesor']])
                            existing_professors.add(p_id) 
                        
                        # Subject Dimension
                        writer_subj.writerow([
                            data['id_asignatura'], 
                            data['nombre_curso'], 
                            data['categoria_id']
                        ])
                        
                        f_facts.flush()
                        f_prof.flush()
                        f_subj.flush()
                    
                    short_name = (data['nombre_curso'][:35] + '..') if len(data['nombre_curso']) > 35 else data['nombre_curso']
                    print(f"\r{log_prefix} [OK] ID {data['id_curso']} | {short_name}".ljust(100), end="")
                
                elif result['status'] == 'skipped':
                     print(f"\r{log_prefix} [SKIP] ID {result['id']} ({result['reason']})".ljust(100), end="")
                
                else:
                    print(f"\r{log_prefix} [ERROR] ID {result['id']}: {result['error']}".ljust(100))

    except KeyboardInterrupt:
        if executor: 
            executor.shutdown(wait=False, cancel_futures=True)
        print("\n[STOP] Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
    finally:
        if executor: 
            executor.shutdown(wait=False)
        print("\n[FIN] Ejecución terminada.")

if __name__ == "__main__":
    main()