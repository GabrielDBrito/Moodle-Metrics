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
        "nombre_curso": course.get("fullname"),
        "id_profesor": prof_id,
        "nombre_profesor": prof_name,
        "categoria_id": course.get("categoryid"),

        "n_estudiantes_procesados": g1["n_estudiantes_procesados"],

        "ind_1_1_cumplimiento": g1["ind_1_1_cumplimiento"],
        "ind_1_2_aprobacion": g1["ind_1_2_aprobacion"],
        "ind_1_3_promedio": g1["ind_1_3_promedio"],
        "ind_1_3_mediana": g1["ind_1_3_mediana"],
        "ind_1_3_desviacion": g1["ind_1_3_desviacion"],
        "ind_1_4_activos": g1["ind_1_4_activos"],
        "ind_1_5_finalizacion": g1["ind_1_5_finalizacion"],

        "ind_2_1_metodologia_activa_pct": g2.get("ind_2_1_metodologia_activa_pct"),
        "ind_2_2_balance_eval_pct": g2.get("ind_2_2_balance_eval_pct"),

        "ind_3_1_procrastinacion_pct": g3.get("ind_3_1_procrastinacion_pct"),
        "ind_3_2_feedback_ratio": g3.get("ind_3_2_feedback_ratio"),
    }
