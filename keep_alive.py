import os
import psycopg2

def ping_database():
    try:
        connection = psycopg2.connect(
            host=os.environ.get("SUPABASE_DB_HOST"),
            port=os.environ.get("SUPABASE_DB_PORT"),
            database=os.environ.get("SUPABASE_DB_NAME"),
            user=os.environ.get("SUPABASE_DB_USER"),
            password=os.environ.get("SUPABASE_DB_PASSWORD"),
            sslmode='require'
        )

        cursor = connection.cursor()
        
        # Simple query to test connectivity and response
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        
        print(f"Ping exitoso. La base de datos respondió: {result[0]}")
        
        cursor.close()
        connection.close()

    except Exception as e:
        print(f"Error al enviar el latido: {e}")
        # If it fails, we'll make the Action fail so you receive an email
        exit(1)

if __name__ == "__main__":
    ping_database()