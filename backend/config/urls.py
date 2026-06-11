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

Endpoints de configuración del complejo:
  GET  /api/settings/   — configuración pública del complejo (AllowAny, acotada al tenant)
  PATCH /api/settings/  — actualizar configuración (solo tenant_admin)

Endpoints de negocio — Sprint 1:
  /api/courts/             — ABM canchas (GET list, POST create)
  /api/courts/{id}/        — GET retrieve, PATCH partial_update, DELETE (soft-delete)
  /api/schedule-blocks/    — ABM bloques horarios (GET list, POST create)
  /api/schedule-blocks/{id}/ — GET retrieve, PATCH partial_update, DELETE (soft-delete)

Endpoints de negocio — Sprint 2 (motor de reservas):
  /api/bookings/                        — GET listado, POST crear reserva
  /api/bookings/{id}/                   — GET detalle
  /api/bookings/{id}/confirm/           — POST confirmar (operator/admin)
  /api/bookings/{id}/cancel/            — POST cancelar
  /api/bookings/{id}/complete/          — POST completar (operator/admin)
  /api/bookings/daily-grid/             — GET grilla multi-cancha del día (operator/admin)
  /api/cash-movements/                  — GET caja diaria (operator/admin)
  /api/cash-movements/export/           — GET exportar caja CSV (operator/admin)
  /api/courts/{id}/availability/        — GET grilla de disponibilidad (AllowAny)

Endpoints de usuarios — Sprint 1+:
  /api/users/me/                        — GET perfil propio (IsAuthenticated)
  /api/users/                           — GET listado / POST crear operador (IsTenantAdmin)
  /api/users/{id}/                      — GET detalle / PATCH editar / DELETE soft-delete (IsTenantAdmin)
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

    # Configuración del complejo (ComplexSettings) — singleton por tenant
    path("api/", include("apps.tenants.urls")),

    # Users (gestión de operadores, perfil propio) — Sprint 1+
    path("api/", include("apps.users.urls")),

    # Courts y ScheduleBlocks — Sprint 1
    path("api/", include("apps.courts.urls")),

    # Bookings (motor de reservas) y CashMovements — Sprint 2
    path("api/", include("apps.bookings.urls")),

    # CashSessions (apertura/cierre de caja diaria) — Sprint 3
    path("api/", include("apps.cashbox.urls")),

    # Agente IA conversacional (ADR-012) — Sprint 3
    path("api/", include("apps.agent.urls")),

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
