# -------------------- ENGLISH VERSION --------------------

# Course Experience Analytics in Moodle (ETL)

This project provides a robust ETL pipeline (Extract, Transform, Load) to analyze academic data from UNIMET's Virtual Classrooms in Moodle. The system extracts raw data, applies an administrative and temporal filtering system, calculates performance and design indicators, and persists the results in a PostgreSQL database (Supabase) for analysis in Business Intelligence (BI) tools like Looker Studio.

The system is designed to be **idempotent, scalable, and sincere**, focusing on reflecting the administrative reality of the institution by analyzing finalized terms without artificial quality smoothing.

---

## Main Features

| Feature                  | Description                                                                                  |
|--------------------------|----------------------------------------------------------------------------------------------|
| Graphical Interface (GUI)| Modern desktop interface for easy execution by non-technical staff.                          |
| Temporal Availability    | Ensures data maturity by only processing terms after their official closing dates.            |
| Sincere Analytics        | KPIs are calculated based on total administrative enrollment to reflect the impact of inactivity.|
| Idempotent ETL           | Allows re-running the process to update records using `UPSERT` logic without duplicates.      |
| Statistical Precision    | Stores numerators and denominators to enable accurate weighted aggregations in BI.            |

---

## Project Structure

- **src/**: Main directory for application source code.
  - **app.py**: Entry point for the Graphical User Interface (GUI).
  - **etl_pipeline.py**: Core ETL pipeline logic and process orchestration.
- **api/**:
  - **client.py**: Low-level client for Moodle API REST calls.
  - **services.py**: High-level orchestrator for course indicator calculations.
- **indicators/**:
  - **group1_results.py, group2_design.py, group3_behavior.py**: Modules for KPI calculation.
- **utils/**:
  - **db.py**: Connection and data persistence in PostgreSQL/Supabase.
  - **filters.py**: Centralized administrative filtering rules (Keywords, Codes, Departments).
  - **period_parser.py**: Maps courses to academic periods and manages the "Term Ready" logic.
  - **config_loader.py & paths.py**: Handles dynamic file paths for development and .exe modes.
- **build.py**: PyInstaller script to compile the project into a Windows standalone executable.
- **keep_alive.py**: Script for GitHub Actions to maintain the Supabase database active.

---

## Installation and Setup

### Prerequisites
- Python 3.9 or higher.
- Access to a PostgreSQL database (Supabase).

### Step 1. Clone and Install
**git clone [repository-URL]**
**cd Indicadores-Moodle**
**python -m venv venv**
**venv\Scripts\activate** (On Windows)
**pip install -r requirements.txt**

### Step 2. Configure Environment
- Create a `bdd.env` file in the root with your Supabase credentials:
  **SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD**
- Create a `config.ini` file in the root with your Moodle Token and API URL.

---

## Execution

**Graphical Interface (Recommended):**
**python src/app.py**

**Command Line:**
**python src/etl_pipeline.py**

---

## Business Rules (Filters)

To ensure data integrity, the system applies three layers of filtering:
1.  **Administrative:** Excludes courses based on keywords (e.g., "PRUEBA", "SANDPIT") and specific departments (e.g., "Teaching Center", "Postgrado").
2.  **Temporal Maturity:** Only processes data from finalized terms. Data becomes available in **December (T1), April (T2), July (T3), and September (Intensive)**.
3.  **Population:** Minimum of **5 enrolled students** required to be considered for institutional analysis and to protect student privacy.

---

## Indicator Matrix (KPIs)

- **1.1 Compliance**: Percentage of activities completed relative to the total administrative enrollment.
- **1.2 Approval**: Proportion of students with a passing grade (≥ 9.5) over the total enrollment.
- **1.3 Grade Statistics**: Mean, Median, and StDev of final grades (Normalization applied to correct Moodle scale inconsistencies).
- **1.4 Participation**: Percentage of enrolled students showing any activity in the course.
- **1.5 Completion**: Percentage of students who completed >70% of significant tasks (items < 5% weight are excluded).
- **2.1 Active Methodology**: Ratio of interactive content vs. static resources.
- **3.1 Excellence**: Rate of outstanding performance (grades ≥ 18/20) over total enrollment.
- **3.2 Feedback**: Percentage of graded items that received qualitative instructor feedback.

---

## License
Academic project for a Thesis at Universidad Metropolitana (UNIMET). All rights reserved.

---
<br>

# -------------------- SPANISH VERSION --------------------

# Analítica de Experiencia de Cursos en Moodle (ETL)

Este proyecto provee un robusto pipeline ETL (Extracción, Transformación y Carga) para analizar los datos académicos de las Aulas Virtuales de la UNIMET en Moodle. El sistema extrae datos crudos, aplica un sistema de filtrado administrativo y temporal, calcula indicadores de rendimiento y diseño, y persiste los resultados en una base de datos PostgreSQL (Supabase) para su análisis en herramientas de BI como Looker Studio.

El sistema está diseñado para ser **idempotente, escalable y sincero**, enfocándose en reflejar la realidad administrativa de la institución al analizar periodos culminados sin maquillajes estadísticos.

---

## Características Principales

| Característica           | Descripción                                                                                  |
|--------------------------|----------------------------------------------------------------------------------------------|
| Interfaz Gráfica (GUI)   | UI moderna de escritorio para una ejecución sencilla por personal no técnico.                |
| Disponibilidad Temporal  | Garantiza la madurez del dato procesando trimestres solo tras su fecha oficial de cierre.    |
| Analítica Sincera        | KPIs calculados sobre la matrícula administrativa total para reflejar el impacto de la inactividad.|
| ETL Idempotente          | Permite re-ejecutar el proceso para actualizar datos mediante lógica `UPSERT` sin duplicados. |
| Precisión Estadística    | Almacena numeradores y denominadores para evitar el "promedio de promedios" en el Dashboard.  |

---

## Estructura del Proyecto

- **src/**: Directorio principal del código fuente.
  - **app.py**: Punto de entrada de la Interfaz Gráfica (GUI).
  - **etl_pipeline.py**: Lógica central del pipeline y orquestación.
- **api/**:
  - **client.py**: Cliente de bajo nivel para llamadas a la API REST de Moodle.
  - **services.py**: Orquestador de alto nivel para el cálculo de indicadores.
- **indicators/**:
  - **group1_results.py, group2_design.py, group3_behavior.py**: Módulos de cálculo de KPIs.
- **utils/**:
  - **db.py**: Conexión y persistencia en PostgreSQL/Supabase.
  - **filters.py**: Reglas centralizadas de filtrado administrativo (Palabras clave, Códigos, Departamentos).
  - **period_parser.py**: Mapeo de cursos a períodos UNIMET y gestión de disponibilidad temporal.
  - **config_loader.py & paths.py**: Manejo de rutas para modo desarrollo y ejecutable .exe.
- **build.py**: Script para compilar el proyecto en un ejecutable Windows independiente.
- **keep_alive.py**: Script para GitHub Actions que evita la suspensión de la base de datos Supabase.

---

## Instalación y Configuración

### Requisitos Previos
- Python 3.9 o superior.
- Acceso a una base de datos PostgreSQL (Supabase).

### Paso 1. Clonar e Instalar
**git clone [URL-del-repositorio]**
**cd Indicadores-Moodle**
**python -m venv venv**
**venv\Scripts\activate** (En Windows)
**pip install -r requirements.txt**

### Paso 2. Configurar Entorno
- Crear archivo `bdd.env` en la raíz con las credenciales de Supabase:
  **SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD**
- Crear archivo `config.ini` en la raíz con el Token de Moodle y la URL de la API.

---

## Ejecución

**Interfaz Gráfica (Recomendado):**
**python src/app.py**

**Línea de Comandos:**
**python src/etl_pipeline.py**

---

## Reglas de Negocio (Filtros)

Para garantizar la integridad del análisis, el sistema aplica tres capas de filtrado:
1.  **Administrativo:** Excluye cursos por palabras clave (ej. "PRUEBA", "SANDPIT") y departamentos ajenos (ej. "Teaching Center", "Postgrado").
2.  **Madurez Temporal:** Solo se procesan periodos finalizados. Los datos están disponibles a partir de: **Diciembre (T1), Abril (T2), Julio (T3) y Septiembre (Intensivo)**.
3.  **Población:** Mínimo de **5 estudiantes inscritos** para asegurar representatividad y proteger la privacidad estudiantil.

---

## Matriz de Indicadores (KPIs)

- **1.1 Cumplimiento**: Porcentaje de actividades completadas respecto a la matrícula administrativa total.
- **1.2 Aprobación**: Proporción de estudiantes con nota aprobatoria (≥ 9.5) sobre el total de inscritos.
- **1.3 Estadística de Notas**: Media, Mediana y Desviación Estándar (Normalización aplicada para corregir escalas de Moodle inconsistentes).
- **1.4 Participación**: Porcentaje de estudiantes inscritos que demuestran actividad real en el curso.
- **1.5 Finalización**: Porcentaje de estudiantes que completaron >70% de las tareas significativas (se ignoran ítems con peso <5%).
- **2.1 Metodología Activa**: Proporción de contenido interactivo frente a recursos estáticos.
- **3.1 Excelencia**: Tasa de desempeño sobresaliente (notas ≥ 18/20) sobre la matrícula total.
- **3.2 Feedback**: Porcentaje de actividades calificadas que recibieron retroalimentación del docente.

---

## Licencia
Proyecto académico desarrollado para un Trabajo de Grado en la Universidad Metropolitana (UNIMET). Todos los derechos reservados.