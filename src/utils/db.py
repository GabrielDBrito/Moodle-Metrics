import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any
import time
import sys
from .paths import get_config_path


# Try multiple sensible locations for the env file so it works both when
# running from source (`src/db.env`) and when running from the project root
# (e.g. after packaging the executable).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env_candidates = [
    os.path.join(BASE_DIR, 'db.env'),           # project_root/db.env
    os.path.join(BASE_DIR, 'src', 'db.env'),    # project_root/src/db.env
    get_config_path('db.env'),                  # helper (keeps backward compatibility)
]
# Normalize and pick the first existing path, otherwise default to first candidate
_env_candidates = [os.path.abspath(p) for p in _env_candidates]
ENV_PATH = next((p for p in _env_candidates if os.path.exists(p)), _env_candidates[0])
# Force override to ensure values from the file are loaded into os.environ
load_dotenv(ENV_PATH, override=True)
_ENV_CANDIDATES = _env_candidates

def get_db_connection():
    """
    Establishes a connection with a specific timeout and SSL mode.
    """
    host = os.getenv("SUPABASE_DB_HOST")
    sslmode = os.getenv("SUPABASE_DB_SSLMODE", "require")
    
    if not host:
        tried = ', '.join(_ENV_CANDIDATES)
        raise ValueError(f"Database credentials not found. Checked env files: {tried}")

    return psycopg2.connect(
        host=host,
        dbname=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
        sslmode=sslmode,
        connect_timeout=10 
    )

