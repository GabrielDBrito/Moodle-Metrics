import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# Cargar variables de entorno desde archivo .env
BASE_DIR = Path(__file__).resolve().parents[2]  # Ajusta según tu estructura
ENV_PATH = BASE_DIR / "src" / "db.env"
load_dotenv(ENV_PATH)

DB_HOST = os.getenv("SUPABASE_DB_HOST")
DB_NAME = os.getenv("SUPABASE_DB_NAME")
DB_USER = os.getenv("SUPABASE_DB_USER")
DB_PASS = os.getenv("SUPABASE_DB_PASSWORD")
DB_PORT = os.getenv("SUPABASE_DB_PORT")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        sslmode="require"
    )

def to_unix_timestamp(value):
    if value is None:
        raise ValueError("Fecha no puede ser None")
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return int(dt.timestamp())
        except ValueError:
            pass
    raise ValueError(f"Formato de fecha no soportado: {value}")

def insert_dim_tiempo(d: dict):
    sql = """
    INSERT INTO dim_tiempo (
        id_tiempo,
        nombre_periodo,
        anio,
        trimestre
    )
    VALUES (
        %(id_tiempo)s,
        %(nombre_periodo)s,
        %(anio)s,
        %(trimestre)s
    )
    ON CONFLICT (id_tiempo) DO UPDATE SET
        nombre_periodo = EXCLUDED.nombre_periodo,
        anio = EXCLUDED.anio,
        trimestre = EXCLUDED.trimestre;
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, d)
        conn.commit()
    except Exception as e:
        print(f"[ERROR DB] Error insertando dim_tiempo {d.get('id_tiempo')}: {e}")
    finally:
        if conn:
            conn.close()

def insert_dim_asignatura(d: dict):
    sql = """
    INSERT INTO dim_asignatura (
        id_asignatura,
        nombre_materia,
        departamento
    )
    VALUES (
        %(id_asignatura)s,
        %(nombre_materia)s,
        %(departamento)s
    )
    ON CONFLICT (id_asignatura) DO UPDATE SET
        nombre_materia = EXCLUDED.nombre_materia,
        departamento = EXCLUDED.departamento;
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, d)
        conn.commit()
    except Exception as e:
        print(f"[ERROR DB] Error insertando dim_asignatura {d.get('id_asignatura')}: {e}")
    finally:
        if conn:
            conn.close()

def insert_course_data(d: dict):
    sql = """
    INSERT INTO hecho_experiencia_curso (
        id_curso,
        id_tiempo,
        id_asignatura,
        id_profesor,


        ind_1_1_cumplimiento,
        ind_1_2_aprobacion,
        ind_1_3_nota_promedio,
        ind_1_3_nota_mediana,
        ind_1_3_nota_desviacion,
        ind_1_4_participacion,
        ind_1_5_finalizacion,

        ind_2_1_metod_activa,
        ind_2_2_ratio_eval,

        ind_3_1_selectividad,

        ind_3_2_feedback
    )
    VALUES (
        %(id_curso)s,
        %(id_tiempo)s,
        %(id_asignatura)s,
        %(id_profesor)s,

        %(ind_1_1_cumplimiento)s,
        %(ind_1_2_aprobacion)s,
        %(ind_1_3_nota_promedio)s,
        %(ind_1_3_nota_mediana)s,
        %(ind_1_3_nota_desviacion)s,
        %(ind_1_4_participacion)s,
        %(ind_1_5_finalizacion)s,

        %(ind_2_1_metod_activa)s,
        %(ind_2_2_ratio_eval)s,

        %(ind_3_1_selectividad)s,

        %(ind_3_2_feedback)s
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
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, d)
        conn.commit()
    except Exception as e:
        print(f"[ERROR DB] Error insertando curso {d.get('id_curso')}: {e}")
    finally:
        if conn:
            conn.close()
def insert_dim_profesor(d: dict):
    sql = """
    INSERT INTO dim_profesor (
        id_profesor,
        nombre_profesor
    )
    VALUES (
        %(id_profesor)s,
        %(nombre_profesor)s
    )
    ON CONFLICT (id_profesor) DO UPDATE SET
        nombre_profesor = EXCLUDED.nombre_profesor;
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, d)
        conn.commit()
    except Exception as e:
        print(f"[ERROR DB] Error insertando dim_profesor {d.get('id_profesor')}: {e}")
    finally:
        if conn:
            conn.close()
