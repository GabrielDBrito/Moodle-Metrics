import statistics
from typing import Dict, List, Optional, Any
from utils.filters import CourseFilter

# --- BUSINESS LOGIC CONFIGURATION ---
TARGET_SCALE = 20.0
PASSING_GRADE = 9.5
DENSITY_ACTIVE = 0.40
DENSITY_COMPLETE = 0.70
MIN_PARTICIPATION_RATE = 0.05
SIGNIFICANT_WEIGHT_THRESHOLD = 0.05

def calculate_group1_metrics(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # ... (Validaciones iniciales igual) ...
    if not grades_data or not isinstance(grades_data, dict): return None
    user_grades = grades_data.get('usergrades')
    if not user_grades or not isinstance(user_grades, list): return None
    
    # Layer 2: Population Check
    total_enrolled = len(user_grades)
    if total_enrolled < CourseFilter.MIN_STUDENTS_REQUIRED: return None

    # ... (STEP 0: Normalization Analysis - IGUAL) ...
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

    # ... (STEP 1: Metadata - IGUAL) ...
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades if s.get('gradeitems'))
    if max_columns == 0: return None
    items_metadata = [None] * max_columns
    participation_counts = [0] * max_columns
    total_valid_students = 0
    manual_override_count = 0 

    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
        total_valid_students += 1
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if item.get('overridden', 0) > 0: manual_override_count += 1
                break
        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                items_metadata[idx] = {'type': item.get('itemtype'), 'module': item.get('itemmodule'), 'gmax': float(item.get('grademax', 0)), 'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else 0.0}
            if item.get('graderaw') is not None: participation_counts[idx] += 1

    # ... (STEP 2: Whitelisting - IGUAL) ...
    has_explicit_weights = any(m and m['type'] not in ('course', 'category') and m['wraw'] > 0.0001 for m in items_metadata)
    whitelisted_indices = []
    total_grademax_sum = 0.0
    max_grades_found = set()
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01: continue
        part_pct = participation_counts[idx] / total_valid_students if total_valid_students > 0 else 0
        if has_explicit_weights:
            if meta['wraw'] <= 0.0001: continue
        else:
            if part_pct < MIN_PARTICIPATION_RATE: continue
        whitelisted_indices.append(idx)
        total_grademax_sum += meta['gmax']
        max_grades_found.add(meta['gmax'])
    if not whitelisted_indices: return None

    # ... (STEP 3: Integrity/Structure - IGUAL) ...
    total_missing_weight = 0.0
    max_effective_weight = 0.0
    for idx in whitelisted_indices:
        meta = items_metadata[idx]
        weight = meta['wraw'] if has_explicit_weights else (meta['gmax'] / total_grademax_sum)
        if weight > max_effective_weight: max_effective_weight = weight
        if participation_counts[idx] == 0: total_missing_weight += weight
    has_hierarchy = CourseFilter.has_valid_hierarchy(len(whitelisted_indices), has_explicit_weights, max_grades_found, max_effective_weight)
    override_ratio = manual_override_count / total_valid_students if total_valid_students > 0 else 0
    if not CourseFilter.is_valid_assessment_structure(has_hierarchy, override_ratio): return None
    if not CourseFilter.is_integrity_valid(total_missing_weight): return None

    # ... (STEP 4: Denominators - IGUAL) ...
    max_tasks_by_passer = 0
    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        norm_final = (raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final
        if norm_final >= PASSING_GRADE:
            completed = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
            if completed > max_tasks_by_passer: max_tasks_by_passer = completed
    compliance_den = max(len(whitelisted_indices), max_tasks_by_passer)
    significant_indices = [idx for idx in whitelisted_indices if items_metadata[idx]['wraw'] >= SIGNIFICANT_WEIGHT_THRESHOLD or not has_explicit_weights]
    if not significant_indices: significant_indices = whitelisted_indices
    finalization_den = len(significant_indices)

    # --- STEP 5: Aggregation Loop (CON NUEVOS CONTADORES) ---
    total_checks = 0; passing_count = 0; active_count = 0; finisher_count = 0
    qualified_grades = []; processed_count = 0
    
    # NUEVOS CONTADORES PARA DISTRIBUCIÓN
    count_range_0_9 = 0
    count_range_10_15 = 0
    count_range_16_20 = 0

    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        
        student_completed_all = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
        student_completed_sig = sum(1 for idx in significant_indices if idx < len(items) and items[idx].get('graderaw') is not None)
        processed_count += 1
        
        norm_grade = min((raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final, TARGET_SCALE)
        
        total_checks += student_completed_all
        if norm_grade >= PASSING_GRADE: passing_count += 1
        
        # Clasificación en rangos (Ind 1.6)
        # Usamos 9.5 como corte para aprobar y 15.5 para excelencia media
        if norm_grade < 9.5:
            count_range_0_9 += 1
        elif norm_grade < 15.5:
            count_range_10_15 += 1
        else:
            count_range_16_20 += 1

        density_all = student_completed_all / compliance_den if compliance_den > 0 else 0
        density_sig = student_completed_sig / finalization_den if finalization_den > 0 else 0
        
        if density_all >= DENSITY_ACTIVE: active_count += 1
        if density_sig >= DENSITY_COMPLETE: finisher_count += 1
        qualified_grades.append(norm_grade)
        total_potential += compliance_den

    if not CourseFilter.is_valid_population(processed_count): return None

    # --- Final Compilation ---
    avg_val = statistics.mean(qualified_grades) if qualified_grades else 0.0
    compliance = (total_checks / total_potential * 100) if total_potential > 0 else 0.0
    if not CourseFilter.is_academically_mature(avg_val, compliance): return None

    return {
        "n_estudiantes_totales": total_enrolled,
        "ind_1_1_cumplimiento": round(compliance, 2),
        "ind_1_2_aprobacion": round((passing_count / total_enrolled) * 100, 2),
        "ind_1_3_nota_promedio": round(avg_val, 2),
        "ind_1_3_nota_mediana": round(statistics.median(qualified_grades), 2) if qualified_grades else 0.0,
        "ind_1_3_nota_desviacion": round(statistics.stdev(qualified_grades), 2) if len(qualified_grades) > 1 else 0.0,
        "ind_1_4_participacion": round((active_count / total_enrolled) * 100, 2), 
        "ind_1_5_finalizacion": round((finisher_count / total_enrolled) * 100, 2),
        
        # Components
        "ind_1_1_num": total_checks, "ind_1_1_den": total_potential,
        "ind_1_2_num": passing_count, "ind_1_2_den": total_enrolled,
        "ind_1_3_num": round(sum(qualified_grades), 2), "ind_1_3_den": len(qualified_grades),
        "ind_1_4_num": active_count, "ind_1_4_den": total_enrolled,
        "ind_1_5_num": finisher_count, "ind_1_5_den": total_enrolled,

        # grade range distribution (Ind 1.6)
        "ind_1_6_rango_0_9": count_range_0_9,
        "ind_1_6_rango_10_15": count_range_10_15,
        "ind_1_6_rango_16_20": count_range_16_20,
        
        "is_irregular": is_irregular,
        "max_grade_config": config_max_grade
    }

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