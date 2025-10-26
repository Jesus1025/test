# core/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    weekly_schedule = models.JSONField(default=dict)
    burnout_threshold = models.IntegerField(default=15)
    
    def get_weekly_schedule(self):
        """Devuelve el horario semanal, o el horario por defecto si no existe."""
        if self.weekly_schedule:
            return self.weekly_schedule
        return self.get_default_schedule()
    
    def set_weekly_schedule(self, schedule_data):
        """Guarda el horario semanal en formato JSON."""
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        new_schedule = {}
        
        for i in range(7):
            start_key = f'start_{i}'
            end_key = f'end_{i}'
            new_schedule[i] = {
                'name': days[i],
                'start': schedule_data.get(start_key, '00:00'),
                'end': schedule_data.get(end_key, '00:00')
            }
        
        self.weekly_schedule = new_schedule
        self.save()
    
    @staticmethod
    def get_default_schedule():
        """Devuelve el horario semanal por defecto."""
        return {
            0: {'name': 'Lunes', 'start': '09:00', 'end': '17:00'},
            1: {'name': 'Martes', 'start': '09:00', 'end': '17:00'},
            2: {'name': 'Miércoles', 'start': '09:00', 'end': '17:00'},
            3: {'name': 'Jueves', 'start': '09:00', 'end': '17:00'},
            4: {'name': 'Viernes', 'start': '09:00', 'end': '17:00'},
            5: {'name': 'Sábado', 'start': '10:00', 'end': '18:00'},
            6: {'name': 'Domingo', 'start': '00:00', 'end': '00:00'}
        }
    
    def __str__(self):
        return f"Perfil de {self.user.username}"

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    effort = models.IntegerField(default=1)
    day = models.DateField()
    time = models.TimeField(null=True, blank=True)
    duration = models.FloatField(default=0.5)  # horas
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.text} ({self.user.username})"