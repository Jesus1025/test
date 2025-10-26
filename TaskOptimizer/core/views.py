# core/views.py

import json
import requests
from datetime import date, timedelta, datetime, time
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# IMPORTANTE: Asegúrate de que estos modelos existan en core/models.py
from .models import Task, UserProfile

# --- CONFIGURACIÓN DE LA API DE GEMINI (SE MANTIENE) ---
GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025'
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# --- ROL DEL AGENTE DE OPTIMIZACIÓN (SE MANTIENE) ---
SYSTEM_INSTRUCTION_PROMPT = """
Actúa como un analista de productividad para inferir la carga cognitiva de una nueva tarea y programarla óptimamente en la semana para prevenir el "burnout" del usuario. Tu objetivo principal es programar la tarea en el día que garantice que el esfuerzo acumulado diario no supere el Umbral de Burnout, respetando la jornada del usuario.

REGLAS DE INFERENCIA:
1.A. TAREAS (Ej: 'Estudiar Python', 'Hacer reporte'): Analiza el TEXTO_NUEVA_TAREA y califícalo:
    - effort: Valor entero de 1 a 5 (1=fácil, 5=muy difícil/demandante).
    - duration_hours: Duración estimada en horas (0.5, 1.0, 2.0, etc.).
1.B. EVENTOS (Ej: 'Concierto Bad Bunny', 'Cita médica', 'Cena familiar'): Si el texto es un evento social o una cita que bloquea tiempo (non una tarea de trabajo/estudio), haz lo siguiente:
    - duration_hours: Estima la duración total del evento (ej. un concierto son 3-4 horas).
    - effort: Asigna un 'esfuerzo' alto para 'bloquear' el día. Usa una heurística de 2 puntos de esfuerzo por cada hora de duración (ej: 3 horas = 6 de esfuerzo).
    - new_task_text: Mantén el nombre del evento (ej: "Concierto Bad Bunny").

REGLAS DE DECISIÓN CLAVE (OPTIMIZACIÓN):
2. UMBRAL DE BURNOUT: El esfuerzo acumulado máximo permitido para cualquier día es de 15 PUNTOS DE ESFUERZO.
3. DISPONIBILIDAD: Las tareas/eventos SOLO pueden programarse dentro del 'HORARIO_SEMANAL_USUARIO' (ver contexto). Un día con '00:00' a '00:00' está LIBRE y no puede recibir tareas.
4. DETECCIÓN DE FECHA/HORA: Si el usuario especifica un día o una hora en el texto (ej: "el sábado a las 20:00", "el 2025-10-28"), DEBES USAR ESE DÍA Y HORA.
5. OPTIMIZACIÓN (SI NO HAY FECHA): Si el usuario NO especifica una fecha:
    5.A. PRIORIDAD DIARIA: Si el esfuerzo total de HOY (Acumulado + Nuevo) NO SUPERA el Umbral de 15, programa la nueva tarea para HOY.
    5.B. PRIORIDAD SEMANAL: Si HOY supera el Umbral de 15, busca en el 'ESFUERZO_SEMANAL_ACTUAL' el día que tenga el MENOR esfuerzo acumulado total y asígnalo allí.
6. PREVENCIÓN DE COLISIONES: Al elegir una 'recommended_time', DEBES revisar la lista de 'TAREAS_PROGRAMADAS_SEMANA' para ese día. NO ASIGNES una tarea a una hora de inicio que ya esté ocupada. Busca el siguiente bloque disponible (ej. 30 min después), respetando siempre la jornada del usuario.

FORMATO DE ENTRADA: Recibirás una nueva tarea y el contexto semanal de la base de datos (DB).
FORMATO DE SALIDA: Debes devolver UNICAMENTE un objeto JSON.

JSON OUTPUT SCHEMA:
{
  "project_name": "TASK FLOW OPTIMIZER",
  "new_task_text": "...",
  "inferred_attributes": {
    "effort": 1-15 (1-5 para tareas, 1-15 para eventos),
    "duration_hours": 0.5+
  },
  "optimization_decision": {
    "recommended_day": "YYYY-MM-DD",
    "recommended_time": "HH:MM" (Si el usuario especificó una hora, úsala. Si no, usa una hora de inicio VÁLIDA y NO OCUPADA),
    "total_effort_today_after_task": 0
  },
  "reasoning": "Clara justificación en español. Si asignaste un evento, explica que lo trataste como una tarea de alto esfuerzo para bloquear el día."
}
"""

