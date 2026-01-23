import sys
import os
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to system path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from utils.config_loader import load_config
from api.services import get_course_grade_stats

# --- Configuration Constants ---
OUTPUT_FILE = "dataset_experiencia_cursos.csv"
MAX_WORKERS = 2
# Keywords to identify non-academic courses (test environments, templates, etc.)
BLACKLIST_KEYWORDS = ["PRUEBA", "PLANTILLA", "COPIA", "SANDPIT", "TEST"]

# Thread-safe lock for CSV writing
csv_lock = threading.Lock()

def get_processed_ids(filename):
    """
    Reads the existing CSV file to retrieve a set of already processed course IDs.
    This enables the script to resume from the last checkpoint.
    """
    processed = set()
    if not os.path.exists(filename):
        return processed
    
    with open(filename, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader) # Skip header
            for row in reader:
                if row:
                    processed.add(int(row[0]))
        except StopIteration:
            pass
    return processed

def init_csv(filename):
    """
    Initializes the output CSV file with Spanish headers if it does not exist.
    Target Dimensional Model headers.
    """
    if not os.path.exists(filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id_curso", 
                "nombre_curso", 
                "id_profesor", 
                "n_estudiantes_procesados", 
                "ind_1_3_promedio", 
                "ind_1_3_mediana", 
                "ind_1_3_desviacion", 
                "ind_1_2_aprobacion", 
                "fecha_extraccion"
            ])

def process_single_course(course, config, total_courses, current_index):
    """
    Worker function to process a single course.
    Includes semantic filtering and exception handling.
    """
    course_id = course['id']
    course_name = course['fullname']
    course_name_upper = course_name.upper()
    
    # --- Semantic Filter ---
    # Check if the course name contains any blacklisted keywords indicating it is not a real course.
    for keyword in BLACKLIST_KEYWORDS:
        if keyword in course_name_upper:
            return {
                'status': 'filtered_name', 
                'data': None, 
                'id': course_id, 
                'name': course_name,
                'reason': keyword
            }
    
    try:
        # Fetch analytics from services
        stats = get_course_grade_stats(config, course_id)
        
        return {
            'status': 'success' if stats else 'skipped_empty',
            'data': stats,
            'id': course_id,
            'name': course_name
        }
    except Exception as e:
        return {
            'status': 'error', 
            'error_msg': str(e), 
            'id': course_id, 
            'name': course_name
        }

def main():
    print("-" * 50)
    print("   UNIMET Analytics ETL - Bulk Extraction Job")
    print("-" * 50 + "\n")

    executor = None
    ignored_courses_report = [] 
    
    try:
        config = load_config()
        init_csv(OUTPUT_FILE)
        processed_ids = get_processed_ids(OUTPUT_FILE)
        
        print("[INFO] Phase 1: Downloading Course Catalog...")
        all_courses = get_target_courses(config)
        
        if not all_courses:
            print("[ERROR] Failed to retrieve course catalog.")
            return

        # Filter out already processed courses
        pending_courses = [c for c in all_courses if c['id'] not in processed_ids]
        total_pending = len(pending_courses)
        print(f"[INFO] Total pending courses to process: {total_pending}")

        print("\n[INFO] Phase 2: Mass Extraction and Processing...")
        
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        future_to_course = {
            executor.submit(process_single_course, c, config, total_pending, i): c 
            for i, c in enumerate(pending_courses)
        }

        completed_count = 0
        
        with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            try:
                for future in as_completed(future_to_course):
                    completed_count += 1
                    res = future.result()
                    
                    progress = (completed_count / total_pending) * 100
                    
                    # Status logging
                    log_prefix = f"[{completed_count}/{total_pending}] {progress:.1f}%"
                    
                    if res['status'] == 'success':
                        status_msg = "[OK]"
                        detail_msg = ""
                    elif res['status'] == 'filtered_name':
                        status_msg = "[FILTERED]"
                        detail_msg = f"(Keyword: {res['reason']})"
                        ignored_courses_report.append(f"ID {res['id']}: {res['name']}")
                    elif res['status'] == 'skipped_empty':
                        status_msg = "[SKIPPED]"
                        detail_msg = "(Insufficient data or low enrollment)"
                    else:
                        status_msg = "[ERROR]"
                        detail_msg = f"({res.get('error_msg', 'Unknown error')})"

                    # Print formatted log line
                    print(f"\r{log_prefix} {status_msg} ID {res['id']} {detail_msg}".ljust(80), end="")
                    
                    # Persist data if successful
                    if res['status'] == 'success':
                        stats = res['data']
                        with csv_lock:
                            writer.writerow([
                                res['id'], 
                                res['name'], 
                                "TBD", # Professor ID Placeholder
                                stats['total_procesados'],
                                stats['ind_1_3_nota_promedio'],
                                stats['ind_1_3_nota_mediana'],
                                stats['ind_1_3_nota_desviacion'],
                                stats['ind_1_2_aprobacion'],
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ])
                            f.flush()

            except KeyboardInterrupt:
                print("\n\n[WARN] User interruption detected. Stopping executor...")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

    except KeyboardInterrupt:
        print("\n[INFO] Process stopped by user.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
    finally:
        if executor: 
            executor.shutdown(wait=False)
        
        # --- Final Report ---
        print("\n\n" + "="*50)
        print("SEMANTIC FILTER REPORT (EXCLUDED COURSES)")
        print("="*50)
        if ignored_courses_report:
            for line in ignored_courses_report:
                print(f" - {line}")
            print(f"\nTotal excluded: {len(ignored_courses_report)}")
        else:
            print("[INFO] No courses were excluded by keyword filters.")
        print("="*50)
        print("[INFO] Job finished.")

if __name__ == "__main__":
    main()