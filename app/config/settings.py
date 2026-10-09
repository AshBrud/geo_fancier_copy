from pathlib import Path
import environ
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# Rendre toutes les applications métier situées dans app/apps/ directement importables
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Configuration GDAL / GEOS sous Windows
if os.name == 'nt':
    _site_packages_candidates = [
        BASE_DIR.parent / '.venv' / 'Lib' / 'site-packages',
        BASE_DIR / 'venv' / 'Lib' / 'site-packages',
    ]
    for _sp in _site_packages_candidates:
        if not _sp.exists():
            continue
        _osgeo_path = _sp / 'osgeo'
        if _osgeo_path.exists():
            os.environ['PROJ_DATA'] = str(_osgeo_path / 'data' / 'proj')
            os.environ['PROJ_LIB'] = str(_osgeo_path / 'data' / 'proj')
            os.environ['PATH'] = str(_osgeo_path) + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(str(_osgeo_path))
                except Exception:
                    pass
            if str(_osgeo_path) not in sys.path:
                sys.path.insert(0, str(_osgeo_path))
            break
        _pyogrio_libs = _sp / 'pyogrio.libs'
        if _pyogrio_libs.exists():
            _gdal_dlls = list(_pyogrio_libs.glob('gdal*.dll'))
            _geos_dlls = list(_pyogrio_libs.glob('geos_c*.dll'))
            if _gdal_dlls:
                GDAL_LIBRARY_PATH = str(_gdal_dlls[0])
            if _geos_dlls:
                GEOS_LIBRARY_PATH = str(_geos_dlls[0])
            
            # Données PROJ
            _proj_data = _sp / 'pyproj' / 'proj_dir' / 'share' / 'proj'
            if _proj_data.exists():
                os.environ['PROJ_DATA'] = str(_proj_data)
                os.environ['PROJ_LIB'] = str(_proj_data)

            # Charger les répertoires de DLLs sous Windows
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(str(_pyogrio_libs))
                except Exception:
                    pass
                _shapely_libs = _sp / 'shapely.libs'
                if _shapely_libs.exists():
                    try:
                        os.add_dll_directory(str(_shapely_libs))
                    except Exception:
                        pass
            os.environ['PATH'] = str(_pyogrio_libs) + os.pathsep + os.environ.get('PATH', '')
            break

env = environ.Env(DEBUG=(bool, True))
# Lecture du .env local ou racine
if (BASE_DIR / '.env').exists():
    environ.Env.read_env(BASE_DIR / '.env', overwrite=True)
elif (BASE_DIR.parent / '.env').exists():
    environ.Env.read_env(BASE_DIR.parent / '.env', overwrite=True)
elif (BASE_DIR.parent / '.env.dev').exists():
    environ.Env.read_env(BASE_DIR.parent / '.env.dev', overwrite=True)

SECRET_KEY = env('SECRET_KEY', default='django-insecure-geofoncier-local-dev-key-change-in-prod')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '0.0.0.0'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:8010', 'http://127.0.0.1:8010'])

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
    'dossiers',
    'accounts',
    'territoire',
    'drones',
    'urbanisme',
    'dashboard',
    'navigation',
    'pdu',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dossiers.middleware.ActiveDossierMiddleware',
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
                'dossiers.context_processors.active_dossier_context',
            ],
            'builtins': [
                'dossiers.templatetags.dossier_tags',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DB_HOST = env('DB_HOST', default='localhost')
DB_PORT = env('DB_PORT', default='5432')

# Résolution automatique transparente : Conteneur Docker vs Machine Hôte (uv/Windows)
if DB_HOST == 'db':
    import socket
    try:
        socket.gethostbyname('db')
    except (socket.gaierror, UnicodeError, OSError):
        DB_HOST = 'localhost'
        DB_PORT = env('DB_DEV_PORT', default='5433')

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME', default='uad_sig_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='123456'),
        'HOST': DB_HOST,
        'PORT': DB_PORT,
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
LOGIN_REDIRECT_URL = '/dossiers/'
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

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


