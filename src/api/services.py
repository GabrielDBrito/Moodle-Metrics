import datetime
from api.client import call_moodle_api

def get_target_courses(config):
    """
    Retrieves all courses from Moodle and filters them based on the 
    date range specified in config.ini.

    Args:
        config (dict): The full configuration object.

    Returns:
        list: A list of dictionaries, where each dictionary is a course 
              that started within the target dates.
    """
    moodle_config = config['MOODLE']
    filter_config = config['FILTERS']
    
    # 1. Parse configuration dates to Unix Timestamp
    # Moodle stores dates as timestamps (seconds since 1970).
    try:
        start_date_str = filter_config['start_date']
        end_date_str = filter_config['end_date']
        
        # Convert "2026-01-01" -> datetime object -> timestamp (int)
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        
        print(f"Filter Range: {start_date_str} ({start_ts}) to {end_date_str} ({end_ts})")

    except ValueError as e:
        print(f"Date Configuration Error: {e}")
        return []

    # 2. Fetch ALL courses (Metadata only)
    # We increase timeout implicitly in client.py (make sure it's high enough)
    print("⏳ Downloading course catalog... (This might take a while)")
    all_courses = call_moodle_api(moodle_config, "core_course_get_courses")

    if not all_courses:
        print("No courses retrieved from API.")
        return []

    # 3. Apply Python-side Filtering
    filtered_courses = []
    
    print(f"Scanning {len(all_courses)} courses for matches...")
    
    for course in all_courses:
        # Moodle returns 'startdate' as an integer timestamp
        c_start = course.get('startdate', 0)
        c_id = course.get('id')
        c_name = course.get('fullname')

        # Logic: Is the course start date inside our target window?
        if start_ts <= c_start <= end_ts:
            filtered_courses.append({
                'id': c_id,
                'fullname': c_name,
                'startdate': datetime.datetime.fromtimestamp(c_start).strftime('%Y-%m-%d'),
                'categoryid': course.get('categoryid')
            })

    return filtered_courses