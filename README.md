# -------------------- ENGLISH VERSION --------------------

# Course Experience Analytics in Moodle (ETL)

This project provides a robust ETL pipeline (Extract, Transform, Load) to analyze academic data from UNIMET's Virtual Classrooms in Moodle. The system extracts raw data, applies a multi-layer quality filtering system, calculates performance and design indicators, and persists the results in a PostgreSQL database (Supabase) for analysis in Business Intelligence (BI) tools like Looker Studio.

The system is designed to be idempotent, scalable, and resilient, handling common issues in academic data such as inconsistent grading scales, incomplete course structures, and administrative noise.

---

## Main Features

| Feature                  | Description                                                                                  |
|--------------------------|----------------------------------------------------------------------------------------------|
| Graphical Interface (GUI)| Modern graphical interface for easy execution by non-technical staff.                        |
| Intelligent Filtering    | Multi-layer system ensuring data quality (Maturity, Hierarchy, Integrity).                   |
| Idempotent ETL           | Allows re-running the process to update data without creating duplicates.                    |
| Scalable Architecture    | Decoupled logic (Engine vs. UI), centralized filters, and multithreaded processing.          |
| Statistical Precision    | Stores numerators and denominators to avoid the "average of averages" problem in Looker Studio.|

---

## Project Structure

