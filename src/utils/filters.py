from typing import Dict, Set, Tuple

class CourseFilter:
    """
    Centralizes all business rules for course inclusion/exclusion.
    Layers:
    1. Metadata (Name, Department, Date)
    2. Population (Student count)
    3. Hierarchy (Pedagogical structure)
    4. Integrity (Empty columns check)
    5. Maturity (Academic progress)
    """

    # --- 1. Metadata Config ---
    BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD"]
    INVALID_DEPARTMENTS = {
        "POSTG", "DIDA", "AE", "U_V", 
        "UNIMET TEACHING CENTER", "SERVICIO COMUNITARIO"
    }

    # --- 2. Population Config ---
    MIN_STUDENTS_REQUIRED = 5

    # --- 3. Hierarchy & Design Config ---
    # Max items allowed without hierarchy (Natural Aggregation)
    MAX_FLAT_ITEMS = 6          
    # % of students with manual override to accept a flat course (Rescue Clause)
    MANUAL_GRADING_THRESHOLD = 0.90 

    # --- 4. Integrity Config ---
    # Max percentage of total grade that can be empty (0 participants)
    # Allows small bonus activities to be empty, but not major exams.
    MAX_MISSING_WEIGHT_TOLERANCE = 0.10 

    # --- 5. Maturity Config ---
    PASSING_GRADE = 9.5
    MIN_MATURITY_COMPLIANCE = 70.0
    MIN_ACCEPTABLE_AVG = 5.0
    STRICT_COMPLIANCE_FLOOR = 80.0

    @staticmethod
    def is_valid_metadata(
        course_fullname: str, 
        category_path: str, 
        course_start_ts: int, 
        min_ts: float, 
        max_ts: float
    ) -> bool:
        """
        Layer 1: Filters based on administrative metadata.
        Checks for blacklisted names, invalid departments, and date ranges.
        """
        name_upper = course_fullname.upper()
        path_upper = category_path.upper()

        # 1. Keyword Check
        if any(k in name_upper for k in CourseFilter.BLACKLIST_KEYWORDS):
            return False

        # 2. Department Check
        if any(d in path_upper for d in CourseFilter.INVALID_DEPARTMENTS):
            return False

        # 3. Date Range Check
        if not (min_ts <= course_start_ts <= max_ts):
            return False

        return True

    @staticmethod
    def is_valid_population(processed_count: int) -> bool:
        """
        Layer 2: Ensure statistical significance.
        Courses with too few active students are volatile and unreliable.
        """
        return processed_count >= CourseFilter.MIN_STUDENTS_REQUIRED

    @staticmethod
    def has_valid_hierarchy(
        num_items: int, 
        has_explicit_weights: bool, 
        max_grades_set: Set[float],
        max_effective_weight: float
    ) -> bool:
        """
        Layer 3 (Part A): Assessment Design Check.
        Evaluates if the course structure implies a valid pedagogical design.
        """
        # Case A: Explicit Weights (Teacher Intent)
        # If the teacher set weights manually, we respect their design.
        if has_explicit_weights:
            # it must have at least one significant milestone (>= 10% weight).
            # This filters out "logbook" courses like Case 2607.
            if num_items > 10 and max_effective_weight < 0.10:
                return False
            return True

        # Case B: Natural Aggregation (No explicit weights)
        # If all items have the exact same max grade (e.g. all 20), it is a flat structure.
        # This implies no distinction between important exams and minor tasks.
        if len(max_grades_set) == 1:
            return False
        
        # If max grades vary (e.g. 20, 30, 15), it implies hierarchy -> Accept
        return True

    @staticmethod
    def is_valid_assessment_structure(has_hierarchy: bool, override_ratio: float) -> bool:
        """
        Layer 3 (Part B): Final Structure Decision with 'Rescue Clause'.
        1. If hierarchy is valid -> Accept.
        2. If hierarchy is invalid BUT teacher entered grades manually -> Accept.
        """
        is_manually_graded = override_ratio >= CourseFilter.MANUAL_GRADING_THRESHOLD
        return has_hierarchy or is_manually_graded

    @staticmethod
    def is_integrity_valid(total_missing_weight: float) -> bool:
        """
        Layer 4: Integrity Check.
        Rejects courses where a significant portion of the grade (e.g. >10%) 
        has absolutely no data (empty columns).
        """
        return total_missing_weight <= CourseFilter.MAX_MISSING_WEIGHT_TOLERANCE

    @staticmethod
    def is_academically_mature(average: float, compliance: float) -> bool:
        """
        Layer 5: Maturity Filter.
        Ensures the course is advanced enough to report valid grades.
        """
        # Rule A: Zero activity / Placeholder
        if average == 0:
            return False

        # Rule B: Too early (Very low grade + High incompletion)
        if average < CourseFilter.MIN_ACCEPTABLE_AVG and compliance < CourseFilter.STRICT_COMPLIANCE_FLOOR:
            return False

        # Rule C: Incomplete middle (Failing grade + Mid completion)
        if average < CourseFilter.PASSING_GRADE and compliance < CourseFilter.MIN_MATURITY_COMPLIANCE:
            return False

        return True