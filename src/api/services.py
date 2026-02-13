import re
from typing import Dict, Any, Optional, Tuple
from .client import call_moodle_api
from .indicators.group1_results import calculate_group1_metrics
from .indicators.group2_design import calculate_design_metrics
from .indicators.group3_behavior import calculate_group3_metrics_from_grades

def get_clean_course_name(fullname: Optional[str]) -> str:
    """
    Strips instructor name from course title.
    Example: "Data Systems - J. Doe" -> "Data Systems"
    """
    if not fullname:
        return "UNNAMED_COURSE"
    return fullname.split("-")[0].strip()

def get_subject_code(shortname: Optional[str]) -> str:
    """Extracts the first part of the shortname as the subject code."""
    if not shortname:
        return "NO_CODE"
    return re.split(r"[-_ ]", shortname)[0].strip()

def identify_instructor(course_id: int, config: Dict[str, Any]) -> Tuple[int, str]:
    """
    Fetches enrolled users and identifies the primary instructor.
    Priority roles: 3 (Editing Teacher), 4 (Teacher), 1 (Manager).
    """
    users = call_moodle_api(
        config["MOODLE"],
        "core_enrol_get_enrolled_users",
        courseid=course_id
    ) or []

    # Common Moodle role IDs for instructors
    for role_id in (3, 4, 1):
        for user in users:
            for role in user.get("roles", []):
                if role.get("roleid") == role_id:
                    return user["id"], user["fullname"]

    return 0, "Unassigned"

def process_course_analytics(config: Dict[str, Any], course: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main orchestrator for course data extraction and KPI calculation.
    Collects raw components (num/den) for accurate BI aggregation.
    """
    course_id = course["id"]

    # 1. Fetch raw data from Moodle API
    grades_report = call_moodle_api(
        config["MOODLE"],
        "gradereport_user_get_grade_items",
        courseid=course_id,
        userid=0
    )

    if not grades_report:
        return None

    # 2. Calculate Group 1 Metrics (Results & Performance)
    g1 = calculate_group1_metrics(grades_report)
    if not g1:
        return None

    # 3. Calculate Group 2 Metrics (Instructional Design)
    course_contents = call_moodle_api(
        config["MOODLE"],
        "core_course_get_contents",
        courseid=course_id
    )
    g2 = calculate_design_metrics(course_contents, grades_report) or {}

    # 4. Calculate Group 3 Metrics (Behavior & Interaction)
    g3 = calculate_group3_metrics_from_grades(grades_report) or {}

    # 5. Identify course owner
    prof_id, prof_name = identify_instructor(course_id, config)
    
    clean_name = get_clean_course_name(course.get("fullname"))

    # Consolidated results including raw components for BI
    return {
        "id_curso": course_id,
        "id_asignatura": get_subject_code(course.get("shortname")),
        "nombre_curso": clean_name,
        "nombre_materia": clean_name, # Added to prevent KeyErrors in DB transactions
        "id_profesor": prof_id,
        "nombre_profesor": prof_name,
        "categoria_id": course.get("categoryid"),

        # Timestamps
        "startdate": course.get("startdate"),
        "enddate": course.get("enddate"),
        "timecreated": course.get("timecreated"),
        "timemodified": course.get("timemodified"),

        # Enrollment Counts
        "n_estudiantes_procesados": g1.get("n_estudiantes_procesados", 0),
        "n_estudiantes_totales": g1.get("n_estudiantes_totales", 0),

        # --- GROUP 1 COMPONENTS ---
        "ind_1_1_cumplimiento": g1.get("ind_1_1_cumplimiento"),
        "ind_1_1_num": g1.get("ind_1_1_num"),
        "ind_1_1_den": g1.get("ind_1_1_den"),

        "ind_1_2_aprobacion": g1.get("ind_1_2_aprobacion"),
        "ind_1_2_num": g1.get("ind_1_2_num"),
        "ind_1_2_den": g1.get("ind_1_2_den"),

        "ind_1_3_nota_promedio": g1.get("ind_1_3_nota_promedio"),
        "ind_1_3_num": g1.get("ind_1_3_num"), # Sum of grades
        "ind_1_3_den": g1.get("ind_1_3_den"), # Count of grades
        "ind_1_3_nota_mediana": g1.get("ind_1_3_nota_mediana"),
        "ind_1_3_nota_desviacion": g1.get("ind_1_3_nota_desviacion"),

        "ind_1_4_participacion": g1.get("ind_1_4_participacion"),
        "ind_1_4_num": g1.get("ind_1_4_num"),
        "ind_1_4_den": g1.get("ind_1_4_den"),

        "ind_1_5_finalizacion": g1.get("ind_1_5_finalizacion"),
        "ind_1_5_num": g1.get("ind_1_5_num"),
        "ind_1_5_den": g1.get("ind_1_5_den"),

        # --- GROUP 2 COMPONENTS ---
        "ind_2_1_metod_activa": g2.get("ind_2_1_metod_activa"),
        "ind_2_1_num": g2.get("ind_2_1_num"),
        "ind_2_1_den": g2.get("ind_2_1_den"),

        "ind_2_2_ratio_eval": g2.get("ind_2_2_ratio_eval"),
        "ind_2_2_num": g2.get("ind_2_2_num"),
        "ind_2_2_den": g2.get("ind_2_2_den"),

        # --- GROUP 3 COMPONENTS ---
        "ind_3_1_selectividad": g3.get("ind_3_1_selectividad"),
        "ind_3_1_num": g3.get("ind_3_1_num"),
        "ind_3_1_den": g3.get("ind_3_1_den"),

        "ind_3_2_feedback": g3.get("ind_3_2_feedback"),
        "ind_3_2_num": g3.get("ind_3_2_num"),
        "ind_3_2_den": g3.get("ind_3_2_den"),
    }