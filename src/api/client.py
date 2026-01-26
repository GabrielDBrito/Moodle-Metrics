import requests
import json

def call_moodle_api(moodle_config, function_name, **kwargs):
    """
    Generic wrapper for Moodle Web Services.
    Handles parameter formatting, including list/array conversion for batch requests.
    """
    url = f"{moodle_config['URL']}/webservice/rest/server.php"
    
    # Base parameters required by Moodle
    params = {
        "wstoken": moodle_config['TOKEN'],
        "wsfunction": function_name,
        "moodlewsrestformat": "json"
    }

    # Dynamic parameter handling
    for key, value in kwargs.items():
        if isinstance(value, list):
            # Moodle API expects arrays like: courseids[0]=1, courseids[1]=2
            for i, item in enumerate(value):
                params[f"{key}[{i}]"] = item
        else:
            params[key] = value

    try:
        response = requests.post(url, data=params, timeout=300)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for Moodle-level exceptions
        if isinstance(data, dict) and 'exception' in data:
            print(f"[API ERROR] {function_name}: {data.get('message')}")
            return None
            
        return data

    except requests.exceptions.RequestException as e:
        print(f"[NETWORK ERROR] {function_name}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"[DATA ERROR] {function_name}: Invalid JSON response")
        return None

def get_target_courses(config):
    """
    Retrieves the full list of courses from Moodle.
    """
    moodle_config = config['MOODLE']
    
    print("   > Contacting Moodle to fetch course catalog...")
    
    # 'core_course_get_courses' usually returns a list directly
    courses = call_moodle_api(moodle_config, "core_course_get_courses")
    
    if courses is None:
        return []
        
    # Moodle sometimes returns a dict with warnings, or a direct list.
    # We ensure we return a list.
    if isinstance(courses, list):
        print(f"   > Catalog downloaded successfully. Total courses: {len(courses)}")
        return courses
    elif isinstance(courses, dict):
        # Handle edge case where Moodle wraps courses (rare in this function but possible)
        return courses.get('courses', [])
    
    return []