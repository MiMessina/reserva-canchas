"""
Django settings — SaaS Gestión de Canchas (Multi-tenant)

Decisiones de arquitectura aplicadas:
  ADR-001: Multi-tenant por esquema PostgreSQL (django-tenants).
  ADR-002: Autenticación stateless con Simple JWT.
  ADR-007: Custom User en TENANT_APPS (usuarios aislados por complejo).
  ADR-009: Alta de tenant por management command (sin panel en MVP).
  ADR-010: CORS con django-cors-headers (frontend ↔ backend, orígenes por entorno).

Reglas inviolables:
  - TIME_ZONE = 'UTC', USE_TZ = True (fechas nunca en hora local).
  - Toda dependencia nueva requiere ADR.
  - Celery/Redis son Post-MVP: NO están instalados aquí.
"""

import os
from datetime import timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    # Valor de fallback solo para CI/test; en producción DEBE venir del entorno.
    "django-insecure-fallback-key-for-dev-only-change-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS_RAW = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,demo.localhost")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_RAW.split(",") if h.strip()]

# ---------------------------------------------------------------------------
# Multi-tenant (ADR-001)
#
# SHARED_APPS: apps cuyas tablas viven SOLO en el esquema `public`.
#   - django_tenants y apps.tenants deben ir primero.
#   - NO incluir apps.users aquí (ADR-007: users son por tenant).
#
# TENANT_APPS: apps cuyas tablas viven en el esquema de cada complejo.
#   - django.contrib.auth y contenttypes aquí (son dependencia de User).
#   - apps.users aquí: cada tenant tiene su propia tabla de usuarios.
#
# INSTALLED_APPS = SHARED_APPS + [apps de TENANT_APPS no ya en SHARED_APPS]
# (django-tenants requiere este patrón de deduplicación).
# ---------------------------------------------------------------------------

SHARED_APPS = [
    # django-tenants primero, obligatorio
    "django_tenants",
    # App tenants (Tenant + Domain viven en public)
    "apps.tenants",
    # Apps Django mínimas en el esquema public.
    # NOTA: admin, sessions y messages NO van aquí porque AUTH_USER_MODEL ('users.User')
    # vive en TENANT_APPS (ADR-007). Agregarlas en SHARED_APPS haría que admin intente
    # crear django_admin_log con FK a users_user, tabla que no existe en public.
    # Para una API JWT pura no se necesitan sessions ni messages en el esquema public.
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
]

TENANT_APPS = [
    # django.contrib.auth y contenttypes en cada esquema (necesario para PermissionsMixin)
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # Admin per-tenant: django_admin_log se crea junto a users_user en cada esquema
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Dominio de negocio por tenant
    "apps.users",    # Custom User (ADR-007: por tenant, no compartido)
    "apps.courts",   # ABM canchas + ScheduleBlock (Sprint 1+)
    "apps.bookings", # Motor de reservas (Sprint 1+)
    "apps.cashbox",  # Caja diaria (Sprint 1+)
    # Framework y documentación
    "rest_framework",
    "drf_spectacular",
    # CORS (ADR-010): debe estar en INSTALLED_APPS para que funcione el middleware
    "corsheaders",
]

# Deduplicación requerida por django-tenants:
# INSTALLED_APPS = SHARED_APPS + TENANT_APPS sin duplicar
INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

# ---------------------------------------------------------------------------
# Modelos de tenant (ADR-001 + ADR-007)
# ---------------------------------------------------------------------------
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

AUTH_USER_MODEL = "users.User"  # ADR-007: User en TENANT_APPS

# ---------------------------------------------------------------------------
# Base de datos (django-tenants con PostgreSQL)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.environ.get("POSTGRES_DB", "canchas_db"),
        "USER": os.environ.get("POSTGRES_USER", "canchas_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "canchas_pass"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    # TenantMainMiddleware DEBE ser el primero (resuelve el esquema por dominio)
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CorsMiddleware DEBE ir antes de CommonMiddleware (ADR-010).
    # Posición tras TenantMainMiddleware: el tenant ya está resuelto cuando
    # CORS evalúa el origen, lo cual es correcto.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Internacionalización y zona horaria
# REGLA: UTC en la DB. La conversión a America/Argentina/Buenos_Aires
# es responsabilidad del frontend/serializer (ver RULES.md).
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-ar"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # Obligatorio: todas las fechas timezone-aware

# ---------------------------------------------------------------------------
# Archivos estáticos
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Primary key por defecto
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework (ADR-002)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Por defecto todos los endpoints requieren autenticación.
        # Los endpoints públicos (grilla, health) anulan esto individualmente.
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Simple JWT (ADR-002)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,  # Sin blacklist en Sprint 0 (post-MVP)
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS — django-cors-headers (ADR-010)
#
# CORS_ALLOWED_ORIGINS se lee de la variable de entorno DJANGO_CORS_ALLOWED_ORIGINS,
# separada por comas. Default de desarrollo: el servidor de Vite en localhost:5173.
#
# NUNCA usar CORS_ALLOW_ALL_ORIGINS=True (ver ADR-010).
# En producción la variable debe contener únicamente el dominio real del complejo.
# ---------------------------------------------------------------------------
_cors_origins_raw = os.environ.get(
    "DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173"
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "CanchaYA API",
    "DESCRIPTION": (
        "API REST para el SaaS multi-tenant de gestión y reserva de complejos deportivos. "
        "Autenticación: Bearer JWT. Cada tenant opera en su propio esquema PostgreSQL."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {"email": "milton.messina@bue.edu.ar"},
    "LICENSE": {"name": "Propietario"},
    "TAGS": [
        {"name": "health", "description": "Estado del servicio"},
        {"name": "auth", "description": "Autenticación JWT (login / refresh)"},
        {"name": "courts", "description": "ABM de canchas y horarios"},
        {"name": "bookings", "description": "Motor de reservas"},
        {"name": "cashbox", "description": "Caja diaria"},
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}

# ---------------------------------------------------------------------------
# Logging básico
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
