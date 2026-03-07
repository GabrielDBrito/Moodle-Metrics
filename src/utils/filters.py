import unicodedata
from typing import Dict, Set

class CourseFilter:
    """
    Centralizes administrative filters for course inclusion.
    Only administrative, scope, and population filters are applied.
    """

    # --- 1. Metadata Configuration ---
    # Keywords to exclude from Moodle Fullname
    BLACKLIST_KEYWORDS = ["PRUEBA", "COPIA", "SANDPIT", "COPIA DE SEGURIDAD", "NARANJA"]

    # Specific SUBJECT CODES to block (targets shortname)
    # Restored and cleaned duplicates
    BLACKLIST_CODES = ["CODNA", "PEE", "FCES", "UNIVIR", "TALLER", "NUEVO", "PADI", "PDU"]

    # Categories to exclude (Administrative/Non-undergraduate)
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

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Helper to remove accents and convert to uppercase."""
        if not text: return ""
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')
        return text.upper().strip()

    @staticmethod
    def _extract_department_from_path(category_path: str) -> str:
        """Extracts and normalizes the department name from the category path."""
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
        Layer 1 & 3: Scope and Temporal filters.
        """
        norm_name = CourseFilter._normalize_text(course_fullname)
        norm_code = CourseFilter._normalize_text(course_shortname)
        dept_name = CourseFilter._extract_department_from_path(category_path)

        # 1. Null/Empty Check
        if not norm_code:
            return False

        # 2. Exclusión por código de postgrado (Starts with 'C')
        if norm_code.startswith("C"):
            return False

        # 3. Exclusión por códigos en Blacklist (CODNA, PEE, etc.)
        if any(norm_code.startswith(code) for code in CourseFilter.BLACKLIST_CODES):
            return False

        # 4. Exclusión por nomenclatura (Keywords en nombre completo)
        if any(k in norm_name for k in CourseFilter.BLACKLIST_KEYWORDS):
            return False

        # 5. Exclusión por departamento (Nombre exacto normalizado)
        if dept_name in CourseFilter.INVALID_DEPARTMENTS:
            return False

        # 6. Ventana temporal (Filtro por rango de fechas del config.ini)
        if not (min_ts <= course_start_ts <= max_ts):
            return False

        return True

    @staticmethod
    def is_valid_population(total_enrolled: int, min_threshold: int) -> bool:
        """
        Layer 2: Demographic sufficiency.
        """
        return total_enrolled >= min_threshold