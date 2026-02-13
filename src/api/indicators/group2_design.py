from typing import Dict, Any

# Pedagogical taxonomy for active learning modules
ACTIVE_MODULES = {
    "assign", "quiz", "forum", "workshop", "lesson",
    "choice", "feedback", "glossary", "h5pactivity"
}

def calculate_design_metrics(
    course_contents: Dict[str, Any],
    grades_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyzes the course structure to determine instructional design KPIs.
    
    This function evaluates the ratio of active vs. passive modules and 
    the balance between summative (evaluated) and formative activities.
    """
    if not course_contents or not isinstance(course_contents, list):
        return {}

    # Import locally to avoid circular dependencies if any
    from .group1_results import extract_valid_evaluable_module_types
    
    valid_evaluable_modules = extract_valid_evaluable_module_types(grades_data)

    # Counters for instructional design components
    total_visible_modules = 0
    total_active_modules = 0
    evaluated_active_modules = 0
    
    # Iterate through course sections and modules
    for section in course_contents:
        for module in section.get("modules", []):
            # Only count modules visible to students
            if not module.get("visible", False):
                continue

            total_visible_modules += 1
            modname = module.get("modname")

            # Check if the module belongs to the active methodology taxonomy
            if modname in ACTIVE_MODULES:
                total_active_modules += 1
                
                # Check if this specific active module is actually being graded
                if modname in valid_evaluable_modules:
                    evaluated_active_modules += 1

    # Default values to prevent division by zero
    metod_activa_pct = 0.0
    ratio_eval_pct = 0.0

    # Calculate Local Indicators (Course Level)
    if total_visible_modules > 0:
        metod_activa_pct = (total_active_modules / total_visible_modules) * 100

    if total_active_modules > 0:
        ratio_eval_pct = (evaluated_active_modules / total_active_modules) * 100
    else:
        # If no active modules exist, the evaluation ratio doesn't apply
        # However, for consistency in dashboards, we keep it as 0
        ratio_eval_pct = 0.0

    return {
        # --- Course Level Indicators (Percentages) ---
        "ind_2_1_metod_activa": round(metod_activa_pct, 2),
        "ind_2_2_ratio_eval": round(ratio_eval_pct, 2),

        # --- Components for Global Aggregation (Numerators & Denominators) ---
        
        # Ind 2.1: Active Methodology = Active Modules / Total Modules
        "ind_2_1_num": total_active_modules,
        "ind_2_1_den": total_visible_modules,

        # Ind 2.2: Evaluation Ratio = Evaluated Active / Total Active
        "ind_2_2_num": evaluated_active_modules,
        "ind_2_2_den": total_active_modules
    }