import statistics
from typing import Dict, List, Optional, Any

# --- BUSINESS LOGIC CONFIGURATION ---
TARGET_SCALE = 20.0
MIN_VALID_GRADE = 1.0
PASSING_GRADE = 9.5

# KPI Thresholds for student status
DENSITY_ACTIVE = 0.40
DENSITY_COMPLETE = 0.80

# Extraction filters
MIN_PARTICIPATION_RATE = 0.05
MIN_STUDENTS_REQUIRED = 5

def calculate_group1_metrics(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyzes course grade data to calculate academic performance and process KPIs.
    
    Returns a dictionary containing both per-course percentages AND 
    raw numerator/denominator components for accurate aggregation in BI tools.
    """
    if not grades_data or not isinstance(grades_data, dict):
        return None
    
    user_grades = grades_data.get('usergrades')
    if not user_grades or not isinstance(user_grades, list) or len(user_grades) < MIN_STUDENTS_REQUIRED:
        return None

    # ---------------------------------------------------------
    # STEP 0: Scale Detection and Normalization Strategy
    # ---------------------------------------------------------
    global_max_observed = 0.0
    config_max_grade = 0.0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue
        
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if config_max_grade == 0.0:
                    config_max_grade = float(item.get('grademax', 0))
                
                raw_score = item.get('graderaw')
                if raw_score is not None:
                    try:
                        val = float(raw_score)
                        if val > global_max_observed:
                            global_max_observed = val
                    except (ValueError, TypeError):
                        pass
                break

    normalize_divisor = 1.0
    should_normalize = False

    # Handling non-standard scales (e.g., Base 100 or Base 1/5/10)
    if config_max_grade > 25.0:
        if global_max_observed > 22.0:
            should_normalize = True
            normalize_divisor = config_max_grade
    elif config_max_grade > 0.001 and abs(config_max_grade - 20.0) > 0.1:
        should_normalize = True
        normalize_divisor = config_max_grade

    # ---------------------------------------------------------
    # STEP 1: Evaluable Items Whitelisting (The 3-Layer Filter)
    # ---------------------------------------------------------
    max_columns = 0
    for student in user_grades:
        if student.get('gradeitems'):
            max_columns = max(max_columns, len(student['gradeitems']))

    if max_columns == 0:
        return None

    participation_counts = [0] * max_columns
    items_metadata = [None] * max_columns
    total_valid_students = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue
        total_valid_students += 1
        
        for idx, item in enumerate(student['gradeitems']):
            try:
                if items_metadata[idx] is None:
                    items_metadata[idx] = {
                        'type': item.get('itemtype'),
                        'gmax': float(item.get('grademax', 0)),
                        'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else None,
                        'wfmt': item.get('weightformatted', '')
                    }
                if item.get('graderaw') is not None:
                    participation_counts[idx] += 1
            except (ValueError, TypeError, IndexError):
                continue

    # Layer 1: Detect if any item has an explicit positive weight
    has_explicit_weights = False
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category'):
            continue
        if (meta['wraw'] is not None and meta['wraw'] > 0.0001) or (meta['wfmt'] and '0.00' not in meta['wfmt']):
            has_explicit_weights = True
            break

    whitelisted_indices = []
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01:
            continue

        participation_pct = participation_counts[idx] / total_valid_students if total_valid_students > 0 else 0

        # Refined Layer 1 & 2: Aggressive filtering of null/zero weights
        if has_explicit_weights:
            is_invalid_weight = (meta['wraw'] is None) or (meta['wraw'] <= 0.0001) or ('0.00' in meta['wfmt'])
            if is_invalid_weight:
                continue
        else:
            if participation_pct < MIN_PARTICIPATION_RATE:
                continue
        
        whitelisted_indices.append(idx)

    # Detect Digital Deserts
    is_digital_desert = (len(whitelisted_indices) == 0)

    # ---------------------------------------------------------
    # STEP 1.5: Success-Based Denominator Logic
    # ---------------------------------------------------------
    final_denominator = 1.0
    if not is_digital_desert:
        max_tasks_by_passing_student = 0
        passers_found = False

        for student in user_grades:
            if not student or not student.get('gradeitems'): continue

            completed_tasks = 0
            for idx in whitelisted_indices:
                try:
                    if student['gradeitems'][idx].get('graderaw') is not None:
                        completed_tasks += 1
                except (IndexError, AttributeError): pass

            student_final_raw = 0.0
            for item in student.get('gradeitems', []):
                if item.get('itemtype') == 'course' and item.get('graderaw') is not None:
                    student_final_raw = float(item['graderaw'])
                    break
            
            norm_final = (student_final_raw / normalize_divisor) * TARGET_SCALE if should_normalize else student_final_raw
            
            if norm_final >= PASSING_GRADE:
                passers_found = True
                if completed_tasks > max_tasks_by_passing_student:
                    max_tasks_by_passing_student = completed_tasks

        final_denominator = max_tasks_by_passing_student if (passers_found and max_tasks_by_passing_student > 0) else max(len(whitelisted_indices), 1)

    # ---------------------------------------------------------
    # STEP 2: Aggregation of Student KPIs
    # ---------------------------------------------------------
    # Counters for Numerators
    total_checks_count = 0      # Ind 1.1 Num
    total_potential_capacity = 0 # Ind 1.1 Den
    
    passing_students_count = 0  # Ind 1.2 Num
    active_students_count = 0   # Ind 1.4 Num
    finisher_students_count = 0 # Ind 1.5 Num
    
    # Denominators
    # processed_count -> Used for Ind 1.2 and Ind 1.5 (Students who participated)
    # total_valid_students -> Used for Ind 1.4 (Total enrollment)
    
    grades_pool = []
    qualified_grades_for_avg = []
    processed_count = 0

    for student in user_grades:
        if not student: continue
        
        items = student.get('gradeitems')
        if not items: continue

        # A. Final Grade Extraction
        raw_final = 0.0
        has_final = False
        for item in items:
            if item.get('itemtype') == 'course' and item.get('graderaw') is not None:
                raw_final = float(item['graderaw'])
                has_final = True
                break

        # B. Task Counting
        student_completed_count = 0
        if not is_digital_desert:
            for idx in whitelisted_indices:
                try:
                    if idx < len(items) and items[idx].get('graderaw') is not None:
                        student_completed_count += 1
                except (IndexError, AttributeError): continue
            total_checks_count += student_completed_count

        # C. Eligibility Check (Filter for "Processed Students")
        is_participant = (has_final and raw_final >= 0.1) or (student_completed_count > 0)
        if not is_participant: continue

        processed_count += 1
        
        # D. KPI Calculation
        norm_grade = (raw_final / normalize_divisor) * TARGET_SCALE if (has_final and should_normalize) else raw_final
        norm_grade = min(norm_grade, TARGET_SCALE)
        
        grades_pool.append(norm_grade)
        if norm_grade >= PASSING_GRADE:
            passing_students_count += 1

        is_active = False
        is_finisher = False

        if is_digital_desert:
            if norm_grade >= 0.1: is_active = True
        else:
            density = student_completed_count / final_denominator
            if density >= DENSITY_ACTIVE or norm_grade >= PASSING_GRADE:
                is_active = True
            if density >= DENSITY_COMPLETE:
                is_finisher = True
            
            total_potential_capacity += final_denominator

        if is_active:
            active_students_count += 1
            if norm_grade >= 0.5:
                qualified_grades_for_avg.append(norm_grade)
        
        if is_finisher:
            finisher_students_count += 1

    if processed_count < MIN_STUDENTS_REQUIRED:
        return None

    # ---------------------------------------------------------
    # STEP 3: Final KPI Compilation
    # ---------------------------------------------------------
    # Statistics for local display
    avg_val = statistics.mean(qualified_grades_for_avg) if qualified_grades_for_avg else 0.0
    med_val = statistics.median(qualified_grades_for_avg) if qualified_grades_for_avg else 0.0
    dev_val = statistics.stdev(qualified_grades_for_avg) if len(qualified_grades_for_avg) > 1 else 0.0

    # Local Percentages (Course Level)
    approval_rate = (passing_students_count / processed_count) * 100
    activity_rate = (active_students_count / total_valid_students) * 100 if total_valid_students > 0 else 0.0

    compliance = None
    completion = None
    if not is_digital_desert:
        compliance = (total_checks_count / total_potential_capacity * 100) if total_potential_capacity > 0 else 0.0
        completion = (finisher_students_count / processed_count) * 100
        compliance = min(round(compliance, 2), 100.0)
        completion = round(completion, 2)

    # Aggregation Components for Ind 1.3 (Grade Average)
    # To get Global Average = Sum(All Grades) / Count(All Graded Students)
    grade_sum = sum(qualified_grades_for_avg)
    grade_count = len(qualified_grades_for_avg)

    return {
        # --- Metadata ---
        "n_estudiantes_procesados": processed_count,
        "n_estudiantes_totales": total_valid_students,

        # --- Course Level Indicators (Percentages/Stats) ---
        "ind_1_1_cumplimiento": compliance,
        "ind_1_2_aprobacion": round(approval_rate, 2),
        "ind_1_3_nota_promedio": round(avg_val, 2),
        "ind_1_3_nota_mediana": round(med_val, 2),
        "ind_1_3_nota_desviacion": round(dev_val, 2),
        "ind_1_4_participacion": round(activity_rate, 2), 
        "ind_1_5_finalizacion": completion,

        # --- Components for Global Aggregation (Numerators & Denominators) ---
        # Ind 1.1: Compliance = Checks / Potential Capacity
        "ind_1_1_num": total_checks_count,
        "ind_1_1_den": total_potential_capacity if not is_digital_desert else 0,

        # Ind 1.2: Approval = Passed / Processed
        "ind_1_2_num": passing_students_count,
        "ind_1_2_den": processed_count,

        # Ind 1.3: Grade Avg = Sum Grades / Count Grades
        "ind_1_3_num": round(grade_sum, 2),
        "ind_1_3_den": grade_count,

        # Ind 1.4: Activity = Active / Total Enrollment (valid students)
        "ind_1_4_num": active_students_count,
        "ind_1_4_den": total_valid_students,

        # Ind 1.5: Completion = Finishers / Processed
        "ind_1_5_num": finisher_students_count,
        "ind_1_5_den": processed_count
    }
def extract_valid_evaluable_module_types(grades_data: Dict[str, Any]) -> set:
    """
    Extracts the set of module types (e.g., 'assign', 'quiz') that are considered 
    valid evaluable items in the course based on the 3-layer filtering logic.
    
    Used by Group 2 indicators to determine which active modules are graded.
    """
    if not grades_data or not isinstance(grades_data, dict):
        return set()

    user_grades = grades_data.get('usergrades')
    if not user_grades or not isinstance(user_grades, list):
        return set()

    # 1. Inspect structure from the first valid student
    # (Simplified approach reusing the logic structure)
    max_columns = 0
    for student in user_grades:
        if student.get('gradeitems'):
            max_columns = max(max_columns, len(student['gradeitems']))

    if max_columns == 0:
        return set()

    # Gather metadata and participation stats
    participation_counts = [0] * max_columns
    items_metadata = [None] * max_columns
    total_valid_students = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue
        total_valid_students += 1

        for idx, item in enumerate(student['gradeitems']):
            try:
                if items_metadata[idx] is None:
                    items_metadata[idx] = {
                        'type': item.get('itemtype'),
                        'module': item.get('itemmodule'), # Crucial: Capture module type
                        'gmax': float(item.get('grademax', 0)),
                        'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else None,
                        'wfmt': item.get('weightformatted', '')
                    }
                if item.get('graderaw') is not None:
                    participation_counts[idx] += 1
            except (ValueError, TypeError, IndexError):
                continue

    # Detect explicit weights strategy
    has_explicit_weights = False
    for meta in items_metadata:
        if not meta or meta['type'] in ('course', 'category'):
            continue
        if (meta['wraw'] is not None and meta['wraw'] > 0.0001) or (meta['wfmt'] and '0.00' not in meta['wfmt']):
            has_explicit_weights = True
            break

    # Identify valid modules
    valid_modules = set()
    for idx, meta in enumerate(items_metadata):
        if not meta or meta['type'] in ('course', 'category'):
            continue
        
        # Filter: meaningful max grade
        if meta['gmax'] <= 0.01:
            continue

        participation_pct = participation_counts[idx] / total_valid_students if total_valid_students else 0

        # Filter: Weights or Participation
        if has_explicit_weights:
            is_invalid_weight = (meta['wraw'] is None) or (meta['wraw'] <= 0.0001) or ('0.00' in meta['wfmt'])
            if is_invalid_weight:
                continue
        else:
            if participation_pct < MIN_PARTICIPATION_RATE:
                continue

        # If it survived filters, add the module name (e.g. 'assign', 'quiz')
        if meta.get('module'):
            valid_modules.add(meta['module'])

    return valid_modules