# --- GeminiAgentService (SE MANTIENE IGUAL) ---
class GeminiAgentService:
    def __init__(self, system_instruction):
        self.system_instruction = system_instruction
        self.api_key = "AIzaSyDAxQLidBsYbsDr9GlpntgCSpetF-ojwxo"

    def optimize_task(self, task_text, context_db):
        full_prompt = context_db
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "systemInstruction": {"parts": [{"text": self.system_instruction}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }
        try:
            response = requests.post(f"{GEMINI_API_URL}?key={self.api_key}", headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            if not result.get('candidates'):
                print(f"Error: Respuesta inesperada de la API Gemini: {result}")
                return {"error": "API_RESPONSE_ERROR", "reasoning": "La API devolvió una respuesta inesperada."}
            gemini_output_text = result['candidates'][0]['content']['parts'][0]['text']
            optimized_data = json.loads(gemini_output_text)
            return optimized_data
        except requests.exceptions.RequestException as e:
            print(f"Error en la llamada a la API de Gemini: {e}")
            return {"error": "API_ERROR", "reasoning": f"No se pudo conectar con el Agente IA. Detalles: {e}"}
        except json.JSONDecodeError as e:
            print(f"Error: La IA no devolvió JSON válido: {e}")
            return {"error": "INVALID_JSON", "reasoning": "La IA no devolvió la respuesta en el formato JSON esperado."}
        except Exception as e:
            print(f"Error inesperado al procesar la respuesta: {e}")
            return {"error": "UNKNOWN_ERROR", "reasoning": f"Error inesperado. Detalles: {e}"}

# Instancia del servicio Gemini
gemini_agent = GeminiAgentService(SYSTEM_INSTRUCTION_PROMPT)

# --- Vista de Registro (SE MANTIENE) ---
def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Crear perfil de usuario automáticamente al registrarse
            UserProfile.objects.get_or_create(user=user)
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# --- FUNCIÓN MEJORADA PARA CALCULAR RACHA ---
def calculate_streak(user):
    """Calcula la racha de días consecutivos completando al menos una tarea."""
    today = date.today()
    streak = 0
    
    try:
        # Obtener fechas únicas donde el usuario completó al menos una tarea
        completed_dates = Task.objects.filter(
            user=user, 
            completed=True
        ).dates('day', 'day', order='DESC')
        
        if not completed_dates:
            return 0
            
        completed_dates_list = list(completed_dates)
        
        # Si la última tarea completada fue hoy, empezamos la racha
        if completed_dates_list[0] == today:
            streak = 1
            current_date = today - timedelta(days=1)
            
            # Verificar días consecutivos hacia atrás
            for completed_date in completed_dates_list[1:]:
                if completed_date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
                    
    except Exception as e:
        print(f"Error al calcular racha: {e}")
        return 0
        
    return streak

# --- Helper Function: Obtener Contexto para IA desde la BD ---
def get_context_for_ia_from_db(user, new_task_text):
    """Compila el contexto para la IA consultando la BD para el usuario dado."""
    today = date.today()
    end_date = today + timedelta(days=6)
    
    try:
        # Obtener o crear el perfil del usuario
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        weekly_schedule = user_profile.get_weekly_schedule()
        burnout_threshold = user_profile.burnout_threshold
        
        # Obtener tareas no completadas del usuario
        user_tasks = Task.objects.filter(
            user=user, 
            day__range=[today, end_date], 
            completed=False
        ).order_by('day', 'time')
        
    except Exception as e:
        print(f"Error consultando datos para IA: {e}")
        # Valores por defecto en caso de error
        weekly_schedule = UserProfile.get_default_schedule()
        burnout_threshold = 15
        user_tasks = []

    weekly_effort_map = {}
    weekly_tasks_map = {}
    
    for i in range(7):
        current_day = today + timedelta(days=i)
        current_day_str = current_day.strftime('%Y-%m-%d')
        current_weekday = current_day.weekday()
        
        # Filtrar tareas para este día
        tasks_for_day = [t for t in user_tasks if t.day == current_day]
        effort_for_day = sum(t.effort for t in tasks_for_day)
        weekly_effort_map[current_day_str] = effort_for_day
        
        weekly_tasks_map[current_day_str] = [
            {
                "text": t.text,
                "start_time": t.time.strftime('%H:%M') if t.time else 'N/A',
                "duration": t.duration
            } for t in tasks_for_day
        ]

    today_str = today.strftime('%Y-%m-%d')
    schedule_context_str = json.dumps(weekly_schedule, indent=2)
    weekly_effort_map_str = json.dumps(weekly_effort_map, indent=2)
    weekly_tasks_map_str = json.dumps(weekly_tasks_map, indent=2)
    
    context = {
        "HORARIO_SEMANAL_USUARIO": schedule_context_str,
        "FECHA_HOY": today_str,
        "ESFUERZO_SEMANAL_ACTUAL": weekly_effort_map_str,
        "TAREAS_PROGRAMADAS_SEMANA": weekly_tasks_map_str,
        "TEXTO_NUEVA_TAREA": new_task_text
    }

    prompt_parts = [
        f"1. HORARIO SEMANAL DEL USUARIO (0=Lunes, 6=Domingo): {context['HORARIO_SEMANAL_USUARIO']}",
        f"2. ESTADO ACTUAL DE LA SEMANA:",
        f"* FECHA_HOY: {context['FECHA_HOY']}",
        f"* ESFUERZO_SEMANAL_ACTUAL (Acumulado por día): {context['ESFUERZO_SEMANAL_ACTUAL']}",
        f"* TAREAS_PROGRAMADAS_SEMANA (JSON): {context['TAREAS_PROGRAMADAS_SEMANA']}",
        f"3. TAREA A PROGRAMAR:",
        f"* TEXTO_NUEVA_TAREA: {context['TEXTO_NUEVA_TAREA']}",
        "Genera la respuesta UNICAMENTE en el formato JSON solicitado."
    ]
    
    return "\n\n".join(prompt_parts)

# --- VISTA PRINCIPAL MEJORADA ---
@login_required
def home(request):
    message = ""
    user = request.user

    # --- Lógica POST: Llamar a la IA y Guardar en BD ---
    if request.method == 'POST':
        new_task_text = request.POST.get('new_task_text')
        if new_task_text:
            context_prompt = get_context_for_ia_from_db(user, new_task_text)
            ia_decision = gemini_agent.optimize_task(new_task_text, context_prompt)
            
            if ia_decision and "error" not in ia_decision:
                try:
                    # Extraer y convertir datos de la IA
                    inferred_effort = int(ia_decision.get('inferred_attributes', {}).get('effort', 1))
                    inferred_duration = float(ia_decision.get('inferred_attributes', {}).get('duration_hours', 0.5))
                    recommended_day_str = ia_decision.get('optimization_decision', {}).get('recommended_day')
                    recommended_time_str = ia_decision.get('optimization_decision', {}).get('recommended_time')

                    # Convertir strings a objetos date/time para el modelo
                    task_day = date.fromisoformat(recommended_day_str) if recommended_day_str else date.today()
                    
                    task_time = None
                    if recommended_time_str and recommended_time_str != 'N/A':
                        try:
                            task_time = datetime.strptime(recommended_time_str, '%H:%M').time()
                        except ValueError:
                            task_time = datetime.strptime('08:00', '%H:%M').time()

                    # Crear y guardar la tarea directamente en la BD
                    Task.objects.create(
                        user=user,
                        text=ia_decision.get('new_task_text', new_task_text),
                        effort=inferred_effort,
                        day=task_day,
                        time=task_time,
                        duration=inferred_duration,
                        completed=False  # Asegurar que empiece como no completada
                    )
                    message = f"Tarea programada. Razón: {ia_decision.get('reasoning', 'Sin detalles.')}"
                    
                except (ValueError, TypeError) as e:
                    message = f"Error al procesar/convertir respuesta de IA: {e}. Respuesta: {ia_decision}"
                except Exception as e:
                    message = f"Error inesperado al guardar la tarea en BD: {e}"
            elif ia_decision:
                message = f"Error de optimización: {ia_decision.get('reasoning', 'Error desconocido.')}"
            else:
                message = "Error: No se pudo obtener respuesta del Agente IA."
        else:
            message = "Error: El texto de la tarea no puede estar vacío."

    # --- Lógica GET: Solo tareas existentes del usuario ---
    today_obj = date.today()
    today_str = today_obj.strftime('%Y-%m-%d')
    today_weekday = today_obj.weekday()
    
    # Obtener perfil del usuario
    try:
        user_profile = UserProfile.objects.get(user=user)
        weekly_schedule = user_profile.get_weekly_schedule()
        burnout_threshold = user_profile.burnout_threshold
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=user)
        weekly_schedule = user_profile.get_weekly_schedule()
        burnout_threshold = user_profile.burnout_threshold
    
    today_schedule = weekly_schedule.get(today_weekday, {'name': 'Día', 'start': '00:00', 'end': '00:00'})

    # Obtener SOLO las tareas del usuario (sin predeterminadas)
    end_date = today_obj + timedelta(days=6)
    all_user_tasks = Task.objects.filter(
        user=user, 
        day__range=[today_obj, end_date]
    ).order_by('day', 'time')

    # Procesar tareas para la vista semanal
    week_view_data = []
    for i in range(7):
        current_date_obj = today_obj + timedelta(days=i)
        current_date_str = current_date_obj.strftime('%Y-%m-%d')
        current_weekday = current_date_obj.weekday()
        
        day_schedule = weekly_schedule.get(current_weekday, {'name': 'Día', 'start': '00:00', 'end': '00:00'})
        
        # Filtrar tareas para este día
        tasks_for_this_day_raw = [t for t in all_user_tasks if t.day == current_date_obj]
        
        processed_tasks = []
        for task in tasks_for_this_day_raw:
            start_time_str = task.time.strftime('%H:%M') if task.time else 'N/A'
            duration_hours = float(task.duration)
            end_time_str = "N/A"
            
            if task.time:
                try:
                    start_dt = datetime.combine(date.today(), task.time)
                    duration_td = timedelta(hours=duration_hours)
                    end_dt = start_dt + duration_td
                    end_time_str = end_dt.strftime('%H:%M')
                except ValueError:
                    pass

            processed_tasks.append({
                'id': task.id,
                'text': task.text,
                'effort': task.effort,
                'day': task.day.strftime('%Y-%m-%d'),
                'time': start_time_str,
                'end_time': end_time_str,
                'duration': task.duration,
                'completed': task.completed,
            })

        effort_for_this_day = sum(
            t['effort'] for t in processed_tasks if not t['completed']
        )

        week_view_data.append({
            'date_str': current_date_str,
            'day_name': day_schedule['name'],
            'tasks': processed_tasks,
            'is_today': (i == 0),
            'accumulated_effort': effort_for_this_day
        })

    accumulated_effort_today = week_view_data[0]['accumulated_effort']
    available_effort_today = max(0, burnout_threshold - accumulated_effort_today)

    # --- LÓGICA DE RACHA Y PROGRESO ---
    current_streak = calculate_streak(user)

    # Conteo mensual de tareas
    start_of_month = today_obj.replace(day=1)
    monthly_completed_tasks = Task.objects.filter(
        user=user,
        completed=True,
        day__gte=start_of_month,
        day__lte=today_obj
    ).count()

    # Lógica de estrellas
    MAX_STARS_PER_MONTH = 30
    stars_to_show = min(monthly_completed_tasks, MAX_STARS_PER_MONTH)

    is_reward_day = False
    reward_image_url = None
    static_background_url = 'core/images/fondo_racha.jfif'
    star_image_base_url = 'core/images/estrella'

    context = {
        'today_date': today_str,
        'today_weekday': today_weekday,
        'today_schedule': today_schedule,
        'weekly_schedule': weekly_schedule,
        'burnout_threshold': burnout_threshold,
        'message': message,
        'week_view_data': week_view_data,
        'accumulated_effort': accumulated_effort_today,
        'available_effort': available_effort_today,
        'user': user,
        'current_streak': current_streak,
        'monthly_completed_tasks': monthly_completed_tasks,
        'stars_to_show': stars_to_show,
        'is_reward_day': is_reward_day,
        'reward_image_url': reward_image_url,
        'static_background_url': static_background_url,
        'star_image_base_url': star_image_base_url,
    }
    
    return render(request, 'core/index.html', context)

# --- VISTA MEJORADA PARA MARCAR TAREAS ---
@login_required
@require_http_methods(["GET"])
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    # Si la tarea se está marcando como COMPLETED (True)
    if not task.completed:
        # 1. Actualiza la fecha de la tarea a HOY
        task.day = date.today()
        # 2. (Opcional) Actualiza la hora al momento actual para el registro
        task.time = timezone.now().time()
    
    # 3. Cambia el estado de completado
    task.completed = not task.completed
    
    task.save() # Guarda el cambio en la BD
    return redirect('home')

# --- VISTA PARA ELIMINAR TAREAS COMPLETADAS ---
@login_required
@require_http_methods(["GET"])
def delete_completed_tasks(request):
    Task.objects.filter(user=request.user, completed=True).delete()
    return redirect('home')

# --- VISTA PARA GUARDAR HORARIO ---
@login_required
@require_http_methods(["POST"])
def save_schedule(request):
    try:
        user = request.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        
        schedule_data = {}
        for i in range(7):
            start_key = f'start_{i}'
            end_key = f'end_{i}'
            schedule_data[start_key] = request.POST.get(start_key, '00:00')
            schedule_data[end_key] = request.POST.get(end_key, '00:00')
        
        user_profile.set_weekly_schedule(schedule_data)
        
        burnout_threshold = request.POST.get('burnout_threshold')
        if burnout_threshold:
            try:
                user_profile.burnout_threshold = int(burnout_threshold)
                user_profile.save()
            except ValueError:
                pass
                
        return redirect('home')
        
    except Exception as e:
        print(f"Error guardando horario: {e}")
        return redirect('home')