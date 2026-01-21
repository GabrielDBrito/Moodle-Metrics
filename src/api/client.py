import requests
import json

def call_moodle_api(config, function_name, **params):
    """
    Generic function to execute a REST call to the Moodle API.
    
    Args:
        config (configparser.SectionProxy): The 'MOODLE' section from config.ini.
        function_name (str): The specific Moodle WS function (e.g., 'core_course_get_courses').
        **params: Additional parameters required by the specific function.
        
    Returns:
        dict/list: The JSON response parsed as a Python object, or None if failed.
    """
    
    # Prepare the standard parameters required by Moodle
    request_params = {
        "wstoken": config['token'],
        "wsfunction": function_name,
        "moodlewsrestformat": "json",
        **params # Unpack specific parameters (like courseid or userid)
    }
    
    url = config['url']
    
    try:
        print(f"Calling API: {function_name}...")
        
        # Execute the HTTP GET request with a timeout
        response = requests.get(url, params=request_params, timeout=300)
        
        # Check for HTTP errors (404, 500, etc.)
        response.raise_for_status()
        
        # Parse JSON
        data = response.json()
        
        # Check for Moodle-specific logic errors (e.g., Invalid Token)
        if isinstance(data, dict) and 'exception' in data:
            print(f"Moodle Exception: {data['message']} (Code: {data['errorcode']})")
            return None
            
        return data

    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        return None