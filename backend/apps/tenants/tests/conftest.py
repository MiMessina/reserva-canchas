"""
conftest.py — fixtures compartidos para tests de la app tenants.

Para el test de aislamiento entre dos tenants ver:
  apps/tenants/tests/test_tenant_isolation.py — TestTenantIsolation

Nota sobre el patrón de tests multi-tenant:
  Los tests que necesitan el contexto de un tenant usan TenantTestCase
  (herencia de unittest.TestCase), no fixtures de pytest, porque
  TenantTestCase gestiona el ciclo de vida del esquema de prueba.

  El fixture tenant_client de abajo aplica solo a tests pytest puros
  que necesitan un cliente HTTP aislado (no a TenantTestCase).

Ver SPRINT_0.md §7 y RBAC.md §7.
"""

import pytest
from django_tenants.test.client import TenantClient

from apps.tenants.models import Domain, Tenant


@pytest.fixture
def tenant_client(db):
    """
    Fixture pytest: crea un tenant de prueba temporal y retorna su TenantClient.

    Uso (en tests pytest puros, no en TenantTestCase):
        def test_algo(tenant_client):
            response = tenant_client.get("/api/health/")
            assert response.status_code == 200

    Nota: para tests de aislamiento entre DOS tenants, usar
    TestTenantIsolation en test_tenant_isolation.py, que opera
    con TenantTestCase y gestiona self.tenant + tenant_b.
    """
    schema = "pytest_tenant_fixture"
    domain_name = "pytest-fixture.localhost"

    tenant = Tenant(schema_name=schema, name="Tenant Fixture (pytest)")
    tenant.save()

    Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

    client = TenantClient(tenant)

    yield client

    # Teardown: eliminar dominio y tenant para no contaminar otros tests
    Domain.objects.filter(tenant=tenant).delete()
    try:
        tenant.delete(force_drop=True)
    except Exception:
        pass
