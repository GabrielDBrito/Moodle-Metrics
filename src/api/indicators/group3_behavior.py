from typing import Dict, Any, Optional
# Importamos la lógica de whitelisting para el feedback
from .group1_results import extract_valid_evaluable_module_types, MIN_PARTICIPATION_RATE

def calculate_group3_metrics_from_grades(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculates behavioral KPIs with a hybrid approach:
    - EXCELLENCE: Based on the final grade of ALL enrolled students.
    - FEEDBACK: Calculated only on VALID (whitelisted) activities to ensure relevance.
    """
    if not grades_data or 'usergrades' not in grades_data:
        return None

    user_grades = grades_data['usergrades']
    if not user_grades:
        return None

    # --- 1. EXCELLENCE KPI (Based on Final Grade of ALL students) ---
    total_students_with_final_grade = 0
    total_excellence = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                try:
                    final_grade = float(item.get('graderaw'))
                    final_gmax = float(item.get('grademax'))
                    
                    # We count any student with a registered final grade
                    total_students_with_final_grade += 1
                    
                    if final_gmax > 0 and (final_grade / final_gmax) >= 0.9:
                        total_excellence += 1
                        
                except (ValueError, TypeError):
                    # Skip if grade is not a valid number
                    pass
                break # Move to the next student once course item is found

    # Calculate final Excellence indicator
    ind_3_1_excelencia = 0
    if total_students_with_final_grade > 0:
        ind_3_1_excelencia = round((total_excellence / total_students_with_final_grade) * 100, 2)

    # --- 2. FEEDBACK KPI (Based on WHITELISTED activities) ---
    # We must replicate the whitelisting logic from Group 1 to be consistent
    
    # 2.1 Replicate Whitelisting
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades if s.get('gradeitems'))
    items_metadata = [None] * max_columns
    participation_counts = [0] * max_columns
    
    for student in user_grades:
        for idx, item in enumerate(student.get('gradeitems', [])):
            if items_metadata[idx] is None:
                items_metadata[idx] = {
                    'type': item.get('itemtype'),
                    'gmax': float(item.get('grademax', 0)),
                    'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else 0.0
                }
            if item.get('graderaw') is not None:
                participation_counts[idx] += 1
    
    has_explicit_weights = any(m and m['type'] not in ('course', 'category') and m['wraw'] > 0.0001 for m in items_metadata)
    whitelisted_indices = []
    
    for idx in range(max_columns):
        meta = items_metadata[idx]
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01: continue
        
        # We need a fallback for total_valid_students if list is empty
        part_pct = participation_counts[idx] / len(user_grades) if user_grades else 0
        
        if has_explicit_weights and meta['wraw'] <= 0.0001: continue
        if not has_explicit_weights and part_pct < MIN_PARTICIPATION_RATE: continue
        
        whitelisted_indices.append(idx)
        
    # 2.2 Calculate Feedback on the whitelisted sample
    total_feedbacks = 0
    total_graded_items_for_feedback = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'): continue
        for idx in whitelisted_indices:
            try:
                item = student['gradeitems'][idx]
                if item.get('graderaw') is not None:
                    total_graded_items_for_feedback += 1
                    if item.get('feedback'):
                        total_feedbacks += 1
            except (IndexError, ValueError, TypeError):
                continue
    
    ind_3_2_feedback = 0
    if total_graded_items_for_feedback > 0:
        ind_3_2_feedback = round((total_feedbacks / total_graded_items_for_feedback) * 100, 2)

    # --- 3. Final Compilation ---
    return {
        "ind_3_1_excelencia": ind_3_1_excelencia,
        "ind_3_2_feedback": ind_3_2_feedback,

        "ind_3_1_num": total_excellence,
        "ind_3_1_den": total_students_with_final_grade, # Denominator is students with a final grade

        "ind_3_2_num": total_feedbacks,
        "ind_3_2_den": total_graded_items_for_feedback # Denominator is total valid graded items
    }