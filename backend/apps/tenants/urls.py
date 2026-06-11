"""
URLs de la app tenants.

Endpoints registrados:
  GET  /api/settings/   — configuración pública del complejo (AllowAny)
  PATCH /api/settings/  — actualizar configuración (solo tenant_admin)

El healthcheck se registra directamente en config/urls.py porque es
un endpoint de infraestructura (no de negocio de tenants).

ADR-009: alta de tenant por management command, sin panel web en MVP.
"""

from django.urls import path

from apps.tenants.views import ComplexSettingsView

urlpatterns = [
    path("settings/", ComplexSettingsView.as_view(), name="complex-settings"),
]
