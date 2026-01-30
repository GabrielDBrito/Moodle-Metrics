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

    # Reutilizar filtro similar a group1 para detectar ítems válidos
    participation_counts = [0] * max_columns
    items_metadata = [None] * max_columns
    total_valid_students = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue
        total_valid_students += 1

        for idx, item in enumerate(student['gradeitems']):
            if items_metadata[idx] is None:
                items_metadata[idx] = {
                    'type': item.get('itemtype'),
                    'module': item.get('itemmodule'),
                    'gmax': float(item.get('grademax', 0)),
                    'wraw': float(item.get('weightraw')) if item.get('weightraw') is not None else None,
                    'wfmt': item.get('weightformatted', '')
                }
            if item.get('graderaw') is not None:
                participation_counts[idx] += 1

    # Detectar si hay pesos explícitos
    has_explicit_weights = any(
        meta and meta['type'] not in ('course', 'category') and
        ((meta['wraw'] is not None and meta['wraw'] > 0.0001) or ('0.00' not in meta['wfmt']))
        for meta in items_metadata
    )

    valid_indices = []
    for idx, meta in enumerate(items_metadata):
        if not meta or meta['type'] in ('course', 'category'):
            continue
        if meta['gmax'] <= 0.01:
            continue

        participation_pct = participation_counts[idx] / total_valid_students if total_valid_students > 0 else 0

        if has_explicit_weights:
            if meta['wraw'] is None or meta['wraw'] <= 0.0001 or '0.00' in meta['wfmt']:
                continue
        else:
            if participation_pct < 0.05:  # umbral de participación
                continue

        valid_indices.append(idx)

    # Calcular indicadores
    total_valid_items = len(valid_indices)
    if total_valid_items == 0:
        return None

    total_graded_items = 0
    total_feedbacks = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        for idx in valid_indices:
            try:
                item = student['gradeitems'][idx]
                if item.get('graderaw') is not None:
                    total_graded_items += 1
                    feedback = item.get('feedback')
                    if feedback:
                        total_feedbacks += 1
            except IndexError:
                continue

    # 3.1: % de ítems con calificación (proxy para procrastinación)
    ind_3_1_procrastinacion_pct = round((total_graded_items / (total_valid_items * total_valid_students)) * 100, 2) if total_valid_items > 0 and total_valid_students > 0 else None
    # 3.2: % de calificaciones con feedback
    ind_3_2_feedback_ratio = round((total_feedbacks / total_graded_items) * 100, 2) if total_graded_items > 0 else None

    return {
        'ind_3_1_procrastinacion_pct': ind_3_1_procrastinacion_pct,
        'ind_3_2_feedback_ratio': ind_3_2_feedback_ratio
    }
