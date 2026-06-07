"""
conftest.py raíz — Backend SaaS Gestión de Canchas

Fixtures y configuración global de pytest para todos los tests del backend.

Referencias:
  - pytest.ini: DJANGO_SETTINGS_MODULE=config.settings
  - docs/SPRINT_0.md §7: tests mínimos (healthcheck, login, aislamiento)
  - docs/RBAC.md §7: tests mínimos de permisos

Nota sobre django-tenants y pytest:
  Los tests que necesitan acceder a datos de un tenant deben usar
  django_tenants.test.cases.TenantTestCase (TestCase-based) o
  fixturas que setean el schema activo con schema_context().

  pytest-django con django-tenants requiere cuidado especial:
  - TenantTestCase maneja automáticamente la creación del schema 'test'.
  - Para fixtures pytest puras se puede usar:
      from django_tenants.utils import schema_context
      with schema_context('test'):
          ...
"""

import django
import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """
    Fixture de setup de DB para la sesión de tests.
    django-tenants crea el schema 'test' automáticamente con TenantTestCase.
    """
    pass
