import unicodedata
from typing import Dict, Set

class CourseFilter:
    """
    Centralizes administrative filters for course inclusion.
    Quality and maturity filters have been disabled as per new directive
    to show a "cruder" reality of the Moodle data.
    """

    # --- 1. Administrative Filters ---
    # Keywords to look for in the FULLNAME (Normalized for accents later)
    BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD", "NARANJA"]

    # Specific SUBJECT CODES to block 
    BLACKLIST_CODES = ["CODNA"]

    INVALID_DEPARTMENTS = {
        "POSTG", "DIDA", "AE", "U_V", 
        "UNIMET TEACHING CENTER", "SERVICIO COMUNITARIO"
    }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Helper to remove accents/tildes and convert to uppercase.
        """
        if not text: return ""
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')
        return text.upper()

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
        # Normalize all inputs for safe comparison
        norm_name = CourseFilter._normalize_text(course_fullname)
        norm_path = CourseFilter._normalize_text(category_path)
        norm_code = CourseFilter._normalize_text(course_shortname)

        # 1. Exact Code Check (CODNA, etc)
        if any(norm_code.startswith(code) for code in CourseFilter.BLACKLIST_CODES):
            return False

        # 2. Keyword Check (PRUEBA, NARANJA, etc)
        if any(k in norm_name for k in CourseFilter.BLACKLIST_KEYWORDS):
            return False

        # 3. Department Check
        if any(d in norm_path for d in CourseFilter.INVALID_DEPARTMENTS):
            return False

        # 4. Date Range Check (Ventana Temporal)
        if not (min_ts <= course_start_ts <= max_ts):
            return False

        return True