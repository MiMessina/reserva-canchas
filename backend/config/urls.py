"""
URL configuration — SaaS Gestión de Canchas

Endpoints de Sprint 0:
  GET  /api/health/        — healthcheck sin autenticación
  POST /api/auth/login/    — obtener tokens JWT  body: {"email", "password"}
  POST /api/auth/refresh/  — renovar access token
  GET  /api/schema/        — esquema OpenAPI (YAML/JSON)
  GET  /api/docs/          — Swagger UI

FIX R-08: /api/auth/login/ usa EmailTokenObtainPairView (email como identificador,
no username). Contrato: POST {"email": "...", "password": "..."} → {access, refresh}.

Endpoints de negocio — Sprint 1:
  /api/courts/             — ABM canchas (GET list, POST create)
  /api/courts/{id}/        — GET retrieve, PATCH partial_update, DELETE (soft-delete)
  /api/schedule-blocks/    — ABM bloques horarios (GET list, POST create)
  /api/schedule-blocks/{id}/ — GET retrieve, PATCH partial_update, DELETE (soft-delete)
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView

from apps.tenants.views import HealthCheckView
from apps.users.views import EmailTokenObtainPairView

urlpatterns = [
    # Admin de Django (esquema public: gestión de tenants/dominios)
    path("admin/", admin.site.urls),

    # Healthcheck — sin autenticación requerida
    path("api/health/", HealthCheckView.as_view(), name="health-check"),

    # Autenticación JWT (ADR-002 + FIX R-08: login por email)
    # EmailTokenObtainPairView acepta {"email", "password"} → {access, refresh}
    path("api/auth/login/", EmailTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Courts y ScheduleBlocks — Sprint 1
    path("api/", include("apps.courts.urls")),

    # Swagger / OpenAPI (drf-spectacular)
    # AllowAny explícito para que no lo bloquee el DEFAULT_PERMISSION_CLASSES=IsAuthenticated
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="swagger-ui",
    ),
]
