#services.py
from typing import Dict, Any, Optional, Tuple
import re

from .client import call_moodle_api
from .indicators.group1_results import calculate_group1_metrics
from .indicators.group2_design import calculate_design_metrics
from .indicators.group3_behavior import calculate_group3_metrics_from_grades




 
def _sanitize_subject_code(shortname: Optional[str]) -> str:
    if not shortname:
        return "NO_CODE"
    return re.split(r"[-_ ]", shortname)[0].strip()


def _identify_instructor(course_id: int, config: Dict[str, Any]) -> Tuple[int, str]:
    users = call_moodle_api(
        config["MOODLE"],
        "core_enrol_get_enrolled_users",
        courseid=course_id
    ) or []

    for role_id in (3, 4, 1):
        for u in users:
            for r in u.get("roles", []):
                if r.get("roleid") == role_id:
                    return u["id"], u["fullname"]

    return 0, "Unassigned"


def process_course_analytics(config: Dict[str, Any], course: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    course_id = course["id"]

    grades = call_moodle_api(
        config["MOODLE"],
        "gradereport_user_get_grade_items",
        courseid=course_id,
        userid=0
    )

    if not grades:
        return None

    g1 = calculate_group1_metrics(grades)
    if not g1:
        return None

    contents = call_moodle_api(
        config["MOODLE"],
        "core_course_get_contents",
        courseid=course_id
    )

    g2 = calculate_design_metrics(contents, grades) or {}
    g3 = calculate_group3_metrics_from_grades(grades) or {}

    prof_id, prof_name = _identify_instructor(course_id, config)
    


    return {
        "id_curso": course_id,
        "id_asignatura": _sanitize_subject_code(course.get("shortname")),
        "nombre_curso": _sanitize_course_name(course.get("fullname")),
        "id_profesor": prof_id,
        "nombre_profesor": prof_name,
        
        "categoria_id": course.get("categoryid"),

        "startdate": course.get("startdate"),
        "enddate": course.get("enddate"),
        "timecreated": course.get("timecreated"),
        "timemodified": course.get("timemodified"),

        "n_estudiantes_procesados": g1["n_estudiantes_procesados"],

        # --- GRUPO 1 ---
        "ind_1_1_cumplimiento": g1["ind_1_1_cumplimiento"],
        "ind_1_2_aprobacion": g1["ind_1_2_aprobacion"],
        "ind_1_3_nota_promedio": g1["ind_1_3_nota_promedio"],
        "ind_1_3_nota_mediana": g1["ind_1_3_nota_mediana"],
        "ind_1_3_nota_desviacion": g1["ind_1_3_nota_desviacion"],
        "ind_1_4_participacion": g1.get("ind_1_4_activos"),

        "ind_1_5_finalizacion": g1["ind_1_5_finalizacion"],

        # --- GRUPO 2 ---
        "ind_2_1_metod_activa": g2.get("ind_2_1_metod_activa"),
        "ind_2_2_ratio_eval": g2.get("ind_2_2_ratio_eval"),

        # --- GRUPO 3 ---
        "ind_3_1_selectividad": g3.get("ind_3_1_selectividad"),
        "ind_3_2_feedback": g3.get("ind_3_2_feedback"),
    }

def get_professor_name(course_id: int, config: Dict[str, Any]) -> Tuple[int, str]:
    # Primero obtenemos los usuarios inscritos en el curso
    users = call_moodle_api(
        config["MOODLE"],
        "core_enrol_get_enrolled_users",
        courseid=course_id
    ) or []

    # Buscamos el primer usuario con rol de profesor (por ejemplo roleid 3 o 4)
    for role_id in (3, 4):
        for user in users:
            for role in user.get("roles", []):
                if role.get("roleid") == role_id:
                    prof_id = user["id"]

                    # Ahora hacemos una llamada a core_user_get_users para obtener el nombre completo
                    response = call_moodle_api(
                        config["MOODLE"],
                        "core_user_get_users",
                        params={"criteria": [{"key": "id", "value": str(prof_id)}]}
                    )
                    if response and "users" in response and len(response["users"]) > 0:
                        prof_user = response["users"][0]
                        full_name = f"{prof_user.get('firstname', '')} {prof_user.get('lastname', '')}".strip()
                        return prof_id, full_name if full_name else "SIN NOMBRE"

                    # Si no pudo obtener el nombre, al menos devolvemos el id
                    return prof_id, "SIN NOMBRE"

    return 0, "Unassigned"

def _sanitize_course_name(fullname: Optional[str]) -> str:
    """
    Si el nombre tiene un guion, se queda solo con la parte izquierda.
    Ej: "Ciudadanía - D. Leal" -> "Ciudadanía"
    """
    if not fullname:
        return "SIN NOMBRE"
    
    # Divide el texto en el primer guion que encuentre y toma la primera parte
    clean_name = fullname.split("-")[0]
    
    # Elimina espacios en blanco sobrantes al inicio y final
    return clean_name.strip() 