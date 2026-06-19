"""
URL configuration para el esquema `public` (PUBLIC_SCHEMA_URLCONF).

Estos endpoints solo responden cuando django-tenants determina que el host
corresponde al esquema `public` (ej: localhost, platform.localhost).

Endpoints de platform (ADR-013):
  POST /api/platform/auth/login/    — login JWT para system_admin (contra auth.User)
  POST /api/platform/auth/refresh/  — refresh del token
  GET  /api/platform/tenants/       — listar tenants
  POST /api/platform/tenants/       — crear tenant
  GET  /api/platform/tenants/{id}/  — detalle
  PATCH /api/platform/tenants/{id}/ — editar nombre
  POST /api/platform/tenants/{id}/toggle/ — activar / desactivar

Endpoints de infraestructura (disponibles en public también):
  GET /api/health/ — healthcheck

Aislamiento de JWT (ADR-013):
  El login aquí usa django.contrib.auth.User (superuser Django, esquema public).
  El login de tenant usa apps.users.User (custom User, esquema tenant).
  Los dos "sabores" de JWT no son intercambiables porque usan USER_ID_CLAIM
  con el mismo nombre pero distintos modelos y esquemas.
"""

from django.urls import include, path

from apps.tenants.views import HealthCheckView
from config.views_platform_auth import PlatformTokenObtainPairView, PlatformTokenRefreshView

urlpatterns = [
    # Healthcheck (también disponible en el esquema public)
    path("api/health/", HealthCheckView.as_view(), name="public-health-check"),

    # Auth del system_admin — JWT contra django.contrib.auth.User
    path(
        "api/platform/auth/login/",
        PlatformTokenObtainPairView.as_view(),
        name="platform-token-obtain",
    ),
    path(
        "api/platform/auth/refresh/",
        PlatformTokenRefreshView.as_view(),  # valida iss='platform' antes de refrescar
        name="platform-token-refresh",
    ),

    # Endpoints de gestión de tenants
    path("api/platform/", include("apps.tenants.urls_platform")),
]
