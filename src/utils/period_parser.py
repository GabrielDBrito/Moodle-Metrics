import re
from datetime import datetime
from typing import Tuple

def get_academic_period(course_fullname: str, start_timestamp: int) -> Tuple[str, str, int, str]:
    """
    Determines the academic period prioritizing the Name Tag over the Date.
    The Name is considered the absolute source of truth.
    """
    # --- Layer 1: Search in Name (Priority) ---
    # Pattern: 4 digits + Term (1, 2, 3, or I)
    name_match = re.search(r'(\d{4})[-_\s]?([123Ii])', course_fullname)
    
    if name_match:
        year_code = name_match.group(1)       # e.g., "2526"
        term = name_match.group(2).upper()    # e.g., "1"
        
        time_id = f"{year_code}{term}"
        period_name = f"{year_code}-{term}"
        # Approximate year for the 'anio' column
        real_year = 2000 + int(year_code[:2]) 
        
        return time_id, period_name, real_year, term

    # --- Layer 2: Fallback to Date (Only if Name has no tag) ---
    dt = datetime.fromtimestamp(int(start_timestamp))
    month, year = dt.month, dt.year
    
    if month >= 9:
        start_y, end_y, date_term = year, year + 1, "1"
    elif 1 <= month <= 3:
        start_y, end_y, date_term = year - 1, year, "2"
    elif 4 <= month <= 6:
        start_y, end_y, date_term = year - 1, year, "3"
    elif 7 <= month <= 8:
        start_y, end_y, date_term = year - 1, year, "I"
    else:
        date_term = "UNKNOWN"

    date_acad_year = f"{str(start_y)[-2:]}{str(end_y)[-2:]}"
    return f"{date_acad_year}{date_term}", f"{date_acad_year}-{date_term}", year, date_term

def is_term_ready_for_analysis(term_id: str) -> bool:
    """
    Check availability based on UNIMET schedule.
    """
    if not term_id or term_id == "UNKNOWN": return False
    now = datetime.now()
    try:
        start_year = 2000 + int(term_id[:2])
        end_year = 2000 + int(term_id[2:4])
        term_type = term_id[4]

        if term_type == "1":
            ready_date = datetime(start_year, 12, 1)
        elif term_type == "2":
            ready_date = datetime(end_year, 4, 1)
        elif term_type == "3":
            ready_date = datetime(end_year, 7, 1)
        elif term_type == "I":
            ready_date = datetime(end_year, 9, 1)
        else:
            return False
        return now >= ready_date
    except:
        return False