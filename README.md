# -------------------- ENGLISH VERSION --------------------

# Course Experience Analytics in Moodle (ETL)

This project provides a robust ETL pipeline (Extract, Transform, Load) to analyze academic data from UNIMET's Virtual Classrooms in Moodle. The system extracts raw data, applies an administrative and temporal filtering system, calculates performance, design, and interaction indicators, and persists the results in a PostgreSQL database (Supabase) for analysis in Business Intelligence (BI) tools like Looker Studio.

The system is designed to be **idempotent, scalable, and sincere**, focusing on reflecting the administrative reality of the institution by analyzing finalized academic terms without artificial quality smoothing.

---

## Main Features

| Feature                 | Description                                                                                                   |
|-------------------------|---------------------------------------------------------------------------------------------------------------|
| **Graphical Interface (GUI)** | A modern desktop UI with configurable parameters, allowing easy execution by non-technical staff.         |
| **Temporal Availability**   | Guarantees data maturity by only processing academic terms after their official closing dates.              |
| **Sincere Analytics**       | KPIs are calculated based on the total administrative enrollment to reflect the true impact of inactivity.    |
| **Idempotent ETL**          | Allows re-running the process to update records using `UPSERT` logic, preventing data duplication.           |
| **Statistical Precision**   | Stores raw numerators and denominators to enable accurate weighted aggregations in BI tools and avoid "average of averages" errors. |

---

## Project Structure

- **`src/`**: Main directory for application source code.
  - **`app.py`**: Entry point for the Graphical User Interface (GUI).
  - **`etl_pipeline.py`**: Core ETL pipeline logic and process orchestration.
- **`api/`**: Modules that interact with the Moodle API.
  - `client.py`: Low-level client for Moodle API REST calls.
  - `services.py`: High-level orchestrator for course indicator calculations.
- **`indicators/`**: Modules for KPI calculation.
  - `group1_results.py`, `group2_design.py`, `group3_behavior.py`.
- **`utils/`**: Helper modules.
  - `db.py`: Connection and data persistence logic for PostgreSQL/Supabase.
  - `filters.py`: Centralized administrative filtering rules (Keywords, Codes, Departments).
  - `period_parser.py`: Maps courses to UNIMET academic periods and manages "Term Ready" logic.
  - `config_loader.py` & `paths.py`: Handles dynamic file paths for development and executable modes.
- **`build.py`**: PyInstaller script to compile the project into a standalone Windows executable.
- **`keep_alive.py`**: Script for GitHub Actions to prevent the Supabase database from pausing due to inactivity.

---

## Installation and Setup

### Prerequisites
- Python 3.9 or higher.
- Access to a PostgreSQL database (e.g., Supabase).

