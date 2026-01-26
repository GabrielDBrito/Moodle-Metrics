import statistics
from api.client import call_moodle_api

# --- CONSTANTES ---
# Listas para clasificar el Diseño Instruccional (Indicadores Grupo 2)
MOD_ACTIVOS = ['assign', 'quiz', 'forum', 'workshop', 'h5pactivity', 'scorm', 'lesson', 'glossary', 'wiki']
MOD_PASIVOS = ['resource', 'url', 'page', 'folder', 'book', 'label', 'imscp']
MOD_EVALUABLES = ['assign', 'quiz', 'workshop']

def get_procrastination_stats(config, course_id, valid_student_ids):
    """
    Calcula KPIs de Procrastinación (3.1) y Retención (2.3) usando 'mod_assign'.
    """
    moodle_config = config['MOODLE']
    
    # 1. Obtener configuración de tareas
    assignments = call_moodle_api(moodle_config, "mod_assign_get_assignments", courseids=[course_id])
    if not assignments or 'courses' not in assignments or not assignments['courses']:
        return None
    
    course_assignments = assignments['courses'][0].get('assignments', [])
    
    # Mapa: ID Tarea -> Fecha Límite. Solo futuras (>0).
    mapa_fechas = {a['id']: a['duedate'] for a in course_assignments if a.get('duedate', 0) > 0}
    if not mapa_fechas: return None

    # Identificar la "Actividad Final" (fecha más tardía) para Retención
    ultima_fecha_entrega = max(mapa_fechas.values())
    ids_actividad_final = set(k for k, v in mapa_fechas.items() if v == ultima_fecha_entrega)

    # 2. Obtener entregas masivas
    assignment_ids = list(mapa_fechas.keys())
    submissions_data = call_moodle_api(moodle_config, "mod_assign_get_submissions", assignmentids=assignment_ids)
    
    if not submissions_data or 'assignments' not in submissions_data: return None

    deltas_horas = []
    usuarios_retenidos = set()

    for task in submissions_data['assignments']:
        t_id = task.get('assignmentid')
        due_date = mapa_fechas.get(t_id)
        es_final = t_id in ids_actividad_final
        
        for sub in task.get('submissions', []):
            # Solo alumnos válidos
            if sub.get('userid') not in valid_student_ids: continue
            
            # Si hay entrega...
            if sub.get('status') == 'submitted' and sub.get('timemodified'):
                # 3.1 Procrastinación: (Límite - Entrega) / 3600
                margin_hours = (due_date - sub['timemodified']) / 3600.0
                if -4400 < margin_hours < 4400: # Filtro de ruido
                    deltas_horas.append(margin_hours)
                
                # 2.3 Retención
                if es_final:
                    usuarios_retenidos.add(sub['userid'])

    return {
        "promedio_horas_margen": round(statistics.mean(deltas_horas), 2) if deltas_horas else None,
        "usuarios_retenidos_ids": usuarios_retenidos
    }

def analyze_structure(config, course_id):
    """ Analiza estructura (Activa vs Pasiva) usando core_course_get_contents """
    contents = call_moodle_api(config['MOODLE'], "core_course_get_contents", courseid=course_id)
    if not contents: return None

    stats = {"total_actividades": 0, "activas": 0, "pasivas": 0, "evaluadas": 0, "no_evaluadas": 0}
    for section in contents:
        for module in section.get('modules', []):
            mod_name = module.get('modname')
            stats["total_actividades"] += 1
            if mod_name in MOD_ACTIVOS: stats["activas"] += 1
            elif mod_name in MOD_PASIVOS: stats["pasivas"] += 1
            
            if mod_name in MOD_EVALUABLES: stats["evaluadas"] += 1
            else: stats["no_evaluadas"] += 1
    return stats

