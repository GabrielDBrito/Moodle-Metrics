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

    for user in users:
        for role in user.get("roles", []):
            if role.get("roleid") in (3, 4, 1):
                return user["id"], user["fullname"]

    return 0, "Unassigned"

def process_course_analytics(config: Any, course: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main orchestrator for course data extraction and KPI calculation.
    Handles dynamic parameters from THRESHOLDS section in config.ini.
    """
    course_id = course["id"]

    # --- 0. Extract Dynamic Thresholds from Config ---
    # These parameters are passed to the indicator functions for modular logic.
    thresholds = config['THRESHOLDS']
    params = {
        'min_students': int(thresholds.get('min_students', 5)),
        'excellence_score': float(thresholds.get('excellence_score', 18.0)),
        'active_density': float(thresholds.get('active_density', 0.40)),
        # Whitelist remains a hidden business rule (5%) as requested, 
        # but is added to params for code independence.
        'whitelist_min': 0.05 
    }

    # 1. Fetch raw data from Moodle API (Grades)
    grades_report = call_moodle_api(
        config["MOODLE"],
        "gradereport_user_get_grade_items",
        courseid=course_id,
        userid=0
    )

    if not grades_report:
        return None

    # 2. Calculate Group 1 Metrics (Results & Performance)
    # Passes 'params' to handle dynamic student counts and activity density.
    g1 = calculate_group1_metrics(grades_report, params)
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
    # Passes 'params' to handle the dynamic excellence threshold (e.g. 18/20).
    g3 = calculate_group3_metrics_from_grades(grades_report, params) or {}

    # 5. Metadata Enrichment
    prof_id, prof_name = identify_instructor(course_id, config)
    clean_name = get_clean_course_name(course.get("fullname"))

    # Consolidated results including raw components for BI aggregation
    return {
        "id_curso": course_id,
        "id_asignatura": get_subject_code(course.get("shortname")),
        "nombre_curso": clean_name,
        "nombre_materia": clean_name, 
        "id_profesor": prof_id,
        "nombre_profesor": prof_name,
        "categoria_id": course.get("categoryid"),

        # Timestamps
        "startdate": course.get("startdate"),
        "enddate": course.get("enddate"),
        "timecreated": course.get("timecreated"),
        "timemodified": course.get("timemodified"),

        # Population
        "n_estudiantes_totales": g1.get("n_estudiantes_totales", 0),

        # --- GROUP 1 COMPONENTS ---
        "ind_1_1_cumplimiento": g1.get("ind_1_1_cumplimiento"),
        "ind_1_1_num": g1.get("ind_1_1_num"),
        "ind_1_1_den": g1.get("ind_1_1_den"),

        "ind_1_2_aprobacion": g1.get("ind_1_2_aprobacion"),
        "ind_1_2_num": g1.get("ind_1_2_num"),
        "ind_1_2_den": g1.get("ind_1_2_den"),

        "ind_1_3_nota_promedio": g1.get("ind_1_3_nota_promedio"),
        "ind_1_3_num": g1.get("ind_1_3_num"), 
        "ind_1_3_den": g1.get("ind_1_3_den"), 
        "ind_1_3_nota_mediana": g1.get("ind_1_3_nota_mediana"),
        "ind_1_3_nota_desviacion": g1.get("ind_1_3_nota_desviacion"),

        "ind_1_4_participacion": g1.get("ind_1_4_participacion"),
        "ind_1_4_num": g1.get("ind_1_4_num"),
        "ind_1_4_den": g1.get("ind_1_4_den"),

        # Group 1 Distributions (Frequencies)
        "ind_1_5_rango_0_25": g1.get("ind_1_5_rango_0_25", 0),
        "ind_1_5_rango_25_50": g1.get("ind_1_5_rango_25_50", 0),
        "ind_1_5_rango_50_75": g1.get("ind_1_5_rango_50_75", 0),
        "ind_1_5_rango_75_100": g1.get("ind_1_5_rango_75_100", 0),

        "ind_1_6_rango_0_9": g1.get("ind_1_6_rango_0_9", 0),
        "ind_1_6_rango_10_15": g1.get("ind_1_6_rango_10_15", 0),
        "ind_1_6_rango_16_20": g1.get("ind_1_6_rango_16_20", 0),

        # --- GROUP 2 COMPONENTS ---
        "ind_2_1_metod_activa": g2.get("ind_2_1_metod_activa"),
        "ind_2_1_num": g2.get("ind_2_1_num"),
        "ind_2_1_den": g2.get("ind_2_1_den"),

        "ind_2_2_ratio_eval": g2.get("ind_2_2_ratio_eval"),
        "ind_2_2_num": g2.get("ind_2_2_num"),
        "ind_2_2_den": g2.get("ind_2_2_den"),

        # --- GROUP 3 COMPONENTS ---
        "ind_3_1_excelencia": g3.get("ind_3_1_excelencia"),
        "ind_3_1_num": g3.get("ind_3_1_num"),
        "ind_3_1_den": g3.get("ind_3_1_den"),

        "ind_3_2_feedback": g3.get("ind_3_2_feedback"),
        "ind_3_2_num": g3.get("ind_3_2_num"),
        "ind_3_2_den": g3.get("ind_3_2_den"),

        # --- AUDIT FIELDS ---
        "is_irregular": g1.get("is_irregular"),
        "max_grade_config": g1.get("max_grade_config"),
    }