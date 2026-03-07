from typing import Dict, Any, Optional

def calculate_group3_metrics_from_grades(grades_data: Dict[str, Any], params: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Calculates behavioral KPIs.
    - EXCELLENCE: Based on the final grade of ALL enrolled students vs the parameterized threshold.
    - FEEDBACK: Calculated only on VALID (whitelisted) activities to ensure relevance.
    """
    if not grades_data or 'usergrades' not in grades_data:
        return None

    user_grades = grades_data['usergrades']
    if not user_grades:
        return None

    # --- 0. Extract Dynamic Parameters ---
    # Default to 18.0 if not set in config
    excellence_score_param = float(params.get('excellence_score', 18.0))
    # Default to 5% participation if not set
    whitelist_threshold = float(params.get('whitelist_min', 0.05))

    # Calculate the ratio required for excellence (e.g. 18/20 = 0.9)
    # This makes it compatible with any scale (100, 10, 20)
    excellence_ratio_required = excellence_score_param / 20.0

    total_enrolled = len(user_grades)

    # --- 1. REPLICATE WHITELISTING LOGIC (For Feedback KPI) ---
    # We identify which activities are "real" to avoid counting feedback on trash items.
    max_columns = max(len(s.get('gradeitems', [])) for s in user_grades if s.get('gradeitems'))
    if max_columns == 0:
        return None

    items_metadata = [None] * max_columns
    participation_counts = [0] * max_columns
    
    for student in user_grades:
        if not student.get('gradeitems'): continue
        for idx, item in enumerate(student['gradeitems']):
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
        
        # Calculate participation % based on TOTAL enrolled
        part_pct = participation_counts[idx] / total_enrolled
        
        # Filter Logic (Dynamic)
        if has_explicit_weights:
            if meta['wraw'] <= 0.0001: continue
        else:
            if part_pct < whitelist_threshold: continue # Uses param from GUI
        
        whitelisted_indices.append(idx)

    # --- 2. CALCULATE INDICATORS ---
    total_excellence = 0
    total_feedbacks = 0
    total_graded_items_for_feedback = 0

    for student in user_grades:
        if not student.get('gradeitems'): continue

        # A. EXCELLENCE CHECK (Course Total)
        # We look for the course total item
        for item in student['gradeitems']:
            if item.get('itemtype') == 'course':
                try:
                    final_grade = float(item.get('graderaw'))
                    final_gmax = float(item.get('grademax'))
                    
                    # Check against dynamic ratio (e.g. >= 0.9 for 18/20)
                    if final_gmax > 0 and (final_grade / final_gmax) >= excellence_ratio_required:
                        total_excellence += 1
                except (ValueError, TypeError):
                    pass # Student has no grade or invalid grade -> Not Excellent
                break 

        # B. FEEDBACK CHECK (Whitelisted Items Only)
        for idx in whitelisted_indices:
            try:
                # Safety check for index out of bounds
                if idx >= len(student['gradeitems']): continue
                
                item = student['gradeitems'][idx]
                if item.get('graderaw') is not None:
                    total_graded_items_for_feedback += 1
                    # Check if text feedback exists and is not empty
                    if item.get('feedback') and str(item.get('feedback')).strip():
                        total_feedbacks += 1
            except (IndexError, AttributeError):
                continue

    # --- 3. FINAL COMPILATION ---
    
    # Ind 3.1 Excelencia: (Excellent Students / Total Enrolled)
    # Reflects the reality: if 50 students enrolled and only 5 got 19, excellence is 10%.
    ind_3_1_excelencia = round((total_excellence / total_enrolled) * 100, 2)

    # Ind 3.2 Feedback: (Items with Feedback / Total Items Graded)
    # Measures teacher effort on graded tasks.
    ind_3_2_feedback = 0
    if total_graded_items_for_feedback > 0:
        ind_3_2_feedback = round((total_feedbacks / total_graded_items_for_feedback) * 100, 2)

    return {
        "ind_3_1_excelencia": ind_3_1_excelencia,
        "ind_3_2_feedback": ind_3_2_feedback,

        "ind_3_1_num": total_excellence,
        "ind_3_1_den": total_enrolled, # Denominator is now Total Enrolled

        "ind_3_2_num": total_feedbacks,
        "ind_3_2_den": total_graded_items_for_feedback
    }