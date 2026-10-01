from pathlib import Path
import environ
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin vers la librairie GDAL (Windows - installée via wheel osgeo)
_osgeo_path = BASE_DIR / 'venv' / 'Lib' / 'site-packages' / 'osgeo'
if _osgeo_path.exists():
    # Forcer PROJ à utiliser sa propre base de données (évite le conflit avec PostgreSQL)
    os.environ['PROJ_DATA'] = str(_osgeo_path / 'data' / 'proj')
    os.environ['PROJ_LIB'] = str(_osgeo_path / 'data' / 'proj')
    # Mettre osgeo en tête du PATH pour charger les bonnes DLL
    os.environ['PATH'] = str(_osgeo_path) + os.pathsep + os.environ.get('PATH', '')
    if str(_osgeo_path) not in sys.path:
        sys.path.insert(0, str(_osgeo_path))

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / '.env', overwrite=True)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    # Third-party
    'rest_framework',
    'rest_framework_gis',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    # Project apps
    'accounts',
    'foncier',
    'drones',
    'constructions',
    'dashboard',
    'navigation',
    'pdu',
    'commune',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.debug_middleware.SessionDebugMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'commune.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='uad_sig_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='123456'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'accounts.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # 6 caractères minimum, chiffres seuls acceptés : les habitants utilisent souvent
    # un code chiffré. Les mots de passe trop courants (123456…) restent refusés.
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

SESSION_COOKIE_NAME = 'geofoncier_sid'

# Session expirée après 30 min d'inactivité (prolongée à chaque requête)
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

# E-mail (console en développement — remplacer par SMTP en production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'GéoFoncier NGOGOM_UAD <noreply@uad.edu.sn>'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

GDAL_LIBRARY_PATH = str(BASE_DIR / 'venv' / 'Lib' / 'site-packages' / 'osgeo' / 'gdal.dll')
GEOS_LIBRARY_PATH = str(BASE_DIR / 'venv' / 'Lib' / 'site-packages' / 'osgeo' / 'geos_c.dll')
