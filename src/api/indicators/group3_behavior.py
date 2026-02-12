from typing import Dict, Any, Optional

def calculate_group3_metrics_from_grades(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    if not grades_data or 'usergrades' not in grades_data:
        return None

    user_grades = grades_data['usergrades']
    if not user_grades:
        return None

    max_columns = 0
    for student in user_grades:
        if student.get('gradeitems'):
            max_columns = max(max_columns, len(student['gradeitems']))

    if max_columns == 0:
        return None

    items_metadata = [None] * max_columns
    total_valid_students = 0

    # -------------------------
    # 1️⃣ Construir metadata
    # -------------------------
    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        total_valid_students += 1

        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                try:
                    gmax = float(item.get('grademax', 0))
                except:
                    gmax = 0

                items_metadata[idx] = {
                    'type': item.get('itemtype'),
                    'gmax': gmax
                }

    # -------------------------
    # 2️⃣ Detectar ítems válidos
    # -------------------------
    valid_indices = []

    for idx, meta in enumerate(items_metadata):
        if not meta:
            continue
        if meta['type'] in ('course', 'category'):
            continue
        if meta['gmax'] <= 0.01:
            continue

        valid_indices.append(idx)

    if not valid_indices:
        return None

    # -------------------------
    # 3️⃣ Cálculos
    # -------------------------
    total_graded_items = 0
    total_feedbacks = 0
    total_excellence = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        for idx in valid_indices:
            try:
                item = student['gradeitems'][idx]
                graderaw = item.get('graderaw')

                if graderaw is None:
                    continue

                graderaw = float(graderaw)
                gmax = items_metadata[idx]['gmax']

                total_graded_items += 1

                # Feedback
                if item.get('feedback'):
                    total_feedbacks += 1

                # Excelencia normalizada ≥ 90%
                if gmax > 0 and (graderaw / gmax) >= 0.9:
                    total_excellence += 1

            except (IndexError, ValueError, TypeError):
                continue

    if total_graded_items == 0:
        return None

    # -------------------------
    # 4️⃣ Indicadores finales
    # -------------------------
    ind_3_1_selectividad = round(
        (total_excellence / total_graded_items) * 100, 2
    )

    ind_3_2_feedback = round(
        (total_feedbacks / total_graded_items) * 100, 2
    )

    return {
        'ind_3_1_selectividad': ind_3_1_selectividad,
        'ind_3_2_feedback': ind_3_2_feedback
    }
