# admin_panel/settings.py

from pathlib import Path
import os
import sys
import dj_database_url
from datetime import timedelta
import base64
import json
import django
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Optional: allow disabling Firestore usage via env var for deployments where
# you want to stop using Firestore (e.g. Render). Set `USE_FIRESTORE=false`.
USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'true').lower() == 'true'

if USE_FIRESTORE:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except Exception:
        # If imports fail, we'll fall back below to the stub implementation.
        firebase_admin = None
        credentials = None
        firestore = None

# ==============================================================================
# Definiciones Base
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Todas las apps del proyecto viven en apps/. Inyectar esa carpeta en sys.path
# permite mantener los nombres cortos en INSTALLED_APPS (p.ej. 'calidad'),
# sin invalidar los app_label de migraciones ya aplicadas en produccion.
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# ==============================================================================
# Configuración de Seguridad y Despliegue
# ==============================================================================
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tu-clave-local-de-desarrollo')
GOOGLE_FORM_SECRET_KEY = os.environ.get('GOOGLE_FORM_SECRET_KEY')
CRON_SECRET_KEY = os.environ.get('CRON_SECRET_KEY')

# URL del sistema externo monitoreo-web (Fase 4 del plan de separacion de
# proyecto_yeni). Mientras no se configure, el login de usuarios de
# Proyecto_Yeni/Yeni_admin sigue funcionando igual que hoy, dentro de este
# repo. Se activa solo cuando monitoreo-web este desplegado y verificado.
MONITOREO_WEB_URL = os.environ.get('MONITOREO_WEB_URL')

# Lógica robusta para la variable DEBUG
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'
print(f"VALOR DE DEBUG LEÍDO: {os.environ.get('DJANGO_DEBUG', 'No definido')}, RESULTADO FINAL DE DEBUG: {DEBUG}")

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.10.42', '10.0.2.2']

# Si la app se despliega en Render, RENDER_EXTERNAL_HOSTNAME será agregado.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    # Puedes añadir tus orígenes de desarrollo si usas HTTPS localmente
    # 'https://localhost:8000',
    # 'https://127.0.0.1:8000',
]

if RENDER_EXTERNAL_HOSTNAME:
    # Construimos la URL completa para el origen de confianza
    trusted_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if trusted_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(trusted_origin)
# --- FIN DEL BLOQUE AÑADIDO ---
# ==============================================================================
# Aplicaciones Instaladas
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Mis aplicaciones
    'calidad',
    'administracion',
    'recursoshumanos', # <-- App base con modelos referenciados
    'cenerisapp',
    'cotizaciones',
    'simple_history',
    # Apps de terceros
    'storages', # <--- ¡CAMBIO IMPORTANTE! La app de storages debe estar registrada.
    # django-crispy-forms (renderiza formularios con plantillas Bootstrap)
    'crispy_forms',
    'crispy_bootstrap5',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'proyectos',
    'mathfilters',
    'inventario',
    'personal',
    'metricas_ceneris',
    'accesos',
    'api',
    'notificaciones',
]

# ==============================================================================
# Middleware
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    # CAV-186: debe ir despues de AuthenticationMiddleware (necesita
    # request.user ya resuelto) y despues de SessionMiddleware.
    'accesos.middleware.PlatformAccessMiddleware',
]

# ==============================================================================
# URLs, Plantillas, WSGI
# ==============================================================================
ROOT_URLCONF = 'admin_panel.urls'
WSGI_APPLICATION = 'admin_panel.wsgi.application'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ==============================================================================
# Base de Datos
# ==============================================================================
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    ),
    # configuracion bd biometrico ceneriso/oficina
    'db_biometrico':{
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'nominas',
        'USER': 'viewer',
        'PASSWORD': 'mirador26',
        'HOST': '38.253.181.75',
        'PORT': '3306',
        'OPTIONS': {
            'connect_timeout': 10,
        }
    },
}

# Router para dirigir las operaciones de base de datos
DATABASE_ROUTERS = [
    'admin_panel.db_router.DatabaseRouter',
]

# ==============================================================================
# Email (Configuración SMTP - Gmail)
# ==============================================================================

# Gmail - más confiable para envío programático (Outlook deshabilitó SMTP AUTH)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'notificaciones.ceneris@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'CENERIS Notificaciones <notificaciones.ceneris@gmail.com>'
EMAIL_TIMEOUT = 30

# Correo para recibir copia de notificaciones de EMOs (BCC)
EMAIL_COPIA_EMOS = os.environ.get('EMAIL_COPIA_EMOS', 'notificaciones@ceneris.com')

# Configuración en Render:
# EMAIL_HOST_USER = notificaciones.ceneris@gmail.com
# EMAIL_HOST_PASSWORD = ugjumjmspstprtca (contraseña de aplicación sin espacios)
# EMAIL_COPIA_EMOS = notificaciones@ceneris.com (opcional)

