# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal del dashboard (requiere login)
    path('', views.home, name='home'),

    # Rutas para acciones de tareas (requieren login implícito por 'home')
    path('toggle_task/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('delete_completed/', views.delete_completed_tasks, name='delete_completed'),

    # NUEVA RUTA: Para el registro de usuarios
    path('register/', views.register, name='register'),

    # La ruta save_schedule se elimina temporalmente
]