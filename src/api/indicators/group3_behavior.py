from typing import Dict, Any, Optional
def calculate_group3_metrics_from_grades(grades_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    if not grades_data or 'usergrades' not in grades_data:
        return None

    user_grades = grades_data['usergrades']
    if not user_grades:
        return None

    total_students = 0
    total_excellence = 0
    total_feedbacks = 0
    total_graded_items = 0

    for student in user_grades:
        if not student or not student.get('gradeitems'):
            continue

        final_grade = None
        final_gmax = None

        for item in student['gradeitems']:

            # Get final grade and max for course-level item to evaluate excellence
            if item.get('itemtype') == 'course':
                try:
                    final_grade = float(item.get('graderaw'))
                    final_gmax = float(item.get('grademax'))
                except (ValueError, TypeError):
                    continue

            # Feedback is only relevant for graded items that are not the course-level final grade
            if item.get('itemtype') not in ('course', 'category'):
                if item.get('graderaw') is not None:
                    total_graded_items += 1
                    if item.get('feedback'):
                        total_feedbacks += 1

        # Evaluate excellence based on final grade if available
        if final_grade is not None and final_gmax and final_gmax > 0:
            total_students += 1
            if (final_grade / final_gmax) >= 0.9:
                total_excellence += 1

    if total_students == 0:
        return None

    ind_3_1_excelencia = round((total_excellence / total_students) * 100, 2)

    ind_3_2_feedback = 0
    if total_graded_items > 0:
        ind_3_2_feedback = round((total_feedbacks / total_graded_items) * 100, 2)

    return {
        "ind_3_1_excelencia": ind_3_1_excelencia,
        "ind_3_2_feedback": ind_3_2_feedback,

        "ind_3_1_num": total_excellence,
        "ind_3_1_den": total_students,

        "ind_3_2_num": total_feedbacks,
        "ind_3_2_den": total_graded_items
    }