from typing import Dict, Any, Optional, Tuple
import re
from .client import call_moodle_api
from .indicators.group1_results import calculate_group1_metrics
from .indicators.group2_design import calculate_design_metrics
from .indicators.group3_behavior import calculate_group3_metrics_from_grades


def _sanitize_subject_code(shortname: Optional[str]) -> str:
    if not shortname:
        return "NO_CODE"
    cleaned_code = re.split(r'[-_ ]', shortname)[0]
    if len(cleaned_code) < 2:
        return shortname.strip()
    return cleaned_code.strip()


def _identify_instructor(course_id: int, config: Dict[str, Any]) -> Tuple[int, str]:
    try:
        enrolled_users = call_moodle_api(
            config['MOODLE'],
            "core_enrol_get_enrolled_users",
            courseid=course_id
        )
    except Exception:
        return 0, "Unassigned"

    if not enrolled_users:
        return 0, "Unassigned"

    for role_id in [3, 4, 1]:  # profesor, tutor, admin (ajusta roles si quieres)
        for user in enrolled_users:
            for role in user.get('roles', []):
                if role.get('roleid') == role_id:
                    return user.get('id', 0), user.get('fullname', 'Unknown')

    return 0, "Unassigned"


def process_course_analytics(
    config: Dict[str, Any],
    course_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:

    course_id = course_data.get('id')
    if not course_id:
        return None

    raw_shortname = course_data.get('shortname', '')
    fullname = course_data.get('fullname', '')
    category_id = course_data.get('categoryid', 0)

    # 1. Grupo 1 – Calificaciones
    grades_payload = call_moodle_api(
        config['MOODLE'],
        "gradereport_user_get_grade_items",
        courseid=course_id,
        userid=0
    )
    if not grades_payload:
        return None

    metrics_g1 = calculate_group1_metrics(grades_payload)
    if not metrics_g1:
        return None

    # 2. Grupo 2 – Diseño instruccional
    course_contents = call_moodle_api(
        config['MOODLE'],
        "core_course_get_contents",
        courseid=course_id
    )

    design_metrics = calculate_design_metrics(
        course_contents=course_contents,
        grades_data=grades_payload
    ) or {}

    # 3. Grupo 3 – Comportamiento (calculado desde calificaciones)
    behavior_metrics = calculate_group3_metrics_from_grades(grades_payload) or {}

    # 4. Metadata del curso
    instructor_id, instructor_name = _identify_instructor(course_id, config)
    clean_subject_id = _sanitize_subject_code(raw_shortname)

    # 5. Resultado final
    return {
        'id_curso': course_id,
        'id_asignatura': clean_subject_id,
        'nombre_curso': fullname,
        'id_profesor': instructor_id,
        'nombre_profesor': instructor_name,
        'categoria_id': category_id,

        # Grupo 1
        'n_estudiantes_procesados': metrics_g1.get('n_estudiantes_procesados'),
        'ind_1_1_cumplimiento': metrics_g1.get('ind_1_1_cumplimiento'),
        'ind_1_2_aprobacion': metrics_g1.get('ind_1_2_aprobacion'),
        'ind_1_3_promedio': metrics_g1.get('ind_1_3_promedio'),
        'ind_1_3_mediana': metrics_g1.get('ind_1_3_mediana'),
        'ind_1_3_desviacion': metrics_g1.get('ind_1_3_desviacion'),
        'ind_1_4_activos': metrics_g1.get('ind_1_4_activos'),
        'ind_1_5_finalizacion': metrics_g1.get('ind_1_5_finalizacion'),

        # Grupo 2
        'ind_2_1_metodologia_activa_ratio': design_metrics.get('ind_2_1_metodologia_activa_ratio'),
        'ind_2_1_metodologia_activa_pct': design_metrics.get('ind_2_1_metodologia_activa_pct'),
        'ind_2_2_eval_noeval_ratio': design_metrics.get('ind_2_2_eval_noeval_ratio'),
        'ind_2_2_balance_eval_pct': design_metrics.get('ind_2_2_balance_eval_pct'),

        # Grupo 3 - desde calificaciones
        'ind_3_1_procrastinacion_pct': behavior_metrics.get('ind_3_1_procrastinacion_pct'),
        'ind_3_2_feedback_ratio': behavior_metrics.get('ind_3_2_feedback_ratio'),
    }
