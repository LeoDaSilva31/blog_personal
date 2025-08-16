# settings.py
from pathlib import Path
import os
import environ
import dj_database_url

# === BASE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === VARIABLES DE ENTORNO ===
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
# Cargar .env solo en desarrollo/local (en Render no hace falta)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# === SEGURIDAD / CORE ===
SECRET_KEY = env("DJANGO_SECRET_KEY", default="!!!-cambia-esto-en-produccion-!!!")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = set(env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"]))
CSRF_TRUSTED_ORIGINS = set(env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[]))

# Host externo generado por Render (se setea automáticamente)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.add(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.add(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Tus dominios personalizados (agregalos fijo)
ALLOWED_HOSTS.update(["leods-blog.org", "www.leods-blog.org"])
CSRF_TRUSTED_ORIGINS.update(["https://leods-blog.org", "https://www.leods-blog.org"])

# En Render forzamos DEBUG=False salvo que explícitamente lo actives
if os.environ.get("RENDER"):
    DEBUG = False

ALLOWED_HOSTS = list(ALLOWED_HOSTS)
CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS)

# === APPS INSTALADAS ===
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Postgres extensions (seguro incluirlo aunque uses SQLite en dev)
    "django.contrib.postgres",

    # Terceros
    "django.contrib.humanize",
    "storages",

    # Apps propias
    "blog",
    "landingpage",
    "propiedades",
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise inmediatamente después de SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# === URLCONF / WSGI / ASGI ===
ROOT_URLCONF = "mi_blog.urls"
WSGI_APPLICATION = "mi_blog.wsgi.application"
ASGI_APPLICATION = "mi_blog.asgi.application"

# === TEMPLATES ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # Podés agregar una carpeta de templates a nivel proyecto si la usás
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
# Agrego tu context processor
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "propiedades.context_processors.emailjs_keys",
]

# === BASE DE DATOS ===
# Render provee DATABASE_URL; localmente caemos a SQLite.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=True,   # <— fuerza TLS aunque falte en la URL
    )
}

# === PASSWORD VALIDATORS ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === I18N / TZ ===
LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

# === STATIC ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise con STORAGES (recomendado en Django 5)
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    # Por defecto, archivos de usuario (MEDIA) quedan en disco local
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}

# === MEDIA (archivos subidos) ===
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# === MEDIA / S3 (opcional; activá USE_S3_MEDIA=True en env para usarlo) ===
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)
if USE_S3_MEDIA:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)

    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE = "virtual"  # bucket.s3.amazonaws.com
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=86400)  # 24h
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "public, max-age=31536000, s-maxage=31536000, immutable"
    }

    # Storage por defecto SOLO para MEDIA → usa tus pre-signed URLs
    STORAGES["default"] = {"BACKEND": "mi_blog.storages.MediaRootS3Boto3Storage"}

# === DEFAULT PK FIELD ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === FLAGS DE SEGURIDAD (ajustables por env) ===
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=False)
# HSTS si lo querés activar en prod:
# SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)
# SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
# SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)

# === EMAILJS (si lo usás en templates)
EMAILJS_PUBLIC_KEY  = env("EMAILJS_PUBLIC_KEY", default="")
EMAILJS_SERVICE_ID  = env("EMAILJS_SERVICE_ID", default="")
EMAILJS_TEMPLATE_ID = env("EMAILJS_TEMPLATE_ID", default="")
