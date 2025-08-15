
from pathlib import Path
import environ

# === RUTAS BASE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === VARIABLES DE ENTORNO (.env) ===
# Crea un archivo .env en la raíz del proyecto (junto a manage.py)
# y definí DJANGO_SECRET_KEY, DJANGO_DEBUG, etc.
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")  # no falla si no existe

# === SEGURIDAD / CORE ===
# NUNCA dejes una SECRET_KEY real en el repo
SECRET_KEY = env("DJANGO_SECRET_KEY", default="!!!-cambia-esto-en-produccion-!!!")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

# Hosts permitidos (lista separada por comas en .env)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
# Orígenes confiables para CSRF (útil en prod: https://tu-dominio.onrender.com)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# === APPS INSTALADAS ===
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.postgres',

    # Terceros
    'django.contrib.humanize',
    'storages',

    # Apps propias
    'blog',
    'landingpage',
    'propiedades',
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise SIEMPRE inmediatamente después de SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise: servir estáticos comprimidos con hashes (cache-friendly)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# === URLCONF / WSGI ===
ROOT_URLCONF = 'mi_blog.urls'
WSGI_APPLICATION = 'mi_blog.wsgi.application'

# === TEMPLATES ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Si algún día querés una carpeta de templates a nivel proyecto, agregala acá:
        'DIRS': [],
        'APP_DIRS': True,  # busca templates dentro de cada app (app/templates)
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# === BASE DE DATOS ===
# En .env podés usar:
#   DJANGO_DATABASE_URL=sqlite:///db.sqlite3
#   o Postgres: DJANGO_DATABASE_URL=postgres://USER:PASS@HOST:PORT/DB
DATABASES = {
    "default": env.db(
        "DJANGO_DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# === PASSWORD VALIDATORS ===
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# === I18N / TZ ===
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# === STATIC (CSS/JS/Images servidos por collectstatic) ===
# Django buscará dentro de cada app en "app/static/..."
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # destino de collectstatic
# Si querés una carpeta "static" a nivel proyecto, podés activar:
# STATICFILES_DIRS = [ BASE_DIR / "static" ]

# === MEDIA (archivos subidos por usuarios) ===
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# === MEDIA / S3 ===
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)

if USE_S3_MEDIA:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)

    # Firma v4
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE = "virtual"  # bucket.s3.amazonaws.com

    # Objetos privados + URLs firmadas y expirables
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True  # <--- URL firmada (por defecto ya es True, lo explicitamos)
    AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=86400)  # 24h

    # Cache agresiva en objetos (útil cuando la misma URL firmada se reutiliza por un tiempo)
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "public, max-age=31536000, s-maxage=31536000, immutable"
    }

    # Storage por defecto SOLO para MEDIA
    DEFAULT_FILE_STORAGE = "mi_blog.storages.MediaRootS3Boto3Storage"

    # No seteamos MEDIA_URL fija: django-storages generará pre-signed URLs dinámicas
    # (Si definís MEDIA_URL, igual se ignorará porque .url() devuelve la URL firmada completa)
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"



# === DEFAULT PK FIELD ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === FLAGS DE SEGURIDAD PARA PRODUCCIÓN (se leen del .env) ===
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE   = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=False)
# (Si usás HSTS en prod)
# SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)
# SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
# SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)


# === EMAILJS ===
EMAILJS_PUBLIC_KEY   = env("EMAILJS_PUBLIC_KEY", default="")
EMAILJS_SERVICE_ID   = env("EMAILJS_SERVICE_ID", default="")
EMAILJS_TEMPLATE_ID  = env("EMAILJS_TEMPLATE_ID", default="")

# habilitar nuestro context processor
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "propiedades.context_processors.emailjs_keys",
]
