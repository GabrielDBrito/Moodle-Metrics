import statistics
from typing import Dict, List, Optional, Any
from utils.filters import CourseFilter

# --- BUSINESS LOGIC CONFIGURATION ---
TARGET_SCALE = 20.0
PASSING_GRADE = 9.5
DENSITY_ACTIVE = 0.40
MIN_PARTICIPATION_RATE = 0.05

def calculate_group1_metrics(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not grades_data or not isinstance(grades_data, dict): return None
    user_grades = grades_data.get('usergrades')
    if not user_grades or not isinstance(user_grades, list): return None
    if len(user_grades) < CourseFilter.MIN_STUDENTS_REQUIRED: return None

    # --- STEP 0: Normalization Analysis ---
    config_max_grade = 0.0
    global_max_observed = 0.0 
    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
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

    # --- STEP 1: Metadata & Participation ---
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades if s.get('gradeitems'))
    if max_columns == 0: return None

    items_metadata = [None] * max_columns
    participation_counts = [0] * max_columns # <--- LÍNEA CORREGIDA
    total_valid_students = 0 
    manual_override_count = 0 

    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
        total_valid_students += 1
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course' and item.get('overridden', 0) > 0:
                manual_override_count += 1
                break
        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                items_metadata[idx] = {'type': item.get('itemtype'), 'module': item.get('itemmodule'), 'gmax': float(item.get('grademax', 0)), 'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else 0.0}
            if item.get('graderaw') is not None:
                participation_counts[idx] += 1

    # --- STEP 2: Whitelisting ---
    has_explicit_weights = any(m and m['type'] not in ('course', 'category') and m['wraw'] > 0.0001 for m in items_metadata)
    whitelisted_indices = []
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01: continue
        if has_explicit_weights and meta['wraw'] <= 0.0001: continue
        whitelisted_indices.append(idx)
    
    if not whitelisted_indices: return None

    # --- STEP 3: Denominators Logic ---
    max_tasks_by_passer = 0
    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        norm_final = (raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final
        if norm_final >= PASSING_GRADE:
            completed = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
            if completed > max_tasks_by_passer: max_tasks_by_passer = completed

    compliance_den = max(len(whitelisted_indices), max_tasks_by_passer)

    # --- STEP 4: Aggregation Loop ---
    total_checks = 0; passing_count = 0; active_count = 0; qualified_grades = []
    
    count_grade_0_9 = 0; count_grade_10_15 = 0; count_grade_16_20 = 0
    count_compl_0_25 = 0; count_compl_25_50 = 0; count_compl_50_75 = 0; count_compl_75_100 = 0

    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        student_completed_all = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
        
        norm_grade = min((raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final, TARGET_SCALE)
        density_all = student_completed_all / compliance_den if compliance_den > 0 else 0
        
        total_checks += student_completed_all
        if norm_grade >= PASSING_GRADE: passing_count += 1
        if density_all >= DENSITY_ACTIVE: active_count += 1
        qualified_grades.append(norm_grade)

        if norm_grade < 9.5: count_grade_0_9 += 1
        elif norm_grade < 15.5: count_grade_10_15 += 1
        else: count_grade_16_20 += 1

        if density_all < 0.25: count_compl_0_25 += 1
        elif density_all < 0.50: count_compl_25_50 += 1
        elif density_all < 0.75: count_compl_50_75 += 1
        else: count_compl_75_100 += 1

    processed_count = total_valid_students
    avg_val = statistics.mean(qualified_grades) if qualified_grades else 0.0
    compliance_final = (total_checks / (compliance_den * processed_count) * 100) if (compliance_den * processed_count) > 0 else 0.0

    return {
        "n_estudiantes_totales": processed_count,
        "ind_1_1_cumplimiento": round(compliance_final, 2),
        "ind_1_2_aprobacion": round((passing_count / processed_count) * 100, 2),
        "ind_1_3_nota_promedio": round(avg_val, 2),
        "ind_1_3_nota_mediana": round(statistics.median(qualified_grades), 2) if qualified_grades else 0.0,
        "ind_1_3_nota_desviacion": round(statistics.stdev(qualified_grades), 2) if len(qualified_grades) > 1 else 0.0,
        "ind_1_4_participacion": round((active_count / total_valid_students) * 100, 2) if total_valid_students > 0 else 0, 
        "ind_1_1_num": total_checks, "ind_1_1_den": compliance_den * processed_count,
        "ind_1_2_num": passing_count, "ind_1_2_den": processed_count,
        "ind_1_3_num": round(sum(qualified_grades), 2), "ind_1_3_den": len(qualified_grades),
        "ind_1_4_num": active_count, "ind_1_4_den": total_valid_students,
        "ind_1_5_rango_0_25": count_compl_0_25, "ind_1_5_rango_25_50": count_compl_25_50, "ind_1_5_rango_50_75": count_compl_50_75, "ind_1_5_rango_75_100": count_compl_75_100,
        "ind_1_6_rango_0_9": count_grade_0_9, "ind_1_6_rango_10_15": count_grade_10_15, "ind_1_6_rango_16_20": count_grade_16_20,
        "is_irregular": is_irregular, "max_grade_config": config_max_grade
    }

# (Función extract_valid_evaluable_module_types se mantiene igual)
def extract_valid_evaluable_module_types(grades_data: Dict[str, Any]) -> set:
    if not grades_data: return set()
    user_grades = grades_data.get('usergrades')
    if not user_grades: return set()
    valid_modules = set()
    for student in user_grades[:5]:
        if not student.get('gradeitems'): continue
        for item in student['gradeitems']:
            if item.get('itemtype') == 'mod' and float(item.get('grademax', 0)) > 0.01:
                valid_modules.add(item.get('itemmodule'))
        break
    return valid_modules