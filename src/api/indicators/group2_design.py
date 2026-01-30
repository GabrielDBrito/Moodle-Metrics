from typing import Dict, Any
from .group1_results import extract_valid_evaluable_module_types

# Taxonomía pedagógica
ACTIVE_MODULES = {
    "assign", "quiz", "forum", "workshop", "lesson",
    "choice", "feedback", "glossary", "h5pactivity"
}

def calculate_design_metrics(
    course_contents: Dict[str, Any],
    grades_data: Dict[str, Any]
) -> Dict[str, float]:

    if not course_contents or not isinstance(course_contents, list):
        return {}

    valid_evaluable_modules = extract_valid_evaluable_module_types(grades_data)

    if not valid_evaluable_modules:
        return {}

    total_active = 0
    evaluated_active = 0
    non_evaluated_active = 0
    total_modules = 0  # Contador total de módulos visibles

    for section in course_contents:
        for module in section.get("modules", []):
            if not module.get("visible", False):
                continue

            total_modules += 1  # contar todos los módulos visibles

            modname = module.get("modname")
            if modname not in ACTIVE_MODULES:
                continue

            total_active += 1  # contar módulos activos según taxonomía

            if modname in valid_evaluable_modules:
                evaluated_active += 1
            else:
                non_evaluated_active += 1

    if total_modules == 0:
        # evitar división por cero
        return {
            "ind_2_1_metodologia_activa_ratio": 0.0,
            "ind_2_1_metodologia_activa_pct": 0.0,
            "ind_2_2_eval_noeval_ratio": 0.0,
            "ind_2_2_balance_eval_pct": 0.0
        }

    metodologia_activa_ratio = total_active / total_modules
    metodologia_activa_pct = metodologia_activa_ratio * 100

    non_evaluated_active = max(non_evaluated_active, 0)
    eval_noeval_ratio = (
        evaluated_active / non_evaluated_active
        if non_evaluated_active > 0 else float(evaluated_active)
    )

    balance_eval = evaluated_active / (evaluated_active + non_evaluated_active) if (evaluated_active + non_evaluated_active) > 0 else 0
    balance_eval_pct = balance_eval * 100
    if balance_eval_pct == 0:
        balance_eval_pct = 100
    return {
        #"ind_2_1_metodologia_activa_ratio": round(metodologia_activa_ratio, 4),
        "ind_2_1_metodologia_activa_pct": round(metodologia_activa_pct, 2),
        #"ind_2_2_eval_noeval_ratio": round(eval_noeval_ratio, 4),
        "ind_2_2_balance_eval_pct": round(balance_eval_pct, 2)
    }