def save_analytics_data_to_db(data: Dict[str, Any]):
    """
    Persists data using a single transaction. 
    Uses n_estudiantes_totales as the population metric.
    """
    
    # Ensure IDs are strings to match DB types
    data['id_tiempo'] = str(data['id_tiempo']) if data.get('id_tiempo') else None
    data['id_asignatura'] = str(data['id_asignatura'])
    data['id_profesor'] = str(data['id_profesor'])
    
    # SQL Queries for Dimensions
    sql_dim_time = """
        INSERT INTO dim_tiempo (id_tiempo, nombre_periodo, anio, trimestre) 
        VALUES (%(id_tiempo)s, %(nombre_periodo)s, %(anio)s, %(trimestre)s) 
        ON CONFLICT (id_tiempo) DO NOTHING;
    """
    sql_dim_professor = """
        INSERT INTO dim_profesor (id_profesor, nombre_profesor) 
        VALUES (%(id_profesor)s, %(nombre_profesor)s) 
        ON CONFLICT (id_profesor) DO UPDATE SET 
            nombre_profesor = EXCLUDED.nombre_profesor;
    """
    sql_dim_subject = """
        INSERT INTO dim_asignatura (id_asignatura, nombre_materia, departamento) 
        VALUES (%(id_asignatura)s, %(nombre_materia)s, %(departamento)s) 
        ON CONFLICT (id_asignatura) DO UPDATE SET 
            nombre_materia = EXCLUDED.nombre_materia, 
            departamento = EXCLUDED.departamento;
    """
    
    # SQL for Fact Table 
    sql_fact_course = """
        INSERT INTO hecho_experiencia_curso (
            id_curso, id_tiempo, id_asignatura, id_profesor,
            n_estudiantes_totales, -- UPDATED: n_estudiantes_procesados removed
            
            ind_1_1_cumplimiento, ind_1_1_num, ind_1_1_den,
            ind_1_2_aprobacion,   ind_1_2_num, ind_1_2_den,
            ind_1_3_nota_promedio, ind_1_3_num, ind_1_3_den,
            ind_1_3_nota_mediana, 
            ind_1_4_participacion, ind_1_4_num, ind_1_4_den,
            ind_1_5_finalizacion,  ind_1_5_num, ind_1_5_den,
            
            ind_2_1_metod_activa, ind_2_1_num, ind_2_1_den,
            ind_2_2_ratio_eval,   ind_2_2_num, ind_2_2_den,
            
            ind_3_1_excelencia,   ind_3_1_num, ind_3_1_den, 
            ind_3_2_feedback,     ind_3_2_num, ind_3_2_den,
            
            fecha_extraccion
        ) VALUES (
            %(id_curso)s, %(id_tiempo)s, %(id_asignatura)s, %(id_profesor)s,
            %(n_estudiantes_totales)s, -- UPDATED: Using the correct key
            
            %(ind_1_1_cumplimiento)s, %(ind_1_1_num)s, %(ind_1_1_den)s,
            %(ind_1_2_aprobacion)s,   %(ind_1_2_num)s, %(ind_1_2_den)s,
            %(ind_1_3_nota_promedio)s, %(ind_1_3_num)s, %(ind_1_3_den)s,
            %(ind_1_3_nota_mediana)s, 
            %(ind_1_4_participacion)s, %(ind_1_4_num)s, %(ind_1_4_den)s,
            %(ind_1_5_finalizacion)s,  %(ind_1_5_num)s, %(ind_1_5_den)s,
            
            %(ind_2_1_metod_activa)s, %(ind_2_1_num)s, %(ind_2_1_den)s,
            %(ind_2_2_ratio_eval)s,   %(ind_2_2_num)s, %(ind_2_2_den)s,
            
            %(ind_3_1_excelencia)s,   %(ind_3_1_num)s, %(ind_3_1_den)s,
            %(ind_3_2_feedback)s,     %(ind_3_2_num)s, %(ind_3_2_den)s,
            
            NOW()
        )
        ON CONFLICT (id_curso) DO UPDATE SET
            id_tiempo = EXCLUDED.id_tiempo,
            id_asignatura = EXCLUDED.id_asignatura,
            id_profesor = EXCLUDED.id_profesor,
            n_estudiantes_totales = EXCLUDED.n_estudiantes_totales, 
            
            ind_1_1_cumplimiento = EXCLUDED.ind_1_1_cumplimiento,
            ind_1_1_num = EXCLUDED.ind_1_1_num, ind_1_1_den = EXCLUDED.ind_1_1_den,
            
            ind_1_2_aprobacion = EXCLUDED.ind_1_2_aprobacion,
            ind_1_2_num = EXCLUDED.ind_1_2_num, ind_1_2_den = EXCLUDED.ind_1_2_den,
            
            ind_1_3_nota_promedio = EXCLUDED.ind_1_3_nota_promedio,
            ind_1_3_num = EXCLUDED.ind_1_3_num, ind_1_3_den = EXCLUDED.ind_1_3_den,
            ind_1_3_nota_mediana = EXCLUDED.ind_1_3_nota_mediana,
            
            
            ind_1_4_participacion = EXCLUDED.ind_1_4_participacion,
            ind_1_4_num = EXCLUDED.ind_1_4_num, ind_1_4_den = EXCLUDED.ind_1_4_den,
            
            ind_1_5_finalizacion = EXCLUDED.ind_1_5_finalizacion,
            ind_1_5_num = EXCLUDED.ind_1_5_num, ind_1_5_den = EXCLUDED.ind_1_5_den,
            
            ind_2_1_metod_activa = EXCLUDED.ind_2_1_metod_activa,
            ind_2_1_num = EXCLUDED.ind_2_1_num, ind_2_1_den = EXCLUDED.ind_2_1_den,
            
            ind_2_2_ratio_eval = EXCLUDED.ind_2_2_ratio_eval,
            ind_2_2_num = EXCLUDED.ind_2_2_num, ind_2_2_den = EXCLUDED.ind_2_2_den,
            
            ind_3_1_excelencia = EXCLUDED.ind_3_1_excelencia,
            ind_3_1_num = EXCLUDED.ind_3_1_num, ind_3_1_den = EXCLUDED.ind_3_1_den,
            
            ind_3_2_feedback = EXCLUDED.ind_3_2_feedback,
            ind_3_2_num = EXCLUDED.ind_3_2_num, ind_3_2_den = EXCLUDED.ind_3_2_den,
            
            fecha_extraccion = NOW();
    """

    # Retry logic for database locks
    for attempt in range(3):
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 15000;") 
                
                if data.get("id_tiempo"):
                    cur.execute(sql_dim_time, data)
                cur.execute(sql_dim_professor, data)
                cur.execute(sql_dim_subject, data)
                cur.execute(sql_fact_course, data)
            
            conn.commit()
            return 
        except Exception as e:
            if conn: conn.rollback()
            if "timeout" in str(e).lower() or "lock" in str(e).lower():
                time.sleep(1) 
                continue
            print(f"[DB ERROR] ID {data.get('id_curso')}: {e}")
            raise
        finally:
            if conn: conn.close()