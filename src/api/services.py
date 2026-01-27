import re
from typing import Dict, Any, Optional, Tuple
from .client import call_moodle_api
from .indicators.group1_results import calculate_group1_metrics

def _sanitize_subject_code(shortname: Optional[str]) -> str:
    """
    Extracts the base subject code from the course shortname string.
    
    Splits the string by underscore, hyphen, or whitespace and returns the first segment.
    Returns the original string if the result is too short or invalid.
    
    Args:
        shortname: The raw course shortname from Moodle.
        
    Returns:
        Cleaned subject code (e.g., 'MATH101' from 'MATH101_Fall2025').
    """
    if not shortname:
        return "NO_CODE"
    
    # Split by common delimiters and take the first part
    cleaned_code = re.split(r'[-_ ]', shortname)[0]
    
    # Basic validation: avoid returning single characters or empty strings
    if len(cleaned_code) < 2:
        return shortname.strip()
        
    return cleaned_code.strip()

def _identify_instructor(course_id: int, config: Dict[str, Any]) -> Tuple[int, str]:
    """
    Identifies the primary instructor for a course based on role hierarchy.
    
    Priority Order:
    1. Editing Teacher (Role ID: 3)
    2. Non-Editing Teacher (Role ID: 4)
    3. Manager (Role ID: 1)
    
    Args:
        course_id: The Moodle course ID.
        config: Application configuration containing API credentials.
        
    Returns:
        A tuple containing (Teacher ID, Teacher Fullname). 
        Returns (0, "Unassigned") if no instructor is found.
    """
    try:
        enrolled_users = call_moodle_api(
            config['MOODLE'], 
            "core_enrol_get_enrolled_users", 
            courseid=course_id
        )
    except Exception:
        # Fail gracefully if the API call fails
        return 0, "Unassigned"
    
    if not enrolled_users:
        return 0, "Unassigned"

    # Strategy: Iterate through priority tiers.
    # We loop multiple times to ensure the highest priority role is selected 
    # regardless of the user list order.

    # Priority 1: Editing Teacher
    for user in enrolled_users:
        for role in user.get('roles', []):
            if role.get('roleid') == 3:
                return user.get('id', 0), user.get('fullname', 'Unknown')

    # Priority 2: Non-Editing Teacher
    for user in enrolled_users:
        for role in user.get('roles', []):
            if role.get('roleid') == 4:
                return user.get('id', 0), user.get('fullname', 'Unknown')
                
    # Priority 3: Manager
    for user in enrolled_users:
        for role in user.get('roles', []):
            if role.get('roleid') == 1:
                return user.get('id', 0), user.get('fullname', 'Unknown')

    return 0, "Unassigned"

def process_course_analytics(config: Dict[str, Any], course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the extraction and calculation of KPIs for a single course.
    
    1. Fetches raw grade data.
    2. Calculates academic metrics (Completion, Approval, Average).
    3. Enriches data with metadata (Instructor, Subject Code).
    
    Args:
        config: Application configuration.
        course_data: Dictionary containing basic course info (id, shortname, fullname).
        
    Returns:
        A flat dictionary ready for CSV serialization, or None if the course 
        does not meet the minimum requirements for analysis.
    """
    course_id = course_data.get('id')
    raw_shortname = course_data.get('shortname', '')
    fullname = course_data.get('fullname', '')
    category_id = course_data.get('categoryid', 0)
    
    # 1. Fetch Raw Grade Data
    grades_payload = call_moodle_api(
        config['MOODLE'], 
        "gradereport_user_get_grade_items", 
        courseid=course_id, 
        userid=0
    )
    
    # 2. Calculate Indicators
    # Returns None if the course is empty or too small
    metrics = calculate_group1_metrics(grades_payload)
    
    if not metrics:
        return None 

    # 3. Data Enrichment
    instructor_id, instructor_name = _identify_instructor(course_id, config)
    clean_subject_id = _sanitize_subject_code(raw_shortname)

    # 4. Construct Output Record
    # Mapping internal metric names to CSV column headers
    return {
        'id_curso': course_id,
        'id_asignatura': clean_subject_id,
        'nombre_curso': fullname,
        'id_profesor': instructor_id,
        'nombre_profesor': instructor_name,
        'categoria_id': category_id,
        
        # Key Performance Indicators
        'n_estudiantes_procesados': metrics['n_estudiantes_procesados'],
        'ind_1_1_cumplimiento': metrics['ind_1_1_cumplimiento'],
        'ind_1_2_aprobacion': metrics['ind_1_2_aprobacion'],
        'ind_1_3_promedio': metrics['ind_1_3_promedio'],
        'ind_1_3_mediana': metrics['ind_1_3_mediana'],
        'ind_1_3_desviacion': metrics['ind_1_3_desviacion'],
        'ind_1_4_activos': metrics['ind_1_4_activos'],
        'ind_1_5_finalizacion': metrics['ind_1_5_finalizacion']
    }