- **src/**: Main directory for application source code.
  - **app.py**: Entry point for the Graphical User Interface (GUI).
  - **etl_pipeline.py**: Core ETL pipeline logic and process orchestration.
- **api/**:
  - **client.py**: Low-level client for API calls.
  - **services.py**: High-level orchestrator for course indicator calculations.
- **indicators/**:
  - **group1_results.py, group2_design.py, group3_behavior.py**: Modules for each indicator group calculation.
- **utils/**:
  - **db.py**: Connection and data persistence in PostgreSQL/Supabase.
  - **filters.py**: Centralized logic for all course quality filtering rules.
  - **period_parser.py**: Maps courses to UNIMET academic periods.
  - **config_loader.py & paths.py**: Handles file paths for development and executable modes.
- **build.py**: PyInstaller script to compile the project into a Windows executable (.exe).
- **keep_alive.py**: GitHub Actions script to prevent Supabase database from entering sleep mode.
- **config.ini**: Configuration file for Moodle API token and date filters.
- **bdd.env**: Environment variables for secure database credentials.

---

## Installation and Setup

### Prerequisites

- Python 3.9 or higher.
- Access to a PostgreSQL database (such as Supabase).

### Step 1. Clone the repository

```shell
git clone [repository-URL]
cd Indicadores-Moodle
```

### Step 2. Create a virtual environment

```shell
python -m venv venv
venv\Scripts\activate  # On Windows
```

### Step 3. Install dependencies

```shell
pip install -r requirements.txt
```

### Step 4. Configure the environment

- Create a `bdd.env` file in the root and fill it with your real Supabase credentials:
    ```env
    # bdd.env
    SUPABASE_DB_HOST=example credentials
    SUPABASE_DB_PORT=example credentials
    SUPABASE_DB_NAME=example credentials
    SUPABASE_DB_USER=example credentials
    SUPABASE_DB_PASSWORD=example credentials
    ```

- Create a `config.ini` file in the root to include your Moodle API token:
    ```ini
    # config.ini
    [MOODLE]
    token = example token
    url = example url API REST Endpoint

    [FILTERS]
    start_date = example date
    end_date = example date
    ```

---

## How to Run the Tool

### With Graphical Interface (Recommended for end users)

This is the main entry point to run the process visually and configure dates:

```shell
python src/app.py
```

### Command Line (For debugging or server use)

Run the ETL pipeline directly using the dates saved in `config.ini`:

```shell
python src/etl_pipeline.py
```

---

## Create the Executable (.exe)

To create a Windows executable for distribution (no need to install Python or use the console):

1. Make sure the library is installed:

    ```shell
    pip install pyinstaller
    ```

2. Run the build script from the project root:

    ```shell
    python build.py
    ```

The executable will be generated in the `dist/` folder. For proper operation on another computer, the `.exe` file must be in the same folder along with `config.ini` and `bdd.env`.

---

## Indicator Matrix (KPIs)

- **1.1 Compliance**: Percentage of activities completed by active students.
- **1.2 Approval**: Proportion of students with a passing final grade (≥ 9.5).
- **1.3 Grade Statistics**: Mean, Median, and Standard Deviation of final grades on a 0-20 scale.
- **1.4 Participation**: Percentage of enrolled students (total enrollment) showing activity in the course.
- **1.5 Completion**: Percentage of students who completed most of the significant evaluative workload (>70%).
- **2.1 Active Methodology**: Ratio of interactive content vs. passive/static content.
- **2.2 Evaluative Ratio**: Balance between graded active tasks and merely formative activities.
- **3.1 Excellence**: Rate of outstanding performance (grades ≥ 90%) over total graded activities.
- **3.2 Feedback**: Percentage of graded activities that received qualitative feedback from the instructor.

---

## License

This is an academic project developed for a Thesis. All rights reserved for internal research purposes at Universidad Metropolitana (UNIMET).

---


# -------------------- SPANISH VERSION --------------------

# Analítica de Experiencia de Cursos en Moodle (ETL)

Este proyecto provee un robusto pipeline ETL (Extracción, Transformación y Carga) para analizar los datos académicos de las Aulas Virtuales de la UNIMET en Moodle. El sistema extrae datos crudos, aplica un sistema de filtrado de calidad multicapa, calcula indicadores de rendimiento y diseño, y persiste los resultados en una base de datos PostgreSQL (Supabase) para su análisis en herramientas de Business Intelligence (BI) como Looker Studio.

El sistema está diseñado para ser idempotente, escalable y resiliente, manejando problemas comunes en data académica como escalas de calificación inconsistentes, estructuras de curso incompletas y ruido administrativo.

---

## Características Principales

| Característica           | Descripción                                                                                  |
|--------------------------|----------------------------------------------------------------------------------------------|
| Interfaz Gráfica (GUI)   | Interfaz gráfica para una ejecución sencilla por parte del personal no técnico. |
| Filtrado Inteligente     | Sistema multicapa que asegura la calidad de los datos (Madurez, Jerarquía, Integridad).      |
| ETL Idempotente          | Permite re-ejecutar el proceso para actualizar datos sin crear duplicados.           |
| Arquitectura Escalable   | Lógica desacoplada (Motor vs. UI), filtros centralizados y procesamiento multihilo.          |
| Precisión Estadística    | Almacena numeradores y denominadores para evitar el problema de "promedio de promedios" en Looker Studio. |

---

## Estructura del Proyecto

- **src/**: Directorio principal del código fuente de la aplicación.
  - **app.py**: Punto de entrada de la Interfaz Gráfica de Usuario (GUI).
  - **etl_pipeline.py**: Lógica central del pipeline ETL y orquestación del proceso.
- **api/**:
  - **client.py**: Cliente de bajo nivel para las llamadas a la API.
  - **services.py**: Orquestador de alto nivel para el cálculo de indicadores por curso.
- **indicators/**:
  - **group1_results.py, group2_design.py, group3_behavior.py**: Módulos para los cálculos de cada grupo de indicadores.
- **utils/**:
  - **db.py**: Conexión y persistencia de datos en PostgreSQL/Supabase.
  - **filters.py**: Lógica centralizada de todas las reglas para el filtrado de calidad de los cursos.
  - **period_parser.py**: Lógica para mapear cursos a los períodos académicos de la UNIMET.
  - **config_loader.py & paths.py**: Manejo de rutas de archivos para modo desarrollo y ejecutable.
- **build.py**: Script de PyInstaller para compilar el proyecto en un ejecutable Windows (.exe).
- **keep_alive.py**: Script para GitHub Actions que previene que la base de datos de Supabase entre en modo de suspensión.
- **config.ini**: Archivo de configuración para el token de la API de Moodle y los filtros de fecha.
- **bdd.env**: Variables de entorno para las credenciales seguras de la base de datos.

---

## Instalación y Configuración

### Requisitos Previos

- Python 3.9 o superior.
- Acceso a una base de datos PostgreSQL (como Supabase).

### Paso 1. Clonar el repositorio

```shell
git clone [URL-del-repositorio]
cd Indicadores-Moodle
```

### Paso 2. Crear un entorno virtual

```shell
python -m venv venv
venv\Scripts\activate  # En Windows
```

### Paso 3. Instalar dependencias

```shell
pip install -r requirements.txt
```

### Paso 4. Configurar el entorno

- Crear en la raiz archivo `bdd.env` y rellenar con las credenciales reales de Supabase:
    ```env
    #bdd.env 
    SUPABASE_DB_HOST=credenciales de ejemplo
    SUPABASE_DB_PORT=credenciales de ejemplo
    SUPABASE_DB_NAME=credenciales de ejemplo
    SUPABASE_DB_USER=credenciales de ejemplo
    SUPABASE_DB_PASSWORD=credenciales de ejemplo
    ```

- Crear en la raiz archivo `config.ini` para incluir tu token de la API de Moodle:
    ```ini
    #config.ini
    [MOODLE]
    token = token de ejemplo
    url = url de Endpoint de la API REST de ejemplo

    [FILTERS]
    start_date = fecha de ejemplo
    end_date = fecha de ejemplo
    ```

---

## Cómo Ejecutar la Herramienta

### Con Interfaz Gráfica (Recomendado para usuarios finales)

Este es el punto de entrada principal para ejecutar el proceso de forma visual y configurar las fechas:

```shell
python src/app.py
```

### Por Línea de Comandos (Para depuración o uso en servidores)

Ejecuta el pipeline de ETL directamente utilizando las fechas guardadas en el archivo `config.ini`:

```shell
python src/etl_pipeline.py
```

---

## Crear el Ejecutable (.exe)

Para crear un archivo ejecutable para distribución en Windows (que no requiere instalar Python ni usar la consola):

1. Asegurarse de tener la librería instalada:

    ```shell
    pip install pyinstaller
    ```

2. Ejecutar el script de construcción desde la raíz del proyecto:

    ```shell
    python build.py
    ```

El ejecutable se generará en la carpeta `dist/`. Para que funcione correctamente en otra computadora, el archivo `.exe` debe estar en la misma carpeta junto con los archivos `config.ini` y `bdd.env`.

---

## Matriz de Indicadores (KPIs)

- **1.1 Cumplimiento**: Porcentaje de actividades completadas por los estudiantes activos.
- **1.2 Aprobación**: Proporción de estudiantes con nota final aprobatoria (≥ 9.5).
- **1.3 Estadística de Notas**: Media, Mediana y Desviación Estándar de las notas finales en escala 0-20.
- **1.4 Participación**: Porcentaje de estudiantes inscritos (matrícula total) que demuestran actividad en el curso.
- **1.5 Finalización**: Porcentaje de estudiantes que completaron la mayoría de la carga evaluativa significativa (>70%).
- **2.1 Metodología Activa**: Proporción de contenido interactivo vs. contenido pasivo o estático.
- **2.2 Ratio Evaluativo**: Balance entre tareas activas calificadas y actividades meramente formativas.
- **3.1 Excelencia**: Tasa de desempeño sobresaliente (notas ≥ 90%) sobre el total de actividades calificadas.
- **3.2 Feedback**: Porcentaje de actividades calificadas que recibieron retroalimentación cualitativa del docente.

---

## Licencia

Este es un proyecto académico desarrollado para un Trabajo de Grado. Todos los derechos están reservados para fines de investigación interna en la Universidad Metropolitana (UNIMET).