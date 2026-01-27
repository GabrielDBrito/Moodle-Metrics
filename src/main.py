import sys
import os
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set, Dict, Any, Optional

# Ensure local modules can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: 
    sys.path.insert(0, current_dir)

from utils.config_loader import load_config
from api.services import process_course_analytics
from api.client import get_target_courses 

# --- OUTPUT CONFIGURATION ---
FACTS_FILENAME = "hechos_curso_grupo1.csv"
DIM_PROF_FILENAME = "dim_profesores.csv"
DIM_SUBJ_FILENAME = "dim_asignaturas.csv"

# Performance Tuning
MAX_WORKERS = 5

# Filtering Rules
# Courses containing these substrings in their name will be ignored.
BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT"]

# Thread synchronization primitive for CSV writing
csv_lock = threading.Lock()

def initialize_storage() -> None:
    """
    Initializes CSV storage files with their respective headers if they do not exist.
    """
    # 1. Fact Table (Course Indicators)
    if not os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id_curso", 
                "id_asignatura", 
                "nombre_curso", 
                "id_profesor", 
                "categoria_id",      
                "n_estudiantes", 
                "tasa_cumplimiento", 
                "tasa_aprobacion",
                "nota_promedio", 
                "nota_mediana", 
                "nota_desviacion",
                "pct_activos", 
                "tasa_finalizacion", 
                "fecha_extraccion"
            ])

    # 2. Dimension: Professors
    if not os.path.exists(DIM_PROF_FILENAME):
        with open(DIM_PROF_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id_profesor", "nombre_profesor"])

    # 3. Dimension: Subjects
    if not os.path.exists(DIM_SUBJ_FILENAME):
        with open(DIM_SUBJ_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id_asignatura", "nombre_materia", "categoria_id"])

def load_processed_course_ids() -> Set[int]:
    """
    Reads the fact table to retrieve IDs of courses that have already been processed.
    This enables the script to resume operation after an interruption.
    
    Returns:
        A set of integers representing processed course IDs.
    """
    processed_ids = set()
    if os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)  # Skip header
                for row in reader:
                    if row: 
                        processed_ids.add(int(row[0]))
            except StopIteration:
                pass
    return processed_ids

def execute_course_task(course: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function to process a single course. 
    Intended to be run inside a ThreadPoolExecutor.
    
    Args:
        course: Dictionary containing raw course metadata.
        config: Application configuration.
        
    Returns:
        A dictionary containing the execution status ('success', 'skipped', 'error')
        and the resulting data or error message.
    """
    try:
        # Delegate logic to the service layer (3-Layer Architecture)
        analytics_result = process_course_analytics(config, course)
        
        if analytics_result:
            # --- GLOBAL QUALITY FILTER ---
            # Discard courses where the average grade is essentially zero,
            # indicating that grading has not occurred.
            avg_grade = analytics_result.get('ind_1_3_promedio', 0.0)
            if avg_grade <= 0.1:
                 return {
                     'status': 'skipped', 
                     'id': course['id'], 
                     'reason': 'Zero average grade (Ungraded)'
                 }
            
            return {'status': 'success', 'data': analytics_result}
        else:
            # Service returns None if the course fails validation (e.g., too few students)
            return {
                'status': 'skipped', 
                'id': course['id'], 
                'reason': 'Insufficient data/students'
            }
            
    except Exception as e:
        return {'status': 'error', 'id': course['id'], 'error': str(e)}

def main() -> None:
    print("--- UNIMET Analytics: Extraction Pipeline (Production) ---")
    executor = None
    
    try:
        config = load_config()
        
        # Parse filter date
        date_str = config['FILTERS']['start_date']
        min_timestamp = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
        
        # Initialize storage and state
        initialize_storage()
        processed_ids = load_processed_course_ids()
        
        print("[INFO] Fetching course catalog...")
        raw_courses = get_target_courses(config)
        if not raw_courses: 
            print("[ERROR] No courses found in the source.")
            return

        # Pre-execution Filtering (Blacklist & Date)
        courses_queue = []
        for course in raw_courses:
            # Resume capability: skip already processed IDs
            if course['id'] in processed_ids: 
                continue
            
            # Name filter: skip test/sandbox courses
            course_name_upper = course['fullname'].upper()
            if any(keyword in course_name_upper for keyword in BLACKLIST_KEYWORDS): 
                continue
            
            # Date filter: skip old courses
            if course.get('startdate', 0) < min_timestamp: 
                continue
            
            courses_queue.append(course)

        print(f"[INFO] Queued {len(courses_queue)} new courses for processing...")

        if not courses_queue: 
            print("[INFO] No new courses to process. System is up to date.")
            return

        # Parallel Execution
        # We use ThreadPoolExecutor for I/O bound tasks (API calls)
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        future_to_course = {
            executor.submit(execute_course_task, c, config): c 
            for c in courses_queue
        }

        completed_count = 0
        total_count = len(courses_queue)
        
        # Open CSV files once and keep handles open for performance
        with open(FACTS_FILENAME, 'a', newline='', encoding='utf-8') as f_facts, \
             open(DIM_PROF_FILENAME, 'a', newline='', encoding='utf-8') as f_prof, \
             open(DIM_SUBJ_FILENAME, 'a', newline='', encoding='utf-8') as f_subj:
            
            writer_facts = csv.writer(f_facts)
            writer_prof = csv.writer(f_prof)
            writer_subj = csv.writer(f_subj)
            
            for future in as_completed(future_to_course):
                completed_count += 1
                result = future.result()
                
                # Progress calculation
                progress_pct = (completed_count / total_count) * 100
                log_prefix = f"[{completed_count}/{total_count}] {progress_pct:.1f}%"
                
                if result['status'] == 'success':
                    data = result['data']
                    
                    # Prepare rows
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
                    
                    row_prof = [data['id_profesor'], data['nombre_profesor']]
                    row_subj = [data['id_asignatura'], data['nombre_curso'], data['categoria_id']]
                    
                    # Thread-safe writing
                    with csv_lock:
                        writer_facts.writerow(row_fact)
                        writer_prof.writerow(row_prof)
                        writer_subj.writerow(row_subj)
                        
                        # Flush to ensure data persists immediately
                        f_facts.flush()
                        f_prof.flush()
                        f_subj.flush()
                    
                    # Console Logging
                    short_name = (data['nombre_curso'][:30] + '..') if len(data['nombre_curso']) > 30 else data['nombre_curso']
                    print(f"\r{log_prefix} [OK] ID {data['id_curso']} | {short_name}".ljust(90), end="")
                
                elif result['status'] == 'skipped':
                     print(f"\r{log_prefix} [SKIP] ID {result['id']} ({result['reason']})".ljust(90), end="")
                
                else:
                    print(f"\r{log_prefix} [ERROR] ID {result['id']}: {result['error']}".ljust(90))

    except KeyboardInterrupt:
        if executor: 
            executor.shutdown(wait=False, cancel_futures=True)
        print("\n[STOP] Process interrupted by user.")
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        
    finally:
        if executor: 
            executor.shutdown(wait=False)
        print("\n[FINISH] Execution completed.")

if __name__ == "__main__":
    main()