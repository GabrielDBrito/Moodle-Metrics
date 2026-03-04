import unicodedata
from typing import Dict, Set

class CourseFilter:
    """
    Centralizes administrative filters for course inclusion.
    """

    # --- 1. Administrative Filters ---
    BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD", "NARANJA"]
    
    # Specific SUBJECT CODES to block (Exact match)
    BLACKLIST_CODES = ["CODNA", "PEE", "FCES", "UNIVIR", "TALLER", "NUEVO", "PADI", "PDU", "NUEVO"] 

    # Specific department names to block (Exact match)
    INVALID_DEPARTMENTS = {
        "POSTG", 
        "DIDA", 
        "AE", 
        "U_V", 
        "UNIMET TEACHING CENTER", 
        "SERVICIO COMUNITARIO", 
        "AULAS DE ENTRENAMIENTO Y CAPACITACIÓN",
        "ARCHIVOS UNIMET VIRTUAL", 
        "PRÁCTICAS AULAS VIRTUALES", 
        "RESPALDOS_BIBLIOTECA", 
        "DIRECCIÓN DE REGISTRO Y CONTROL DE ESTUDIOS", 
        "TALLER DE TRABAJO DE GRADO" 
    }

    # --- 2. Population Config ---
    MIN_STUDENTS_REQUIRED = 5

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Helper to remove accents/tildes and convert to uppercase.
        """
        if not text: return ""
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')
        return text.upper().strip()

    @staticmethod
    def _extract_department_from_path(category_path: str) -> str:
        """
        Extracts the department name (2nd level) from a full category path.
        """
        parts = [p.strip() for p in category_path.split("/") if p.strip()]
        if len(parts) >= 2:
            return CourseFilter._normalize_text(parts[1])
        return ""


    @staticmethod
    def is_valid_metadata(
        course_fullname: str, 
        course_shortname: str,
        category_path: str, 
        course_start_ts: int, 
        min_ts: float, 
        max_ts: float
    ) -> bool:
        """
        Layer 1: Filters based on administrative metadata and dates.
        """
        # Normalize inputs for safe comparison
        norm_name = CourseFilter._normalize_text(course_fullname)
        norm_code = CourseFilter._normalize_text(course_shortname)
        
        # Extract and normalize department name
        dept_name_from_path = CourseFilter._extract_department_from_path(category_path)

        # --- 1. Filter by Shortcode Start Letter --- (NEW FILTER)
        # Discard courses whose shortcode starts with 'C'
        if norm_code.startswith("C"):
            return False

        # --- 2. Filter by Exact Blacklisted Codes ---
        if any(norm_code.startswith(code) for code in CourseFilter.BLACKLIST_CODES):
            return False

        # --- 3. Filter by Blacklisted Keywords in Fullname ---
        if any(k in norm_name for k in CourseFilter.BLACKLIST_KEYWORDS):
            return False

        # --- 4. Filter by Invalid Department Name (Exact Match) ---
        if dept_name_from_path in CourseFilter.INVALID_DEPARTMENTS:
            return False

        # --- 5. Filter by Date Range ---
        if not (min_ts <= course_start_ts <= max_ts):
            return False

        return True
    
    @staticmethod
    def is_valid_population(total_students: int) -> bool:
        """
        Layer 2: Ensure the course has a minimum of students.
        """
        return total_students >= CourseFilter.MIN_STUDENTS_REQUIRED