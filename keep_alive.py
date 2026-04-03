import os
import psycopg2

def ping_database():
    """
    Connects to the Supabase PostgreSQL database and performs a lightweight 
    read operation to prevent the project from being paused due to inactivity.
    """
    try:
        # Fetch credentials from environment variables (provided by GitHub Actions)
        db_host = os.environ.get("SUPABASE_DB_HOST")
        db_port = os.environ.get("SUPABASE_DB_PORT")
        db_name = os.environ.get("SUPABASE_DB_NAME")
        db_user = os.environ.get("SUPABASE_DB_USER")
        db_pass = os.environ.get("SUPABASE_DB_PASSWORD")

        # Validate that all required secrets are loaded
        if not all([db_host, db_port, db_name, db_user, db_pass]):
            print("ERROR CRÍTICO: Faltan credenciales de la base de datos en GitHub Secrets.")
            exit(1)

        print(f"Intentando conectar al host: {db_host}...")

        # Establish connection with SSL required for Supabase
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass,
            sslmode='require',
            connect_timeout=20
        )

        cursor = connection.cursor()
        
        # Querying an actual table ensures Supabase registers this as real storage/compute activity.
        print("Ejecutando consulta de lectura en la tabla 'dim_tiempo'...")
        cursor.execute("SELECT id_tiempo FROM dim_tiempo LIMIT 1;")
        
        result = cursor.fetchone()
        
        if result:
            print(f"Ping exitoso. Registro detectado: {result[0]}")
        else:
            print("Ping exitoso. Conexión establecida (la tabla dim_tiempo está vacía).")
            
        # Clean up connections
        cursor.close()
        connection.close()
        print("Conexión cerrada correctamente.")

    except Exception as e:
        print(f"Error al enviar el latido a la base de datos: {e}")
        # Force exit code 1 to make the GitHub Action fail and send you an email alert
        exit(1)

if __name__ == "__main__":
    ping_database()
