import statistics
from typing import Dict, List, Optional, Any

# --- BUSINESS CONFIGURATION ---
TARGET_SCALE = 20.0
MIN_VALID_GRADE = 1.0
PASSING_GRADE = 9.5

# KPI Thresholds
DENSITY_ACTIVE = 0.40
DENSITY_COMPLETE = 0.80

# Filtering Thresholds
MIN_PARTICIPATION_RATE = 0.05
MIN_STUDENTS_REQUIRED = 5

def calculate_group1_metrics(grades_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Calculates academic KPIs (Approval, Completion, Grades) for a specific course.
    
    Implements a 'Success-Based Denominator' logic to handle flexible learning paths
    and detects 'Digital Deserts' (courses with no online activity) to return 
    process indicators as None.
    """
    if not grades_data or not isinstance(grades_data, dict):
        return None
    
    all_students = grades_data.get('usergrades')
    if not all_students or not isinstance(all_students, list) or len(all_students) < MIN_STUDENTS_REQUIRED:
        return None

    # ---------------------------------------------------------
    # STEP 0: Scale Detection & Normalization Strategy
    # ---------------------------------------------------------
    # Detect the grading scale used in the course to normalize it to Base 20.
    global_max_observed = 0.0
    config_max_grade = 0.0

    for student in all_students:
        if not student or not student.get('gradeitems'):
            continue
        
        # Check course total item
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                if config_max_grade == 0.0:
                    config_max_grade = float(item.get('grademax', 0))
                
                raw_val = item.get('graderaw')
                if raw_val is not None:
                    try:
                        val = float(raw_val)
                        if val > global_max_observed:
                            global_max_observed = val
                    except (ValueError, TypeError):
                        pass
                break

    normalize_divisor = 1.0
    should_normalize = False

    # Logic to handle different scales (e.g., Base 100, Base 1, Base 5)
    if config_max_grade > 25.0:
        # Likely Base 100
        if global_max_observed > 22.0:
            should_normalize = True
            normalize_divisor = config_max_grade
    elif config_max_grade > 0.001 and abs(config_max_grade - 20.0) > 0.1:
        # Weird small scales (e.g., 0-1, 0-5, 0-10)
        should_normalize = True
        normalize_divisor = config_max_grade

    # ---------------------------------------------------------
    # STEP 1: Task Whitelisting (Noise Filtering)
    # ---------------------------------------------------------
    # Identify valid evaluable items based on weight and participation rates.
    max_cols = 0
    for s in all_students:
        if s.get('gradeitems'):
            max_cols = max(max_cols, len(s['gradeitems']))

    if max_cols == 0:
        return None

    column_counts = [0] * max_cols
    column_meta = [None] * max_cols
    total_scanned = 0

    for s in all_students:
        if not s: continue
        items = s.get('gradeitems')
        if not items: continue
        total_scanned += 1

        for idx, item in enumerate(items):
            try:
                if not item: continue
                if column_meta[idx] is None:
                    column_meta[idx] = {
                        'type': item.get('itemtype'),
                        'gmax': float(item.get('grademax', 0)),
                        'wraw': float(item.get('weightraw', 0)) if item.get('weightraw') is not None else None,
                        'wfmt': item.get('weightformatted', '')
                    }
                if item.get('graderaw') is not None:
                    column_counts[idx] += 1
            except (ValueError, TypeError):
                continue

    # Determine if weights are configured in the gradebook
    has_positive_weights = False
    for idx in range(max_cols):
        meta = column_meta[idx]
        if not meta or meta['type'] in ('course', 'category'):
            continue
        if (meta['wraw'] and meta['wraw'] > 0.0001) or (meta['wfmt'] and '0.00' not in meta['wfmt']):
            has_positive_weights = True
            break

    # Filter indices
    evaluable_indices = []
    for idx in range(max_cols):
        meta = column_meta[idx]
        if not meta: continue
        if meta['type'] in ('course', 'category'): continue
        if meta['gmax'] <= 0.01: continue

        participation_pct = column_counts[idx] / total_scanned if total_scanned > 0 else 0

        # Filtering logic: Ignore items with 0 weight or very low participation
        if has_positive_weights:
            is_zero_weight = (meta['wraw'] is not None and meta['wraw'] <= 0.0001) or \
                             (meta['wfmt'] and '0.00' in meta['wfmt'])
            if is_zero_weight: continue
            if meta['wraw'] is None and participation_pct < MIN_PARTICIPATION_RATE: continue
        else:
            if participation_pct < MIN_PARTICIPATION_RATE: continue
        
        evaluable_indices.append(idx)

    # Detect "Digital Desert": Courses with no valid online activities.
    is_digital_desert = (len(evaluable_indices) == 0)

    # ---------------------------------------------------------
    # STEP 1.5: Dynamic Denominator Calculation
    # ---------------------------------------------------------
    # The denominator is set by the most active student who achieved a passing grade.
    final_denominator = 1.0

    if not is_digital_desert:
        max_checks_passed = 0
        max_checks_any = 0
        passers_exist = False

        for s in all_students:
            if not s or not s.get('gradeitems'): continue

            # Count completed tasks for this student
            checks_temp = 0
            for idx in evaluable_indices:
                try:
                    if idx < len(s['gradeitems']):
                        item = s['gradeitems'][idx]
                        if item and item.get('graderaw') is not None:
                            checks_temp += 1
                except (IndexError, AttributeError):
                    pass

            # Check final grade for passing status
            raw_final = 0.0
            for item in s.get('gradeitems', []):
                if item.get('itemtype') == 'course' and item.get('graderaw') is not None:
                    raw_final = float(item['graderaw'])
                    break
            
            norm_final = raw_final
            if should_normalize:
                norm_final = (raw_final / normalize_divisor) * TARGET_SCALE
            
            if norm_final >= PASSING_GRADE:
                passers_exist = True
                if checks_temp > max_checks_passed:
                    max_checks_passed = checks_temp
            
            if checks_temp > max_checks_any:
                max_checks_any = checks_temp

        # Set denominator
        if passers_exist and max_checks_passed > 0:
            final_denominator = max_checks_passed
        else:
            # Fallback: Use total columns if no one passed
            total_cols = len(evaluable_indices)
            final_denominator = max(total_cols, 1)

    # ---------------------------------------------------------
    # STEP 2: Individual Student Metrics
    # ---------------------------------------------------------
    total_checks_realized = 0
    total_checks_capacity = 0
    
    count_actives_kpi = 0
    count_finishers_kpi = 0
    
    grades_for_average = []
    all_grades = []
    valid_student_count = 0
    total_enrolled = 0

    for student in all_students:
        if not student: continue
        total_enrolled += 1

        items = student.get('gradeitems')
        if items is None or not isinstance(items, list): continue

        # A. Retrieve Final Grade
        final_grade = 0.0
        has_final = False
        for item in items:
            try:
                if item and item.get('itemtype') == 'course':
                    raw = item.get('graderaw')
                    if raw is not None:
                        final_grade = float(raw)
                        has_final = True
                    break
            except (ValueError, TypeError):
                continue

        # B. Count Digital Checks (Strict)
        items_completed_count = 0
        if not is_digital_desert:
            for idx in evaluable_indices:
                try:
                    if idx < len(items):
                        item = items[idx]
                        if item and item.get('graderaw') is not None:
                            items_completed_count += 1
                except (IndexError, AttributeError):
                    continue
            
            total_checks_realized += items_completed_count

        # C. Validate Participant
        # Valid if they have a final grade OR at least one digital interaction
        is_participant = (has_final and final_grade >= 0.1) or (items_completed_count > 0)

        if is_participant:
            valid_student_count += 1

            # Normalize Grade
            norm_grade = 0.0
            if has_final:
                if should_normalize:
                    norm_grade = (final_grade / normalize_divisor) * TARGET_SCALE
                else:
                    norm_grade = final_grade
            
            # Cap at target scale
            if norm_grade > TARGET_SCALE: 
                norm_grade = TARGET_SCALE

            # D. Status Determination
            is_active = False
            is_finisher = False

            if is_digital_desert:
                # Analog Mode: Active if grade exists. Finisher is N/A (Null).
                if has_final and norm_grade >= 0.1:
                    is_active = True
            else:
                # Digital Mode: Based on density relative to the denominator
                student_density = items_completed_count / final_denominator

                # Active: High density OR Passing grade
                if student_density >= DENSITY_ACTIVE: is_active = True
                if norm_grade >= PASSING_GRADE: is_active = True

                # Finisher: STRICT density requirement (Grade alone does not qualify)
                if student_density >= DENSITY_COMPLETE:
                    is_finisher = True
            
            if is_active: count_actives_kpi += 1
            if is_finisher: count_finishers_kpi += 1

            all_grades.append(norm_grade)
            if is_active and norm_grade >= 0.5:
                grades_for_average.append(norm_grade)

            if not is_digital_desert:
                total_checks_capacity += final_denominator

    if valid_student_count < MIN_STUDENTS_REQUIRED:
        return None

    # ---------------------------------------------------------
    # STEP 3: Aggregation and Final Output
    # ---------------------------------------------------------
    
    # 1. Grade Statistics
    if not grades_for_average:
        avg_grade, med_grade, dev_grade = 0.0, 0.0, 0.0
    else:
        avg_grade = statistics.mean(grades_for_average)
        med_grade = statistics.median(grades_for_average)
        dev_grade = statistics.stdev(grades_for_average) if len(grades_for_average) > 1 else 0.0

    passing_count = sum(1 for g in all_grades if g >= PASSING_GRADE)
    approval_rate = (passing_count / valid_student_count) * 100

    # 2. Activity Rate
    active_rate = 0.0
    if total_enrolled > 0:
        active_rate = (count_actives_kpi / total_enrolled) * 100

    # 3. Process Indicators (Return None if Digital Desert)
    if is_digital_desert:
        compliance_rate = None
        completion_rate = None
    else:
        completion_rate = (count_finishers_kpi / valid_student_count) * 100
        
        compliance_rate = 0.0
        if total_checks_capacity > 0:
            compliance_rate = (total_checks_realized / total_checks_capacity) * 100
        
        if compliance_rate > 100.0: 
            compliance_rate = 100.0
        
        completion_rate = round(completion_rate, 2)
        compliance_rate = round(compliance_rate, 2)

    return {
        "n_estudiantes_procesados": valid_student_count,
        "ind_1_1_cumplimiento": compliance_rate,      # None if analog course
        "ind_1_2_aprobacion": round(approval_rate, 2),
        "ind_1_3_promedio": round(avg_grade, 2),
        "ind_1_3_mediana": round(med_grade, 2),
        "ind_1_3_desviacion": round(dev_grade, 2),
        "ind_1_4_activos": round(active_rate, 2),
        "ind_1_5_finalizacion": completion_rate       # None if analog course
    }