# ==============================================================================
# SendGrid (correo transaccional — HT-12)
# ==============================================================================
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.environ.get(
    'SENDGRID_FROM_EMAIL', 'notificaciones.ceneris@gmail.com'
)
SENDGRID_MAX_REINTENTOS = int(os.environ.get('SENDGRID_MAX_REINTENTOS', '5'))

# ==============================================================================
# Archivos Estáticos (Configuración para Render con WhiteNoise)
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]


STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]   
# ==============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE MEDIOS (MEDIA FILES) - ¡CORREGIDO PARA DEPURACIÓN!
# ==============================================================================

# --- Configuración para AWS S3 (se aplicará siempre, en local y en producción) ---
# --- Configuración para AWS S3 (se aplicará siempre, en local y en producción) ---
# Lectura desde variables de entorno. No guarde credenciales en el repositorio.
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

# Nombre del bucket S3. Usar EXACTAMENTE este nombre en AWS si no se pasa via env:
# asistencia-ceneris-media
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'asistencia-ceneris-media')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com' if AWS_STORAGE_BUCKET_NAME else None

# Prefijo (carpeta) dentro del bucket donde se guardarán los archivos de MEDIA
AWS_LOCATION = 'media'

# Seguridad y firma
# Evitamos ACLs públicas por defecto y usamos políticas de bucket o presigned URLs.
AWS_DEFAULT_ACL = None
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Storage backend: usa la clase de depuración en DEBUG y el backend estándar en producción
if DEBUG:
    DEFAULT_FILE_STORAGE = 'calidad.storages.DebugS3Boto3Storage'
else:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

IMAGEKIT_DEFAULT_FILE_STORAGE = DEFAULT_FILE_STORAGE

# URL base para acceder a los archivos de medios desde el bucket de S3
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/"
else:
    MEDIA_URL = '/media/'


# Configuración para django-crispy-forms (definida a nivel global)
# Usamos Bootstrap 5 como template pack por defecto.
# Asegúrate de tener instalado: pip install django-crispy-forms crispy-bootstrap5
CRISPY_ALLOWED_TEMPLATE_PACKS = ('bootstrap5',)
CRISPY_TEMPLATE_PACK = 'bootstrap5'


# ==============================================================================
# Otros Ajustes de Django
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [ {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}, ]
LANGUAGE_CODE = 'es-PE'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'recursoshumanos:main_dashboard'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ==============================================================================
# Inicialización de Firebase
# ==============================================================================
firebase_creds_base64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON_BASE64')

if USE_FIRESTORE and (firebase_admin is not None):
    # Attempt to initialize real Firebase credentials
    if firebase_creds_base64:
        decoded_creds = base64.b64decode(firebase_creds_base64)
        service_account_info = json.loads(decoded_creds)
        cred = credentials.Certificate(service_account_info)
    else:
        SERVICE_ACCOUNT_KEY_PATH = os.path.join(BASE_DIR, 'secrets', 'firebase-service-account.json')
        if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        else:
            cred = None
            print("ADVERTENCIA: Archivo de credenciales de Firebase no encontrado.")

    if cred and not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        db = None
else:
    # Firestore disabled — use the local stub so the app doesn't crash.
    try:
        from .firestore_stub import db as db
    except Exception:
        db = None

# Safety net: if for any reason `db` is still None (e.g. missing creds
# while USE_FIRESTORE=true), fall back to the stub to avoid AttributeError
# in views that expect `db` to exist. This makes local development easier.
if db is None:
    try:
        from .firestore_stub import db as db
        print('INFO: Firestore not available — using firestore_stub (db is a stub).')
    except Exception:
        db = None
    
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Esta es la única línea que necesitas para la autenticación por token.
        # Le dice a Django que use el sistema de JWT (Bearer Token).
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # Opcional pero recomendado: Por defecto, todas las vistas de API 
        # requerirán que el usuario esté autenticado.
        'rest_framework.permissions.IsAuthenticated',
    )
}

DATE_INPUT_FORMATS = [
    '%Y-%m-%d',  # Formato estándar HTML5 (2025-11-18)
    '%d/%m/%Y',  # Formato común Latam (18/11/2025)
    '%d-%m-%Y',  # Variación con guiones
]

SIMPLE_JWT = {
    # Aquí definimos que la sesión dure 15 horas (cubre toda la jornada laboral)
    'ACCESS_TOKEN_LIFETIME': timedelta(days=3650),
    
    # El token para renovar dura 30 días
    'REFRESH_TOKEN_LIFETIME': timedelta(days=3650),
    
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ==============================================================================
# CORS - Permitir peticiones desde la app Flutter Web/Movil
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = True
