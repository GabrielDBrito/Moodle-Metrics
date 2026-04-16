import os
import requests
import sys

def ping_supabase():
    """
    Sends a REST API request to Supabase to simulate real usage activity.
    This prevents the project from being paused in the free tier.
    """
    try:
        # Load environment variables
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")

        if not all([supabase_url, supabase_key]):
            print("ERROR: Missing Supabase credentials in GitHub Secrets.")
            sys.exit(1)

        # Endpoint (usa una tabla real de tu modelo)
        endpoint = f"{supabase_url}/rest/v1/dim_tiempo?select=id_tiempo&limit=1"

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }

        print("Enviando request REST a Supabase...")

        response = requests.get(endpoint, headers=headers, timeout=20)

        if response.status_code == 200:
            print("Ping exitoso (REST API). Supabase activo.")
            print(f"Respuesta: {response.json()}")
        else:
            print(f"Error en request: {response.status_code} - {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"Error en keep-alive: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ping_supabase()
