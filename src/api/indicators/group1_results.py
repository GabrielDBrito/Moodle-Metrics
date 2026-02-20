import statistics
from typing import Dict, List, Optional, Any
from utils.filters import CourseFilter

# --- BUSINESS LOGIC CONFIGURATION ---
TARGET_SCALE = 20.0
PASSING_GRADE = 9.5
DENSITY_ACTIVE = 0.40
DENSITY_COMPLETE = 0.80
MIN_PARTICIPATION_RATE = 0.05

def calculate_group1_metrics(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyzes course grade data with advanced quality and integrity filtering.
    
    This function handles:
    1. Normalization of inconsistent Moodle scales.
    2. Assessment hierarchy check (rejects flat/logbook structures).
    3. Evaluation integrity check (rejects courses with missing major grades).
    4. Maturity filtering (rejects early-stage courses).
    """
    if not grades_data or not isinstance(grades_data, dict):
        return None
    
    user_grades = grades_data.get('usergrades')
    if not user_grades or not isinstance(user_grades, list):
        return None
        
    # Layer 2: Population Check
    if len(user_grades) < CourseFilter.MIN_STUDENTS_REQUIRED:
        return None

    # --- STEP 0: Normalization & Scale Analysis ---
    config_max_grade = 0.0
    global_max_observed = 0.0 

    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if config_max_grade == 0.0:
                    config_max_grade = float(item.get('grademax', 0))
                
                raw_score = item.get('graderaw')
                if raw_score is not None:
                    try:
                        val = float(raw_score)
                        if val > global_max_observed: global_max_observed = val
                    except: pass
                break

    normalize_divisor = config_max_grade if config_max_grade > 0 else 1.0
    should_normalize = (config_max_grade > 25.0) or (abs(config_max_grade - 20.0) > 0.1)

    # Scale Protection: If Max is huge but grades are already in 0-20 scale
    if should_normalize and config_max_grade > 40.0 and global_max_observed <= 22.0:
        should_normalize = False
        normalize_divisor = 1.0

    # --- STEP 1: Metadata, Participation & Manual Override Detection ---
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades)
    if max_columns == 0: return None

    participation_counts = [0] * max_columns
    items_metadata = [None] * max_columns
    total_valid_students = 0
    manual_override_count = 0 

    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
        total_valid_students += 1
        
        # Detect Manual Override on Course Total
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if item.get('overridden', 0) > 0:
                    manual_override_count += 1
                break

        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                items_metadata[idx] = {
                    'type': item.get('itemtype'),
                    'gmax': float(item.get('grademax', 0)),
                    'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else 0.0
                }
            if item.get('graderaw') is not None:
                participation_counts[idx] += 1

    # --- STEP 2: Strict Whitelisting ---
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

    # --- STEP 3: Assessment Design & Integrity Check ---
    total_missing_weight = 0.0
    max_effective_weight = 0.0
    
    for idx in whitelisted_indices:
        meta = items_metadata[idx]
        # Calculate weight: use explicit if available, otherwise relative points
        weight = meta['wraw'] if has_explicit_weights else (meta['gmax'] / total_grademax_sum)
        
        if weight > max_effective_weight:
            max_effective_weight = weight
            
        # Integrity: check for completely empty columns (0 participation)
        if participation_counts[idx] == 0:
            total_missing_weight += weight

    # 1. Structure Check (Hierarchy)
    has_hierarchy = CourseFilter.has_valid_hierarchy(
        num_items=len(whitelisted_indices),
        has_explicit_weights=has_explicit_weights,
        max_grades_set=max_grades_found,
        max_effective_weight=max_effective_weight
    )

    # 2. Rescue Clause: Check Manual Override Ratio
    override_ratio = manual_override_count / total_valid_students if total_valid_students > 0 else 0

    # 3. Final Structural Decision
    if not CourseFilter.is_valid_assessment_structure(has_hierarchy, override_ratio):
        return None

    # 4. Final Integrity Decision (Case 2515)
    if not CourseFilter.is_integrity_valid(total_missing_weight):
        return None

    # --- STEP 4: Denominator Logic & KPI Calculation ---
    max_tasks_by_passer = 0
    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        norm_final = (raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final
        if norm_final >= PASSING_GRADE:
            completed = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
            if completed > max_tasks_by_passer: max_tasks_by_passer = completed

    final_denominator = max(len(whitelisted_indices), max_tasks_by_passer)

    total_checks = 0
    total_potential = 0
    passing_count = 0
    active_count = 0
    finisher_count = 0
    qualified_grades = []
    processed_count = 0

    for student in user_grades:
        items = student.get('gradeitems', [])
        raw_final = next((float(i['graderaw']) for i in items if i.get('itemtype') == 'course' and i.get('graderaw') is not None), 0.0)
        student_completed = sum(1 for idx in whitelisted_indices if idx < len(items) and items[idx].get('graderaw') is not None)
        
        if raw_final < 0.1 and student_completed == 0: continue
        processed_count += 1
        
        norm_grade = min((raw_final / normalize_divisor) * TARGET_SCALE if should_normalize else raw_final, TARGET_SCALE)
        if norm_grade >= PASSING_GRADE: passing_count += 1

        density = student_completed / final_denominator if final_denominator > 0 else 0
        if density >= DENSITY_ACTIVE or norm_grade >= PASSING_GRADE: active_count += 1
        if density >= DENSITY_COMPLETE: finisher_count += 1
        if norm_grade >= 0.5: qualified_grades.append(norm_grade)
        
        total_checks += student_completed
        total_potential += final_denominator

    if not CourseFilter.is_valid_population(processed_count):
        return None

    # --- STEP 5: Maturity Filter ---
    avg_val = statistics.mean(qualified_grades) if qualified_grades else 0.0
    compliance = (total_checks / total_potential * 100) if total_potential > 0 else 0.0

    if not CourseFilter.is_academically_mature(avg_val, compliance):
        return None

    return {
        "n_estudiantes_procesados": processed_count,
        "n_estudiantes_totales": total_valid_students,
        "ind_1_1_cumplimiento": round(compliance, 2),
        "ind_1_2_aprobacion": round((passing_count / processed_count) * 100, 2),
        "ind_1_3_nota_promedio": round(avg_val, 2),
        "ind_1_3_nota_mediana": round(statistics.median(qualified_grades), 2) if qualified_grades else 0.0,
        "ind_1_3_nota_desviacion": round(statistics.stdev(qualified_grades), 2) if len(qualified_grades) > 1 else 0.0,
        "ind_1_4_participacion": round((active_count / total_valid_students) * 100, 2), 
        "ind_1_5_finalizacion": round((finisher_count / processed_count) * 100, 2),
        "ind_1_1_num": total_checks, "ind_1_1_den": total_potential,
        "ind_1_2_num": passing_count, "ind_1_2_den": processed_count,
        "ind_1_3_num": round(sum(qualified_grades), 2), "ind_1_3_den": len(qualified_grades),
        "ind_1_4_num": active_count, "ind_1_4_den": total_valid_students,
        "ind_1_5_num": finisher_count, "ind_1_5_den": processed_count
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