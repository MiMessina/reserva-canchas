"""
URLs del Panel de System Admin (ADR-013).

Registra el TenantViewSet bajo /api/platform/tenants/.
Este archivo se incluye desde config/urls_public.py (PUBLIC_SCHEMA_URLCONF),
que solo aplica para el esquema `public` de PostgreSQL.

Endpoints resultantes:
  GET    /api/platform/tenants/              — listar
  POST   /api/platform/tenants/              — crear
  GET    /api/platform/tenants/{id}/         — detalle
  PATCH  /api/platform/tenants/{id}/         — editar nombre
  POST   /api/platform/tenants/{id}/toggle/  — activar / desactivar
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenants.views_platform import TenantViewSet

router = DefaultRouter()
router.register(r"tenants", TenantViewSet, basename="platform-tenants")

urlpatterns = [
    path("", include(router.urls)),
]