def get_full_course_analytics(config, course_id):
    """
    ORQUESTADOR PRINCIPAL
    Usa gradereport_user_get_grade_items (userid=0) para bajar todo de golpe.
    """
    moodle_config = config['MOODLE']

    # --- 1. Estructura (Grupo 2) ---
    struct = analyze_structure(config, course_id)
    if not struct or struct['total_actividades'] == 0: return None

    # --- 2. Notas y Progreso (Grupo 1) ---
    # ESTA ES LA LLAMADA QUE SÍ FUNCIONA
    grades_data = call_moodle_api(moodle_config, "gradereport_user_get_grade_items", courseid=course_id, userid=0)
    
    if not grades_data or 'usergrades' not in grades_data: return None
    all_students = grades_data['usergrades']
    
    # Filtro tamaño mínimo
    if len(all_students) < 3: return None

    # Variables de acumulación
    valid_student_ids = set()
    final_grades_cache = []
    
    total_checks_completados = 0 
    estudiantes_con_actividad = 0
    estudiantes_finalizadores = 0
    
    total_items_calificados_feedback = 0
    total_items_con_texto_feedback = 0

    # Contar cuántas actividades tiene el curso (usando al primer alumno como referencia)
    total_items_rastreables = 0
    if all_students:
        # Contamos todo lo que NO sea el total del curso ('course') ni categorías ('category')
        total_items_rastreables = len([i for i in all_students[0]['gradeitems'] 
                                     if i['itemtype'] not in ('course', 'category')])

    TARGET_SCALE = 20.0
    MIN_VALID_GRADE = 1.0 

    for student in all_students:
        uid = student['userid']
        items_completados_usuario = 0
        user_is_active = False # ¿Tiene nota en el curso?
        
        for item in student.get('gradeitems', []):
            item_type = item.get('itemtype')
            raw = item.get('graderaw')
            
            # A. Nota Final del Curso
            if item_type == 'course':
                gmax = item.get('grademax')
                if raw is not None and gmax is not None and float(gmax) > 0:
                    val = float(raw)
                    if val >= MIN_VALID_GRADE:
                        user_is_active = True
                        final_grades_cache.append({'val': val, 'max': float(gmax)})
            
            # B. Actividades Individuales (Cumplimiento y Feedback)
            elif item_type not in ('course', 'category'):
                # Si tiene nota, asumimos actividad completada
                if raw is not None:
                    items_completados_usuario += 1
                    total_checks_completados += 1
                    
                    # 3.2 Feedback
                    total_items_calificados_feedback += 1
                    fb = str(item.get('feedback', '')).replace('<p>', '').replace('</p>', '').strip()
                    # Si el feedback tiene más de 5 letras, es cualitativo real
                    if len(fb) > 5: 
                        total_items_con_texto_feedback += 1

        # Métricas por estudiante
        if user_is_active:
            valid_student_ids.add(uid)
            
            # 1.4 Activos (Hizo al menos 1 cosa)
            if items_completados_usuario >= 1: 
                estudiantes_con_actividad += 1
            
            # 1.5 Finalización (>80% de actividades con nota)
            if total_items_rastreables > 0 and (items_completados_usuario / total_items_rastreables) >= 0.8:
                estudiantes_finalizadores += 1

    if not final_grades_cache: return None

    # --- Procesamiento Notas (Normalización y Limpieza) ---
    raw_vals = [x['val'] for x in final_grades_cache]
    max_vals = [x['max'] for x in final_grades_cache]
    
    avg_raw = statistics.mean(raw_vals)
    max_conf = statistics.mode(max_vals)
    max_real = max(raw_vals)
    
    # Corrección: Si está configurado en 100 pero evalúan en 20
    apply_correction = (max_conf > 25.0 and max_real <= 20.0 and avg_raw > 5.0)
    
    normalized_grades = []
    for x in final_grades_cache:
        val, gmax = x['val'], x['max']
        norm = val if apply_correction or gmax == TARGET_SCALE else (val / gmax) * TARGET_SCALE
        normalized_grades.append(norm)

    # Si el promedio es absurdo (<1), descartamos curso
    if statistics.mean(normalized_grades) < 1.0: return None
    
    num_validos = len(normalized_grades)

    # --- 3. Procrastinación (Grupo 3) ---
    proc_stats = get_procrastination_stats(config, course_id, valid_student_ids)
    
    avg_proc = None
    retenidos = 0
    if proc_stats:
        avg_proc = proc_stats["promedio_horas_margen"]
        retenidos = len(proc_stats["usuarios_retenidos_ids"])

    # --- CÁLCULOS FINALES KPI ---
    
    # 1.1 Cumplimiento
    capacidad = num_validos * total_items_rastreables
    tasa_cumplimiento = (total_checks_completados / capacidad * 100) if capacidad > 0 else 0

    # 1.2 Aprobación
    tasa_aprobacion = (sum(1 for g in normalized_grades if g >= 10)/num_validos)*100
    
    # 2.1 Metodología
    pct_metodologia = (struct['activas'] / struct['total_actividades'] * 100) if struct['total_actividades'] > 0 else 0
    
    # 2.2 Relación
    rel_eval = struct['evaluadas'] / struct['no_evaluadas'] if struct['no_evaluadas'] > 0 else struct['evaluadas']

    # 3.2 Feedback
    pct_feedback = (total_items_con_texto_feedback / total_items_calificados_feedback * 100) if total_items_calificados_feedback > 0 else 0

    return {
        "id_curso": course_id,
        "n_estudiantes": num_validos,
        # Grupo 1
        "ind_1_1_cumplimiento": round(tasa_cumplimiento, 2),
        "ind_1_2_aprobacion": round(tasa_aprobacion, 2),
        "ind_1_3_promedio": round(statistics.mean(normalized_grades), 2),
        "ind_1_3_mediana": round(statistics.median(normalized_grades), 2),
        "ind_1_3_desviacion": round(statistics.stdev(normalized_grades), 2) if num_validos > 1 else 0,
        "ind_1_4_activos": round((estudiantes_con_actividad/num_validos)*100, 2),
        "ind_1_5_finalizacion": round((estudiantes_finalizadores/num_validos)*100, 2),
        # Grupo 2
        "ind_2_1_metodologia": round(pct_metodologia, 2),
        "ind_2_2_relacion_eval": round(rel_eval, 2),
        "ind_2_3_retencion": round((retenidos/num_validos)*100, 2),
        # Grupo 3
        "ind_3_1_procrastinacion": avg_proc,
        "ind_3_2_feedback": round(pct_feedback, 2)
    }