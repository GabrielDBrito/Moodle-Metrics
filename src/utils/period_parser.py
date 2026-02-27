import re
from datetime import datetime
from typing import Tuple, Optional

def is_term_ready_for_analysis(term_id: str) -> bool:
    """
    Checks if a term is finished and ready based on the current date.
    Schedule:
    - Term 1 (Sep-Nov): Ready from Dec 1st.
    - Term 2 (Jan-Mar): Ready from Apr 1st.
    - Term 3 (Apr-Jun): Ready from Jul 1st.
    - Term I (Jul-Aug): Ready from Sep 1st.
    """
    now = datetime.now()
    # Parse term_id (e.g., "24251")
    # First 2 digits = Start Year (24 -> 2024)
    # Next 2 digits = End Year (25 -> 2025)
    # Last char = Term (1, 2, 3, I)
    
    try:
        start_year_short = int(term_id[:2])
        end_year_short = int(term_id[2:4])
        term_type = term_id[4]
        
        # Determine the target year for the "Ready Date"
        # Term 1 belongs to the start year, others to the end year
        target_year = 2000 + (start_year_short if term_type == "1" else end_year_short)
        
        # Define the threshold date
        if term_type == "1":
            ready_date = datetime(target_year, 12, 1)
        elif term_type == "2":
            ready_date = datetime(target_year, 4, 1)
        elif term_type == "3":
            ready_date = datetime(target_year, 7, 1)
        elif term_type == "I":
            ready_date = datetime(target_year, 9, 1)
        else:
            return False
            
        return now >= ready_date
    except:
        return False

def get_academic_period(course_fullname: str, start_timestamp: int) -> Tuple[str, str, int, str]:
    """
    Determines the academic period based on a 2-layer strategy:
    1. Regex extraction from course name (e.g., "Materia (2425-1)").
    2. Derivation from the start date based on university rules.

    University Logic:
    - Sep-Nov (Months 9,10,11,12): Period 1 of Next Year (e.g., Sep 23 -> 2324-1)
    - Jan-Mar (Months 1,2,3): Period 2 of Current Year (e.g., Jan 24 -> 2324-2)
    - Apr-Jun (Months 4,5,6): Period 3 of Current Year
    - Jul-Aug (Months 7,8): Period I (Intensive) of Current Year

    Returns:
        Tuple containing: (id_tiempo, nombre_periodo, anio_real, trimestre)
    """
    
    # --- Layer 1: Extraction from Name ---
    # Pattern looks for: 4 digits, separator, then 1 digit or 'I'/'i'
    # Examples: "2425-1", "2425 2", "2526-I"
    match = re.search(r'(\d{4})[-_\s]?([123Ii])', course_fullname)
    
    if match:
        year_code = match.group(1)       # example: "2425"
        term = match.group(2).upper()    # example: "1", "2", "I"
        
        # We approximate the real year based on the code (taking the first 2 digits + 2000)
        # This is an approximation for the 'anio' column, which is mostly descriptive.
        real_year = 2000 + int(year_code[:2]) 
        
        period_name = f"{year_code}-{term}"
        time_id = f"{year_code}{term}"
        
        return time_id, period_name, real_year, term

    # --- Layer 2: Derivation from Date ---
    if not start_timestamp:
        return "UNKNOWN", "Unknown", 0, "0"

    dt = datetime.fromtimestamp(int(start_timestamp))
    month = dt.month
    year = dt.year
    
    # Calculate Academic Year Pair (YY-YY)
    # If we are in Sep-Dec (9-12), the academic year starts here (e.g., late 2024 is start of 24-25)
    # If we are in Jan-Aug (1-8), we are in the second half of the academic year (e.g., early 2025 is end of 24-25)
    
    if month >= 9:
        start_y = year
        end_y = year + 1
    else:
        start_y = year - 1
        end_y = year
        
    # Format: "2425"
    acad_year_str = f"{str(start_y)[-2:]}{str(end_y)[-2:]}"
    
    # Determine Term (Trimestre)
    if 9 <= month <= 12:
        term = "1"
    elif 1 <= month <= 3:
        term = "2"
    elif 4 <= month <= 6:
        term = "3"
    elif 7 <= month <= 8:
        term = "I"
    else:
        term = "UNKNOWN"

    period_name = f"{acad_year_str}-{term}"
    time_id = f"{acad_year_str}{term}"
    
    return time_id, period_name, year, term