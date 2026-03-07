import statistics
from typing import Dict, List, Optional, Any
from utils.filters import CourseFilter

# --- FIXED BUSINESS LOGIC ---
TARGET_SCALE = 20.0
PASSING_GRADE = 9.5

def calculate_group1_metrics(grades_data: Dict[str, Any], params: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Analyzes course grade data showing the raw institutional reality.
    - Includes all students and all valid activities.
    - No pedagogical quality filters applied.
    """
    if not grades_data or 'usergrades' not in grades_data: return None
    user_grades = grades_data.get('usergrades')
    if not user_grades: return None
    
    # --- 1. POPULATION FILTER ---
    total_enrolled = len(user_grades)
    min_students_param = int(params.get('min_students', 5))
    
    if not CourseFilter.is_valid_population(total_enrolled, min_students_param):
        return None

    # --- 2. NORMALIZATION ANALYSIS ---
    config_max_grade = 0.0
    global_max_observed = 0.0 
    for student in user_grades:
        if not student.get('gradeitems'): continue
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if config_max_grade == 0.0: config_max_grade = float(item.get('grademax', 0))
                raw_score = item.get('graderaw')
                if raw_score is not None:
                    try:
                        val = float(raw_score)
                        if val > global_max_observed: global_max_observed = val
                    except: pass
                break

    normalize_divisor = config_max_grade if config_max_grade > 0 else 1.0
    should_normalize = (config_max_grade > 25.0) or (abs(config_max_grade - 20.0) > 0.1)
    
    if should_normalize and config_max_grade > 40.0 and global_max_observed <= 22.0:
        should_normalize = False
        normalize_divisor = 1.0
    
    is_irregular = (config_max_grade != 20.0 and config_max_grade > 0)

    # --- 3. WHITELISTING ---
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades if s.get('gradeitems'))
    items_metadata = [None] * max_columns
    
    if max_columns > 0:
        for student in user_grades:
            if not student.get('gradeitems'): continue
            for idx, item in enumerate(student['gradeitems']):
                if items_metadata[idx] is None:
                    items_metadata[idx] = {
                        'type': item.get('itemtype'),
                        'module': item.get('itemmodule'),
                        'gmax': float(item.get('grademax', 0)),
                        'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else 0.0
                    }

    has_explicit_weights = any(m and m['type'] not in ('course', 'category') and m['wraw'] > 0.0001 for m in items_metadata)
    
    whitelisted_indices = []
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01: continue
        if has_explicit_weights and meta['wraw'] <= 0.0001: continue
        whitelisted_indices.append(idx)
    
    # --- 4. CALCULATION ---
    compliance_den = len(whitelisted_indices) if whitelisted_indices else 0
    total_checks = 0; passing_count = 0; active_count = 0; qualified_grades = []
    c0_9 = 0; c10_15 = 0; c16_20 = 0
    cp0_25 = 0; cp25_50 = 0; cp50_75 = 0; cp75_100 = 0

    active_density_threshold = float(params.get('active_density', 0.40))

    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        norm_grade = min((raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final, TARGET_SCALE)
        
        student_completed = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
        
        total_checks += student_completed
        qualified_grades.append(norm_grade)
        
        if norm_grade >= PASSING_GRADE: passing_count += 1
        
        density = student_completed / compliance_den if compliance_den > 0 else 0
        if density >= active_density_threshold: active_count += 1

        if norm_grade < 9.5: c0_9 += 1
        elif norm_grade < 15.5: c10_15 += 1
        else: c16_20 += 1

        if density < 0.25: cp0_25 += 1
        elif density < 0.50: cp25_50 += 1
        elif density < 0.75: cp50_75 += 1
        else: cp75_100 += 1

    processed_count = total_enrolled
    avg_val = statistics.mean(qualified_grades) if qualified_grades else 0.0
    compliance_final = (total_checks / (compliance_den * processed_count) * 100) if (compliance_den * processed_count) > 0 else 0.0

    return {
        "n_estudiantes_totales": total_enrolled,
        "ind_1_1_cumplimiento": round(compliance_final, 2),
        "ind_1_2_aprobacion": round((passing_count / total_enrolled) * 100, 2),
        "ind_1_3_nota_promedio": round(avg_val, 2),
        "ind_1_3_nota_mediana": round(statistics.median(qualified_grades), 2) if qualified_grades else 0.0,
        "ind_1_3_nota_desviacion": round(statistics.stdev(qualified_grades), 2) if len(qualified_grades) > 1 else 0.0,
        "ind_1_4_participacion": round((active_count / total_enrolled) * 100, 2), 
        "ind_1_1_num": total_checks, 
        "ind_1_1_den": compliance_den * total_enrolled,
        "ind_1_2_num": passing_count, 
        "ind_1_2_den": total_enrolled,
        "ind_1_3_num": round(sum(qualified_grades), 2), 
        "ind_1_3_den": len(qualified_grades),
        "ind_1_4_num": active_count, 
        "ind_1_4_den": total_enrolled,
        "ind_1_5_rango_0_25": cp0_25, "ind_1_5_rango_25_50": cp25_50, "ind_1_5_rango_50_75": cp50_75, "ind_1_5_rango_75_100": cp75_100,
        "ind_1_6_rango_0_9": c0_9, "ind_1_6_rango_10_15": c10_15, "ind_1_6_rango_16_20": c16_20,
        "is_irregular": is_irregular, 
        "max_grade_config": config_max_grade
    }

# --- ESTA ES LA FUNCIÓN QUE FALTABA Y CAUSABA EL ERROR ---
def extract_valid_evaluable_module_types(grades_data: Dict[str, Any]) -> set:
    """
    Returns the set of module types (e.g., 'assign', 'quiz') that are 
    valid evaluable items in the course. Used by Group 2.
    """
    if not grades_data: return set()
    user_grades = grades_data.get('usergrades')
    if not user_grades: return set()
    
    valid_modules = set()
    # Check structure from the first students to identify module types
    for student in user_grades[:5]:
        if not student.get('gradeitems'): continue
        for item in student['gradeitems']:
            # We consider it valid if it's a module and has a point value
            if item.get('itemtype') == 'mod' and float(item.get('grademax', 0)) > 0.01:
                valid_modules.add(item.get('itemmodule'))
        break
    return valid_modules