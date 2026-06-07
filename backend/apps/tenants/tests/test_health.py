"""
Tests del healthcheck — GET /api/health/

Cobertura Sprint 0:
  - El endpoint responde 200.
  - El body contiene {"status": "ok"}.
  - No requiere autenticación (AllowAny).

Nota: estos tests usan django-tenants TenantTestCase para que el middleware
de tenant no rompa la resolución del request en el test runner.
"""

import pytest
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient


class TestHealthCheck(TenantTestCase):
    """
    Tests del endpoint GET /api/health/

    TenantTestCase crea automáticamente un tenant de prueba ('test')
    y lo activa para el scope de la clase.
    """

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

    def test_health_returns_200(self):
        """El healthcheck responde HTTP 200."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_returns_status_ok(self):
        """El body del healthcheck contiene {"status": "ok"}."""
        response = self.client.get("/api/health/")
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ok")

    def test_health_no_auth_required(self):
        """El healthcheck no requiere token JWT ni sesión."""
        # Sin ningún header de autenticación, debe responder 200
        response = self.client.get("/api/health/", HTTP_AUTHORIZATION="")
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Los tests de aislamiento entre dos tenants viven en:
#   apps/tenants/tests/test_tenant_isolation.py — TestTenantIsolation
# ---------------------------------------------------------------------------