### Steps
1.  **Clone and Install:**
    ```bash
    git clone [repository-URL]
    cd Indicadores-Moodle
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Configure Environment:**
    - Create a `bdd.env` file in the root directory with your Supabase credentials.
    - Create a `config.ini` file in the root directory with your Moodle Token and API URL.

---

## Execution

The application is designed to be run through its graphical interface.

**Run the GUI:**
```bash
python src/app.py
```

**Usage:**
1.  **Execution Tab:** Select the desired date range for data extraction. Courses from academic terms that have not yet officially closed will be automatically skipped.
2.  **Parameters Tab:** Adjust the numerical thresholds for `Minimum Students`, `Excellence Score`, and `Active Density` to refine the analysis.
3.  **Monitoring:** The log console will display real-time progress and the status of each processed course (OK, SKIP, or ERROR).

---

## Indicator Matrix (KPIs)

### Group 1: Compliance and Results
- **1.1 Compliance**: Measures the volume of completed activities against the total expected for the entire enrolled student body.
- **1.2 Approval**: Proportion of students with a passing grade (≥ 9.5) out of the total enrolled.
- **1.3 Grade Statistics**: Mean, Median, and Standard Deviation of final grades, with heuristic normalization to correct inconsistent Moodle scales.
- **1.4 Participation**: Percentage of students who meet the parameterized activity threshold (default: 40% of tasks).
- **1.5 Compliance Distribution**: A count of students grouped by their activity completion percentage (0-25%, 25-50%, etc.).
- **1.6 Grade Distribution**: A count of students grouped by their final grade range (0-9, 10-15, 16-20).

### Group 2: Instructional Design
- **2.1 Active Methodology**: Ratio of interactive content (assignments, quizzes) versus static resources (files, links).
- **2.2 Evaluative Ratio**: Percentage of active modules that are linked to a grade in the gradebook.

### Group 3: Behavior and Interaction
- **3.1 Excellence**: Rate of outstanding performance (based on a parameterized threshold, default ≥ 18/20) across the total enrollment.
- **3.2 Feedback**: Percentage of graded activities that received qualitative feedback from the instructor.

---

## License
Academic project developed for a Thesis at Universidad Metropolitana (UNIMET). All rights reserved.

---
<br>

# -------------------- VERSIÓN EN ESPAÑOL --------------------

# Analítica de Experiencia de Cursos en Moodle (ETL)

Este proyecto provee un robusto pipeline ETL (Extracción, Transformación y Carga) para analizar los datos académicos de las Aulas Virtuales de la UNIMET. El sistema extrae datos crudos de Moodle, aplica un sistema de filtrado administrativo y temporal, calcula indicadores de rendimiento, diseño e interacción, y persiste los resultados en una base de datos PostgreSQL (Supabase) para su análisis en herramientas de BI como Looker Studio.

El sistema está diseñado para ser **idempotente, escalable y sincero**, enfocándose en reflejar la realidad administrativa de la institución al analizar únicamente períodos académicos culminados.

---

## Características Principales

| Característica | Descripción |
| :--- | :--- |
| **Interfaz Gráfica (GUI)** | UI de escritorio moderna con parámetros configurables, permitiendo una ejecución sencilla por personal no técnico. |
| **Disponibilidad Temporal** | Garantiza la madurez del dato procesando trimestres solo tras su fecha oficial de cierre. |
| **Analítica Sincera** | Los KPIs se calculan sobre la matrícula administrativa total para reflejar el impacto real de la inactividad. |
| **ETL Idempotente** | Permite re-ejecutar el proceso para actualizar datos mediante lógica `UPSERT`, sin riesgo de crear duplicados. |
| **Precisión Estadística** | Almacena numeradores y denominadores para que los dashboards realicen agregaciones ponderadas matemáticamente exactas. |

---

## Estructura del Proyecto

- **`src/`**: Directorio principal del código fuente.
  - **`app.py`**: Punto de entrada de la Interfaz Gráfica de Usuario (GUI).
  - **`etl_pipeline.py`**: Lógica central del pipeline y orquestación del proceso.
- **`api/`**: Módulos que interactúan con la API de Moodle.
  - `client.py`: Cliente de bajo nivel para las peticiones REST.
  - `services.py`: Orquestador de alto nivel para el cálculo de indicadores por curso.
- **`indicators/`**: Módulos de cálculo de los KPIs.
  - `group1_results.py`, `group2_design.py`, `group3_behavior.py`.
- **`utils/`**: Módulos de soporte.
  - `db.py`: Lógica de conexión y persistencia en PostgreSQL/Supabase.
  - `filters.py`: Reglas centralizadas de filtrado administrativo (Palabras Clave, Códigos, Departamentos).
  - `period_parser.py`: Mapeo de cursos a períodos académicos UNIMET y gestión de disponibilidad temporal.
  - `config_loader.py` & `paths.py`: Manejo de rutas de archivos para modo desarrollo y ejecutable.
- **`build.py`**: Script de PyInstaller para compilar el proyecto en un ejecutable de Windows.
- **`keep_alive.py`**: Script para GitHub Actions que evita la suspensión de la base de datos Supabase.

---

## Instalación y Configuración

### Requisitos Previos
- Python 3.9 o superior.
- Acceso a una base de datos PostgreSQL (ej. Supabase).

### Pasos
1.  **Clonar e Instalar:**
    ```bash
    git clone [URL-del-repositorio]
    cd Indicadores-Moodle
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Configurar Entorno:**
    - Crear un archivo `bdd.env` en la raíz del proyecto con las credenciales de Supabase.
    - Crear un archivo `config.ini` en la raíz del proyecto con el Token de Moodle y la URL de la API.

---

## Ejecución y Uso

La aplicación está diseñada para ser ejecutada a través de su interfaz gráfica.

**Lanzar la GUI:**
```bash
python src/app.py
```

**Uso de la Interfaz:**
1.  **Pestaña Ejecución:** Selecciona el rango de fechas para la extracción. Los cursos de trimestres que no hayan finalizado serán omitidos automáticamente. Haz clic en "INICIAR PROCESO".
2.  **Pestaña Parámetros:** Ajusta los umbrales numéricos para los filtros de `Mínimo de Estudiantes`, `Nota de Excelencia` y `Densidad Activa`.
3.  **Monitoreo:** La consola de logs mostrará el progreso en tiempo real y el estado de cada curso procesado (OK, OMITIR o ERROR).

---

## Matriz de Indicadores (KPIs)

### Grupo 1: Cumplimiento y Resultados
- **1.1 Cumplimiento**: Mide el volumen de actividades completadas respecto al total esperado para toda la matrícula inscrita.
- **1.2 Aprobación**: Proporción de estudiantes con nota aprobatoria (≥ 9.5) sobre el total de inscritos.
- **1.3 Estadística de Notas**: Media, Mediana y Desviación Estándar de las notas finales, con normalización heurística para corregir escalas inconsistentes de Moodle.
- **1.4 Participación**: Porcentaje de estudiantes que cumplen con el umbral de actividad parametrizado (por defecto, 40% de las tareas).
- **1.5 Distribución de Cumplimiento**: Conteo de estudiantes agrupados por su porcentaje de completitud de tareas (0-25%, 25-50%, etc.).
- **1.6 Distribución de Notas**: Conteo de estudiantes agrupados por su rango de nota final (0-9, 10-15, 16-20).

### Grupo 2: Diseño Instruccional
- **2.1 Metodología Activa**: Proporción de contenido interactivo (tareas, quices) frente a recursos estáticos (PDFs, enlaces).
- **2.2 Ratio Evaluativo**: Porcentaje de las actividades activas que están vinculadas a una calificación en el libro de notas.

### Grupo 3: Comportamiento e Interacción
- **3.1 Excelencia**: Tasa de desempeño sobresaliente (según umbral parametrizable, por defecto ≥ 18/20) sobre la matrícula total.
- **3.2 Feedback**: Porcentaje de actividades calificadas que recibieron retroalimentación cualitativa del docente.

---

## Licencia
Proyecto académico desarrollado para un Trabajo de Grado en la Universidad Metropolitana (UNIMET). Todos los derechos reservados.