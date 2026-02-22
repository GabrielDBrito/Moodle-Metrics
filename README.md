# Indicadores-Moodle
# Proyecto de Análisis de Experiencia de Cursos

Este sistema procesa datos académicos de estudiantes y cursos desde Moodle para generar indicadores de desempeño, participación y calidad educativa. El objetivo principal es analizar cómo el diseño de los contenidos influye en las notas finales y el éxito académico.

---

## Estructura del Proyecto

Aquí se listan las páginas/archivos principales del proyecto y su función.

- **src/main.py**: Pipeline ETL principal. Orquesta la descarga de metadatos y catálogo de cursos, aplica filtros, delega el cálculo de indicadores para cada curso y persiste los resultados en la base de datos.
- **src/gui.py**: Interfaz de escritorio (CustomTkinter). Permite configurar el rango de fechas, lanzar/monitorizar el pipeline y visualizar logs en tiempo real.
- **src/api/client.py**: Cliente HTTP para llamar a la API de Moodle. Centraliza la construcción de requests y el manejo de paginación/errores.
- **src/api/services.py**: Orquestador de métricas por curso. Llama a las funciones de los módulos de indicadores y consolida la estructura final que se persiste.
- **src/api/indicators/**: Implementación de los cálculos de indicadores. Se organiza en tres grupos:
	- `group1_results.py`: métricas de resultados y desempeño (notas, aprobación, cumplimiento).
	- `group2_design.py`: métricas relacionadas con el diseño instruccional y la estructura de contenidos.
	- `group3_behavior.py`: métricas de comportamiento e interacción (participación, feedback).
- **src/utils/db.py**: Persistencia a PostgreSQL/Supabase. Contiene conexión segura, carga de `.env` y la función `save_analytics_data_to_db` que inserta/actualiza dimensiones y hechos.
- **src/db.env** (o `bdd.env`): Fichero de variables de entorno con credenciales DB (no publicables en github). Ejemplo de variables: `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_NAME`.
- **src/utils/config_loader.py**: Lector de `config.ini` (no publicable en github) con secciones como `MOODLE` y `FILTERS`.
- **src/utils/filters.py**: Reglas para filtrar cursos (población mínima, integridad, estructura, categoría, rango de fechas, shortname/fullname patterns).
- **src/utils/period_parser.py**: Lógica para mapear cursos a periodos académicos (`id_tiempo`, `nombre_periodo`, `anio`, `trimestre`) usando nombre y timestamps.
- **keep_alive.py**: Script opcional/auxiliar para heartbeat o tareas periódicas (usado en despliegues/CI según el repositorio).
- **requirements.txt**: Dependencias Python del proyecto.

---

## Requisitos Previos

* Python 3.10 o superior.
* Acceso a base de datos PostgreSQL/Supabase.
* Librerías: psycopg2-binary, python-dotenv.

---

## Configuración e Instalación

1.  **Preparar entorno**: Copiar bdd.env.example a bdd.env.
2.  **Variables**: Configurar HOST, NAME, USER y PASSWORD en el archivo .env.
3.  **Dependencias**: Ejecutar pip install -r requirements.txt, pip install customtkinter

---

## Ejecución y Uso

Para iniciar el procesamiento:
Hay dos formas habituales de ejecutar el proyecto:

- **Interfaz gráfica**: ejecutar `python src/gui.py` y usar la ventana para seleccionar fechas y lanzar el proceso.
- **Línea de comandos / servidor**: ejecutar `python src/main.py` para correr el pipeline sin interfaz.

*Nota: Ejecutar a mitad de trimestre puede generar datos parciales en cuanto los indicadores 1.x"

---

##  Matriz de Indicadores (KPIs)

* **1.1 Cumplimiento**: Porcentaje de actividades entregadas.
* **1.2 Aprobación**: Ratio de estudiantes con nota satisfactoria.
* **1.3 Estadística**: Media, mediana y desviación estándar.
* **2.1 Metodología**: Nivel de interacción de contenidos.
* **3.2 Feedback**: Calidad de la retroalimentación docente.

---

## Reglas de Negocio (Filtros)

1.  **Población**: Mínimo 5 estudiantes por curso.
2.  **Integridad**: Máximo 10% de actividades sin calificar.
3.  **Estructura**: No se procesan cursos con jerarquía plana.

---

## Modelo de Datos

* **Dimensiones**: dim_tiempo, dim_profesor, dim_asignatura.
* **Hechos**: hecho_experiencia_curso.
* **Conflictos**: Se usa ON CONFLICT DO UPDATE para evitar duplicados.

---

## Solución de Problemas

* **Error SSL**: El proyecto está preparado para conectarse a Supabase con `sslmode=require`. Asegúrate de que `src/db.env` (o tus variables de entorno) contienen las credenciales correctas: `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_NAME`.
* **Librerías**: Verificar instalación con pip list.
* **Datos**: Validar que el id_periodo sea el correcto en la base de datos.

---

## Licencia

Proyecto académico para tesis. Uso restringido a fines de investigación interna.