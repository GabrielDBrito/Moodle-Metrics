import sys
import os
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Dict, Any

from utils.db import insert_course_data, insert_dim_asignatura, insert_dim_tiempo
from utils.config_loader import load_config
from api.services import process_course_analytics
from api.client import get_target_courses, call_moodle_api

# --------------------------------------------------
# PATH CONFIG
# --------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --------------------------------------------------
# OUTPUT FILES
# --------------------------------------------------
FACTS_FILENAME = "hechos_curso_grupo1.csv"
DIM_PROF_FILENAME = "dim_profesores.csv"
DIM_SUBJ_FILENAME = "dim_asignaturas.csv"

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------
MAX_WORKERS = 5
BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD"]
INVALID_DEPARTMENTS = {"POSTG", "DIDA", "AE", "U_V"}

csv_lock = threading.Lock()

# --------------------------------------------------
# CATEGORY HELPERS (COPIADO DEL CÓDIGO QUE FUNCIONABA)
# --------------------------------------------------
def build_category_map(categories):
    """
    {category_id: 'FACULTAD/DEPARTAMENTO/CATEGORIA'}
    """
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

# --------------------------------------------------
# CSV INIT
# --------------------------------------------------
def initialize_storage():
    if not os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, "w", newline="", encoding="utf-8") as f:
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
                "ind_1_3_nota_promedio",
                "ind_1_3_nota_mediana",
                "ind_1_3_nota_desviacion",
                "ind_1_4_participacion",
                "ind_1_5_finalizacion",

                "ind_2_1_metod_activa",
                "ind_2_2_ratio_eval",

                "ind_3_1_procrastinacion",
                "ind_3_2_feedback",

                "fecha_extraccion"
            ])

    if not os.path.exists(DIM_PROF_FILENAME):
        with open(DIM_PROF_FILENAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["id_profesor", "nombre_profesor"])

    if not os.path.exists(DIM_SUBJ_FILENAME):
        with open(DIM_SUBJ_FILENAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["id_asignatura", "nombre_materia", "categoria_id"])

# --------------------------------------------------
# LOADERS
# --------------------------------------------------
def load_processed_course_ids() -> Set[int]:
    ids = set()
    if os.path.exists(FACTS_FILENAME):
        with open(FACTS_FILENAME, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    ids.add(int(r[0]))
    return ids

def load_existing_professor_ids() -> Set[int]:
    ids = set()
    if os.path.exists(DIM_PROF_FILENAME):
        with open(DIM_PROF_FILENAME, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    ids.add(int(r[0]))
    return ids

# --------------------------------------------------
# WORKER
# --------------------------------------------------
def execute_course_task(course: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = process_course_analytics(config, course)
        if not data:
            return {"status": "skipped", "id": course["id"], "reason": "Insufficient data/students (<5)"}
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "id": course["id"], "error": str(e)}

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    print("--- UNIMET Analytics: Pipeline de Extracción ---")

    config = load_config()
    initialize_storage()

    processed_ids = load_processed_course_ids()
    existing_professors = load_existing_professor_ids()

    print("[INFO] Descargando categorías...")
    categories = call_moodle_api(config["MOODLE"], "core_course_get_categories")
    category_map = build_category_map(categories)

    print("[INFO] Descargando cursos...")
    raw_courses = get_target_courses(config)

    courses_queue = []
    for c in raw_courses:

        if c["id"] in processed_ids:
            continue

        if any(k in c["fullname"].upper() for k in BLACKLIST_KEYWORDS):
            continue

        cat_path = category_map.get(c.get("categoryid"), "").upper()
        if any(dep in cat_path for dep in INVALID_DEPARTMENTS):
            continue

        courses_queue.append(c)

    print(f"[INFO] Se procesarán {len(courses_queue)} cursos")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor, \
         open(FACTS_FILENAME, "a", newline="", encoding="utf-8") as f_facts, \
         open(DIM_PROF_FILENAME, "a", newline="", encoding="utf-8") as f_prof, \
         open(DIM_SUBJ_FILENAME, "a", newline="", encoding="utf-8") as f_subj:

        writer_facts = csv.writer(f_facts)
        writer_prof = csv.writer(f_prof)
        writer_subj = csv.writer(f_subj)

        futures = {executor.submit(execute_course_task, c, config): c for c in courses_queue}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            pct = (i / len(futures)) * 100

            if result["status"] == "success":
                d = result["data"]

                categoria_id = d["categoria_id"]
                departamento = category_map.get(categoria_id, "OTRO")

                with csv_lock:
                    writer_facts.writerow([
                        d["id_curso"],
                        d["id_asignatura"],
                        d["nombre_curso"],
                        d["id_profesor"],
                        categoria_id,
                        d["n_estudiantes_procesados"],

                        d["ind_1_1_cumplimiento"],
                        d["ind_1_2_aprobacion"],
                        d["ind_1_3_nota_promedio"],
                        d["ind_1_3_nota_mediana"],
                        d["ind_1_3_nota_desviacion"],
                        d["ind_1_4_participacion"],
                        d["ind_1_5_finalizacion"],

                        d["ind_2_1_metod_activa"],
                        d["ind_2_2_ratio_eval"],

                        d["ind_3_1_procrastinacion"],
                        d["ind_3_2_feedback"],

                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])

                    if d["id_profesor"] not in existing_professors:
                        writer_prof.writerow([d["id_profesor"], d["nombre_profesor"]])
                        existing_professors.add(d["id_profesor"])

                    writer_subj.writerow([d["id_asignatura"], d["nombre_curso"], categoria_id])

                # ---------------- SUPABASE ----------------
                fecha_origen = d.get("startdate") or d.get("enddate") or d.get("timecreated")
                if fecha_origen:
                    dt = datetime.fromtimestamp(int(fecha_origen))
                    anio = dt.year
                    trimestre = (dt.month - 1) // 3 + 1
                    id_tiempo = int(f"{anio}{trimestre}")
                else:
                    id_tiempo = None

                insert_dim_asignatura({
                    "id_asignatura": d["id_asignatura"],
                    "nombre_materia": d["nombre_curso"],
                    "departamento": departamento
                })

                insert_dim_tiempo({
                    "id_tiempo": id_tiempo,
                    "anio": anio,
                    "trimestre": trimestre,
                    "nombre_periodo": f"{anio} T{trimestre}"
                })

                insert_course_data({
                    **d,
                    "departamento": departamento,
                    "profesor": d["nombre_profesor"],
                    "id_tiempo": id_tiempo
                })

                print(f"[{i}/{len(futures)}] {pct:.1f}% OK | {d['nombre_curso'][:40]}")

            elif result["status"] == "skipped":
                print(f"[{i}/{len(futures)}] SKIP ID {result['id']}")

            else:
                print(f"[{i}/{len(futures)}] ERROR ID {result['id']} → {result['error']}")

    print("[FIN] Ejecución terminada.")

if __name__ == "__main__":
    main()
