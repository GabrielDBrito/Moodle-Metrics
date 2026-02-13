from typing import Dict, Any, Optional

def calculate_group3_metrics_from_grades(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculates behavioral and interaction KPIs based on gradebook records.
    
    This group focuses on 'Selectivity' (Excellence rate) and 'Feedback' 
    (Instructor interaction level).
    """
    if not grades_data or 'usergrades' not in grades_data:
        return None

    user_grades = grades_data['usergrades']
    if not user_grades:
        return None

    # Determine the number of grade columns to analyze
    max_columns = 0
    for student in user_grades:
        if student.get('gradeitems'):
            max_columns = max(max_columns, len(student['gradeitems']))

    if max_columns == 0:
        return None

    items_metadata = [None] * max_columns
    total_valid_students = 0

    # --- 1. Metadata Extraction ---
    # Identify evaluable items and their maximum possible grades
    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        total_valid_students += 1

        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                try:
                    gmax = float(item.get('grademax', 0))
                except (ValueError, TypeError):
                    gmax = 0

                items_metadata[idx] = {
                    'type': item.get('itemtype'),
                    'gmax': gmax
                }

    # --- 2. Valid Items Filtering ---
    # We only care about actual activities (excluding course/category totals)
    valid_indices = []
    for idx, meta in enumerate(items_metadata):
        if not meta or meta['type'] in ('course', 'category') or meta['gmax'] <= 0.01:
            continue
        valid_indices.append(idx)

    if not valid_indices:
        return None

    # --- 3. Interaction & Performance Counters ---
    total_graded_items = 0    # Common Denominator
    total_feedbacks = 0       # Num for Feedback KPI
    total_excellence = 0      # Num for Selectivity KPI

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        for idx in valid_indices:
            try:
                item = student['gradeitems'][idx]
                graderaw = item.get('graderaw')

                # Only count items that have an actual grade recorded
                if graderaw is None:
                    continue

                graderaw = float(graderaw)
                gmax = items_metadata[idx]['gmax']

                total_graded_items += 1

                # Check for instructor feedback
                if item.get('feedback'):
                    total_feedbacks += 1

                # Check for excellence (normalized grade >= 90%)
                if gmax > 0 and (graderaw / gmax) >= 0.9:
                    total_excellence += 1

            except (IndexError, ValueError, TypeError):
                continue

    if total_graded_items == 0:
        return None

    # --- 4. Final KPI Compilation ---
    # Local Percentages (Course Level)
    ind_3_1_selectivity = round((total_excellence / total_graded_items) * 100, 2)
    ind_3_2_feedback = round((total_feedbacks / total_graded_items) * 100, 2)

    return {
        # --- Course Level Indicators (Percentages) ---
        'ind_3_1_selectividad': ind_3_1_selectivity,
        'ind_3_2_feedback': ind_3_2_feedback,

        # --- Components for Global Aggregation (Numerators & Denominators) ---
        
        # Ind 3.1: Selectivity = Excellence Count / Total Grades
        'ind_3_1_num': total_excellence,
        'ind_3_1_den': total_graded_items,

        # Ind 3.2: Feedback = Feedback Count / Total Grades
        'ind_3_2_num': total_feedbacks,
        'ind_3_2_den': total_graded_items
    }