# main.py (versión refactorizada)

import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

# --- Importaciones Simplificadas ---
from utils.db import save_analytics_data_to_db # ¡Solo importamos la función transaccional!
from utils.config_loader import load_config
from api.services import process_course_analytics
from api.client import get_target_courses, call_moodle_api

# --- Configuración (se mantiene igual) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

MAX_WORKERS = 5
BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD"]
INVALID_DEPARTMENTS = {"POSTG", "DIDA", "AE", "U_V"}

# --- Helpers de Categoría (se mantienen igual) ---
def build_category_map(categories):
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
    if not category_path: return None
    parts = [p.strip() for p in category_path.split("/") if p.strip()]
    if len(parts) < 2: return "Otros"
    return parts[1]

# --- WORKER: Función que ejecuta la tarea para cada curso ---
def execute_course_task(course: Dict[str, Any], config: Dict[str, Any], category_map: Dict[int, str]):
    """
    Función de trabajo que procesa y guarda los datos de un curso.
    """
    try:
        # 1. Calcular todos los indicadores
        data = process_course_analytics(config, course)
        if not data:
            return {"status": "skipped", "id": course["id"], "reason": "Datos insuficientes o <5 estudiantes"}

        data["nombre_materia"] = data["nombre_curso"] # dim_asignatura espera 'nombre_materia', que es el mismo que 'nombre_curso'

        # 2. Enriquecer el diccionario 'data' con información adicional
        categoria_id = data["categoria_id"]
        ruta_categoria = category_map.get(categoria_id, "")
        data["departamento"] = extract_departamento(ruta_categoria) or "OTRO"
        
        fecha_origen = data.get("startdate") or data.get("timecreated")
        if fecha_origen:
            dt = datetime.fromtimestamp(int(fecha_origen))
            anio = dt.year
            trimestre = (dt.month - 1) // 3 + 1
            data["id_tiempo"] = int(f"{anio}{trimestre}")
            data["anio"] = anio
            data["trimestre"] = trimestre
            data["nombre_periodo"] = f"{anio} T{trimestre}"
        else:
             data["id_tiempo"] = None # Manejar casos sin fecha

        # 3. Guardar en la base de datos de forma atómica y segura
        save_analytics_data_to_db(data)

        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "id": course["id"], "error": str(e)}

# --- MAIN: Orquestador Principal ---
def main():
    print("--- UNIMET Analytics: Pipeline de Extracción Idempotente ---")
    config = load_config()

    # Configuración de filtro de fechas (se mantiene igual)
    start_str = config['FILTERS']['start_date']
    min_ts = datetime.strptime(start_str, "%Y-%m-%d").timestamp()
    end_str = config['FILTERS']['end_date']
    max_ts = datetime.strptime(end_str, "%Y-%m-%d").timestamp() + 86399

    print("[INFO] Descargando categorías...")
    categories = call_moodle_api(config["MOODLE"], "core_course_get_categories")
    category_map = build_category_map(categories)

    print("[INFO] Descargando cursos...")
    raw_courses = get_target_courses(config)

    courses_queue = []
    for c in raw_courses:
        # SE ELIMINÓ LA COMPROBACIÓN DE IDs PROCESADOS
        if any(k in c["fullname"].upper() for k in BLACKLIST_KEYWORDS): continue
        cat_path = category_map.get(c.get("categoryid"), "").upper()
        if any(dep in cat_path for dep in INVALID_DEPARTMENTS): continue
        c_start = c.get("startdate", 0)
        if not (min_ts <= c_start <= max_ts): continue
        
        courses_queue.append(c)

    if not courses_queue:
        print("[INFO] No hay cursos nuevos o para actualizar en el rango de fechas. Proceso finalizado.")
        return

    print(f"[INFO] Se procesarán y actualizarán {len(courses_queue)} cursos.")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Ya no se abren archivos CSV aquí
        futures = {executor.submit(execute_course_task, c, config, category_map): c for c in courses_queue}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            pct = (i / len(futures)) * 100
            course_id = result.get('id') or result.get('data', {}).get('id_curso')

            if result["status"] == "success":
                course_name = result["data"]["nombre_curso"]
                print(f"[{i}/{len(futures)}] {pct:.1f}% OK   | ID: {course_id} | {course_name[:40]}")
            elif result["status"] == "skipped":
                print(f"[{i}/{len(futures)}] {pct:.1f}% SKIP | ID: {course_id} | Razón: {result.get('reason')}")
            else: # status == "error"
                print(f"[{i}/{len(futures)}] {pct:.1f}% ERROR| ID: {course_id} | Detalle: {result.get('error')}")

    print("[FIN] Ejecución terminada.")

if __name__ == "__main__":
    main()