# TaskOptimizer/urls.py

from django.contrib import admin
from django.urls import path, include # Asegúrate de importar include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')), # Tu aplicación core

    # URLs de autenticación (login, logout, cambio de contraseña, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    
]