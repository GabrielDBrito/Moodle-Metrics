# db.py (versión refactorizada y unificada)

import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# --- Carga de variables de entorno ---
# (Esta parte se mantiene igual)
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR /"bdd.env"
load_dotenv(ENV_PATH)

DB_HOST = os.getenv("SUPABASE_DB_HOST")
DB_NAME = os.getenv("SUPABASE_DB_NAME")
DB_USER = os.getenv("SUPABASE_DB_USER")
DB_PASS = os.getenv("SUPABASE_DB_PASSWORD")
DB_PORT = os.getenv("SUPABASE_DB_PORT")

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        sslmode="require"
    )

def save_analytics_data_to_db(data: dict):
    """
    Guarda todos los datos de un curso en la base de datos de forma transaccional.
    Utiliza la lógica UPSERT para insertar nuevos registros o actualizar los existentes.
    """
    
    # --- Consultas SQL con la cláusula ON CONFLICT DO UPDATE ---
    
    # "DO NOTHING" es eficiente para dimensiones que no cambian.
    sql_dim_tiempo = """
        INSERT INTO dim_tiempo_test (id_tiempo, nombre_periodo, anio, trimestre)
        VALUES (%(id_tiempo)s, %(nombre_periodo)s, %(anio)s, %(trimestre)s)
        ON CONFLICT (id_tiempo) DO NOTHING;
    """
    
    # "DO UPDATE" para dimensiones que podrían cambiar (ej. nombre del profesor).
    sql_dim_profesor = """
        INSERT INTO dim_profesor_test (id_profesor, nombre_profesor)
        VALUES (%(id_profesor)s, %(nombre_profesor)s)
        ON CONFLICT (id_profesor) DO UPDATE SET
            nombre_profesor = EXCLUDED.nombre_profesor;
    """

    sql_dim_asignatura = """
        INSERT INTO dim_asignatura_test (id_asignatura, nombre_materia, departamento)
        VALUES (%(id_asignatura)s, %(nombre_materia)s, %(departamento)s)
        ON CONFLICT (id_asignatura) DO UPDATE SET
            nombre_materia = EXCLUDED.nombre_materia,
            departamento = EXCLUDED.departamento;
    """
    
    # La tabla de hechos siempre se actualiza con los últimos cálculos.
    sql_hechos_curso = """
        INSERT INTO hecho_experiencia_curso_test (
            id_curso, id_tiempo, id_asignatura, id_profesor,
            ind_1_1_cumplimiento, ind_1_2_aprobacion, ind_1_3_nota_promedio,
            ind_1_3_nota_mediana, ind_1_3_nota_desviacion, ind_1_4_participacion,
            ind_1_5_finalizacion, ind_2_1_metod_activa, ind_2_2_ratio_eval,
            ind_3_1_selectividad, ind_3_2_feedback
        ) VALUES (
            %(id_curso)s, %(id_tiempo)s, %(id_asignatura)s, %(id_profesor)s,
            %(ind_1_1_cumplimiento)s, %(ind_1_2_aprobacion)s, %(ind_1_3_nota_promedio)s,
            %(ind_1_3_nota_mediana)s, %(ind_1_3_nota_desviacion)s, %(ind_1_4_participacion)s,
            %(ind_1_5_finalizacion)s, %(ind_2_1_metod_activa)s, %(ind_2_2_ratio_eval)s,
            %(ind_3_1_selectividad)s, %(ind_3_2_feedback)s
        )
        ON CONFLICT (id_curso) DO UPDATE SET
            id_tiempo = EXCLUDED.id_tiempo,
            id_asignatura = EXCLUDED.id_asignatura,
            id_profesor = EXCLUDED.id_profesor,
            ind_1_1_cumplimiento = EXCLUDED.ind_1_1_cumplimiento,
            ind_1_2_aprobacion = EXCLUDED.ind_1_2_aprobacion,
            ind_1_3_nota_promedio = EXCLUDED.ind_1_3_nota_promedio,
            ind_1_3_nota_mediana = EXCLUDED.ind_1_3_nota_mediana,
            ind_1_3_nota_desviacion = EXCLUDED.ind_1_3_nota_desviacion,
            ind_1_4_participacion = EXCLUDED.ind_1_4_participacion,
            ind_1_5_finalizacion = EXCLUDED.ind_1_5_finalizacion,
            ind_2_1_metod_activa = EXCLUDED.ind_2_1_metod_activa,
            ind_2_2_ratio_eval = EXCLUDED.ind_2_2_ratio_eval,
            ind_3_1_selectividad = EXCLUDED.ind_3_1_selectividad,
            ind_3_2_feedback = EXCLUDED.ind_3_2_feedback;
    """

    conn = None
    try:
        # 1. Abrir UNA SOLA conexión
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. Ejecutar todas las consultas dentro de la misma transacción
            if data.get("id_tiempo"):
                cur.execute(sql_dim_tiempo, data)
            
            cur.execute(sql_dim_profesor, data)
            cur.execute(sql_dim_asignatura, data)
            cur.execute(sql_hechos_curso, data)
        
        # 3. Si todo va bien, confirmar los cambios
        conn.commit()
    except Exception as e:
        # 4. Si algo falla, revertir todo
        if conn:
            conn.rollback()
        print(f"[ERROR DB] Falla en transacción para el curso {data.get('id_curso')}: {e}")
        # Re-lanzar la excepción para que el worker principal la capture como un error
        raise
    finally:
        # 5. Cerrar la conexión
        if conn:
            conn.close()