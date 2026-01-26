import sys
import os
import csv
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.insert(0, current_dir)

from utils.config_loader import load_config
from api.services import get_full_course_analytics 
from api.client import get_target_courses 

FILE_FACTS = "hechos_curso.csv"
FILE_DIM_SUBJECT = "dim_asignaturas.csv"
MAX_WORKERS = 2
BLACKLIST_KEYWORDS = ["PRUEBA", "PLANTILLA", "COPIA", "SANDPIT", "TEST"]

csv_lock = threading.Lock()

def init_csvs():
    if not os.path.exists(FILE_FACTS):
        with open(FILE_FACTS, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id_curso", "id_asignatura", "id_profesor", "n_estudiantes",
                "tasa_cumplimiento", "tasa_aprobacion", "nota_promedio", 
                "nota_mediana", "nota_desviacion", "pct_activos", "tasa_finalizacion",
                "pct_metodologia_activa", "relacion_eval_noeval", "tasa_retencion",
                "indice_procrastinacion", "nivel_feedback", 
                "fecha_extraccion"
            ])
    if not os.path.exists(FILE_DIM_SUBJECT):
        with open(FILE_DIM_SUBJECT, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id_asignatura", "nombre_materia", "categoria_id"])

def get_processed_ids():
    """ Devuelve un set con los IDs de cursos ya procesados en el CSV """
    processed = set()
    if os.path.exists(FILE_FACTS):
        with open(FILE_FACTS, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)
                for row in reader:
                    if row: processed.add(int(row[0]))
            except StopIteration: pass
    return processed

def process_single_course(course, config):
    """
    Worker simplificado: Ya NO filtra por fecha ni nombre, 
    asume que recibe un curso válido y solo ejecuta la extracción.
    """
    c_id = course['id']
    
    # Objeto base de respuesta
    result = {
        'id': c_id,
        'course_info': course,
        'status': 'unknown'
    }
    
    try:
        # Llamada directa a la lógica de negocio
        stats = get_full_course_analytics(config, c_id)
        
        if stats:
            result.update({'status': 'success', 'stats': stats})
        else:
            result.update({'status': 'skipped_empty', 'reason': 'No data/Low enrollment'})
        return result
            
    except Exception as e:
        result.update({'status': 'error', 'error_msg': str(e)})
        return result

def main():
    print("--- UNIMET Analytics ETL: Pre-filtered Batch ---")
    executor = None
    
    try:
        config = load_config()
        date_str = config['FILTERS']['start_date']
        min_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
        
        init_csvs()
        processed_ids = get_processed_ids()
        
        print("[INFO] Phase 1: Descargando Catálogo Completo...")
        raw_courses = get_target_courses(config)
        if not raw_courses: return
        
        total_raw = len(raw_courses)
        print(f"       -> Catálogo bruto: {total_raw} cursos.")

        # --- PRE-FILTRADO (Aquí está la magia) ---
        print(f"[INFO] Aplicando filtros (Fecha > {date_str} y Palabras Clave)...")
        
        courses_to_run = []
        skipped_old = 0
        skipped_name = 0
        
        for c in raw_courses:
            # 1. Filtro Nombre
            if any(kw in c['fullname'].upper() for kw in BLACKLIST_KEYWORDS):
                skipped_name += 1
                continue
            
            # 2. Filtro Fecha
            start_date = c.get('startdate', 0)
            if start_date < min_ts:
                skipped_old += 1
                continue
                
            # 3. Filtro "Ya Procesado" (Resume Logic)
            if c['id'] in processed_ids:
                continue

            # Si pasa todo, lo agregamos a la lista de ejecución
            courses_to_run.append(c)

        print(f"       -> Descartados por Antigüedad: {skipped_old}")
        print(f"       -> Descartados por Nombre/Test: {skipped_name}")
        print(f"       -> Ya procesados anteriormente: {len(processed_ids)}")
        print(f"[INFO] Phase 2: Iniciando procesamiento de {len(courses_to_run)} cursos válidos...")
        
        if not courses_to_run:
            print("[WARN] No hay cursos nuevos que cumplan los criterios.")
            return

        # --- EJECUCIÓN ---
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        
        # Ahora el futuro solo recibe cursos válidos
        future_to_course = {
            executor.submit(process_single_course, c, config): c 
            for c in courses_to_run
        }

        completed = 0
        total_valid = len(courses_to_run)
        
        with open(FILE_FACTS, mode='a', newline='', encoding='utf-8') as f_facts, \
             open(FILE_DIM_SUBJECT, mode='a', newline='', encoding='utf-8') as f_dim:
            
            writer_facts = csv.writer(f_facts)
            writer_dim = csv.writer(f_dim)
            
            for future in as_completed(future_to_course):
                completed += 1
                res = future.result()
                
                pct = (completed / total_valid) * 100
                log_prefix = f"[{completed}/{total_valid}] {pct:.1f}%"
                
                if res['status'] == 'success':
                    stats = res['stats']
                    info = res['course_info']
                    
                    proc_val = stats['ind_3_1_procrastinacion']
                    if proc_val is None: proc_val = ""
                    
                    # Escritura Hechos
                    row_fact = [
                        stats['id_curso'], info.get('shortname', 'SIN_CODIGO'), "TBD",
                        stats['n_estudiantes'], stats['ind_1_1_cumplimiento'],
                        stats['ind_1_2_aprobacion'], stats['ind_1_3_promedio'],
                        stats['ind_1_3_mediana'], stats['ind_1_3_desviacion'],
                        stats['ind_1_4_activos'], stats['ind_1_5_finalizacion'],
                        stats['ind_2_1_metodologia'], stats['ind_2_2_relacion_eval'],
                        stats['ind_2_3_retencion'], proc_val, stats['ind_3_2_feedback'],
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    
                    # Escritura Dimensión
                    row_dim = [
                        info.get('shortname', 'SIN_CODIGO'),
                        info.get('fullname', 'Desconocido'),
                        info.get('categoryid', 0)
                    ]
                    
                    with csv_lock:
                        writer_facts.writerow(row_fact)
                        writer_dim.writerow(row_dim)
                        f_facts.flush()
                        f_dim.flush()

                    print(f"\r{log_prefix} [OK] ID {res['id']}".ljust(80), end="")
                
                elif res['status'] == 'error':
                    print(f"\r{log_prefix} [ERROR] ID {res['id']} {res.get('error_msg')}".ljust(80))
                
                else:
                    # Skipped empty (Pocos alumnos o sin notas)
                    print(f"\r{log_prefix} [SKIPPED] ID {res['id']} ({res.get('reason')})".ljust(80), end="")

    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupción detectada. Deteniendo...")
        if executor: executor.shutdown(wait=False, cancel_futures=True)
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback; traceback.print_exc()
        
    finally:
        if executor: executor.shutdown(wait=False)
        print("\nJob Finished.")

if __name__ == "__main__":
    main()