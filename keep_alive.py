import os
import requests
import sys
import time
from datetime import datetime

# Configuración
MAX_RETRIES = 3
TIMEOUT = 15


def log(msg):
    """Formato de logs con timestamp"""
    print(f"[{datetime.utcnow()}] {msg}")


def make_request(url, headers, method="GET", payload=None):
    """Ejecuta request con manejo de errores"""
    try:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method == "PATCH":
            return requests.patch(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        log(f"Error de conexión: {e}")
        return None


def ping_supabase():
    try:
        # Variables de entorno
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            log("ERROR: Missing Supabase credentials.")
            sys.exit(1)

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        # Endpoint principal 
        read_endpoint = f"{supabase_url}/rest/v1/dim_tiempo?select=id_tiempo&limit=1"

        # Endpoint opcional 
        count_endpoint = f"{supabase_url}/rest/v1/dim_tiempo?select=count"

        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            log(f"Intento {attempt} - GET principal")

            response = make_request(read_endpoint, headers)

            if response and response.status_code == 200:
                log("Lectura exitosa (dim_tiempo)")
                log(f"Data: {response.json()}")
                success = True
                break
            else:
                log(f"Fallo en intento {attempt}: {response.status_code if response else 'No response'}")
                time.sleep(3)

        if not success:
            log("Fallaron todos los intentos de lectura")
            sys.exit(1)

        # Segundo request 
        log("Ejecutando segunda consulta (count)...")
        response2 = make_request(count_endpoint, headers)

        if response2 and response2.status_code == 200:
            log("Segunda consulta exitosa")
        else:
            log("egunda consulta falló (no crítico)")

        log("Keep-alive ejecutado correctamente.")

    except Exception as e:
        log(f"Error crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ping_supabase()
