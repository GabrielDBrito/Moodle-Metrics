import sys
import os

# --- FIX DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from utils.config_loader import load_config
# Ahora importamos nuestro servicio inteligente
from api.services import get_target_courses

def main():
    print("==========================================")
    print("   UNIMET Analytics ETL - Starting Job")
    print("==========================================\n")

    try:
        # 1. Load Configuration
        config = load_config()
        
        # 2. Extraction Phase: Get Courses by Date
        print("\n--- PHASE 1: Extracting Target Courses ---")
        courses_list = get_target_courses(config)
        
        # 3. Report Results
        if courses_list:
            count = len(courses_list)
            print(f"\n✅ Success! Found {count} active courses in this trimester.")
            
            # Show the first 5 found as a preview
            print("   Preview of found courses:")
            for course in courses_list[:5]:
                print(f"   - [{course['id']}] {course['fullname']} (Starts: {course['startdate']})")
        else:
            print("\n⚠️ No courses found in that date range (or API failed).")
            print("   Check your dates in config.ini")

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
    
    print("\n==========================================")
    print("   Job Finished")
    print("==========================================")

if __name__ == "__main__":
    main()