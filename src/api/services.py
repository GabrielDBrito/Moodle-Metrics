import statistics
from api.client import call_moodle_api

def get_course_grade_stats(config, course_id):
    """
    Retrieves and normalizes grade statistics for a given course using bulk extraction.
    
    Includes logic for:
    1. Bulk data retrieval (userid=0 optimization).
    2. Heuristic detection of scale misconfiguration (100-scale vs 20-scale).
    3. Filtering of inactive students (grades < 1.0).
    4. Outlier detection for course averages.

    Returns:
        dict: Statistical indicators or None if the course is invalid/empty.
    """
    moodle_config = config['MOODLE']
    
    # 1. Bulk Extraction
    # We use userid=0 to fetch all students in a single API call.
    grades_data = call_moodle_api(
        moodle_config, 
        "gradereport_user_get_grade_items", 
        courseid=course_id, 
        userid=0 
    )
    
    if not grades_data or 'usergrades' not in grades_data:
        return None

    all_students = grades_data['usergrades']
    
    # Minimum sample size filter (exclude individual tutorials or empty courses)
    if len(all_students) < 4:
        return None

    raw_grades_cache = []
    
    # Constants for UNIMET Academic Scale
    TARGET_SCALE = 20.0
    PASSING_GRADE = 10.0 
    MIN_VALID_GRADE = 1.0 # Grades below this are considered dropouts/inactive

    # --- Phase 1: Raw Data Collection ---
    for student in all_students:
        for item in student.get('gradeitems', []):
            if item.get('itemtype') == 'course':
                raw = item.get('graderaw')
                gmax = item.get('grademax')
                
                if raw is not None and gmax is not None and float(gmax) > 0:
                    raw_grades_cache.append({
                        'val': float(raw),
                        'max': float(gmax)
                    })
                break
    
    if not raw_grades_cache:
        return None

    # --- Phase 2: Heuristic Scale Analysis ---
    # Detects if the professor configured the course total as 100 but uploaded grades in base 20.
    
    raw_values = [x['val'] for x in raw_grades_cache]
    max_values = [x['max'] for x in raw_grades_cache]
    
    promedio_crudo = statistics.mean(raw_values)
    max_configurado = statistics.mode(max_values) 
    max_nota_real = max(raw_values) 

    apply_scale_correction = False
    
    # Logic: If Max is > 25 (e.g., 100), but no student scored above 20, 
    # and the class average is plausible for base 20 (> 5.0), assume configuration error.
    if max_configurado > 25.0 and max_nota_real <= 20.0 and promedio_crudo > 5.0:
        apply_scale_correction = True

    # --- Phase 3: Normalization and Filtering ---
    final_grades = []
    
    for item in raw_grades_cache:
        val = item['val']
        gmax = item['max']
        
        normalized_grade = 0.0
        
        if apply_scale_correction:
            # Trust the raw value as the true grade
            normalized_grade = val
        else:
            # Standard normalization
            if gmax != TARGET_SCALE:
                normalized_grade = (val / gmax) * TARGET_SCALE
            else:
                normalized_grade = val
        
        # Inactivity Filter: Exclude grades near zero (dropouts)
        if normalized_grade < MIN_VALID_GRADE:
            continue
            
        final_grades.append(normalized_grade)

    # --- Phase 4: Final Validation and Statistics ---
    if not final_grades:
        return None

    average_grade = round(statistics.mean(final_grades), 2)
    
    # Quality Control: If course average is still mathematically improbable (< 5.0),
    # discard the course to avoid polluting the dataset with bad data.
    if average_grade < 5.0:
        return None

    stats = {
        "ind_1_3_nota_promedio": average_grade,
        "ind_1_3_nota_mediana": round(statistics.median(final_grades), 2),
        "ind_1_3_nota_desviacion": 0.0,
        "ind_1_2_aprobacion": 0.0,
        "total_procesados": len(final_grades)
    }

    if len(final_grades) > 1:
        stats["ind_1_3_nota_desviacion"] = round(statistics.stdev(final_grades), 2)
    
    approved_count = sum(1 for grade in final_grades if grade >= PASSING_GRADE)
    stats["ind_1_2_aprobacion"] = round((approved_count / len(final_grades)) * 100, 2)

    return stats