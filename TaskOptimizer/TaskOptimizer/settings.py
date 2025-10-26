# TaskOptimizer/settings.py

"""
Django settings for TaskOptimizer project.
"""

from pathlib import Path
import os # Necesario para leer variables de entorno (más adelante)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# En producción, esto debería leerse de una variable de entorno
SECRET_KEY = 'django-insecure-tu_clave_secreta_aqui'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False # Cambiar a False en producción

# En producción, añade tu dominio aquí (ej: ['www.tusitio.com'])
ALLOWED_HOSTS = ['web-production-631b1.up.railway.app', 'localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', # Necesario para usuarios
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core', # Tu aplicación
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Necesario
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'TaskOptimizer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # AÑADIDO: Django buscará templates en la carpeta 'templates' de cada app
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth', # Necesario
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'TaskOptimizer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Usaremos SQLite para desarrollo. En producción, cambiarías esto.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# En producción, configurarías STATIC_ROOT

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- AÑADIDO: Redirecciones para Login/Logout ---
LOGIN_REDIRECT_URL = '/' # A dónde ir después de iniciar sesión
LOGOUT_REDIRECT_URL = '/' # A dónde ir después de cerrar sesión
LOGIN_URL = 'login' # Nombre de la URL de login (definida por django.contrib.auth.urls)

CSRF_TRUSTED_ORIGINS = ['web-production-631b1.up.railway.app']