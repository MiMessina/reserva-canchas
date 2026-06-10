"""
conftest.py — fixtures para tests de la app cashbox.

Desactiva el throttling de DRF para evitar 429 en llamadas repetidas a
/api/auth/login/ durante el setUp() de TenantTestCase cuando se corren
todos los tests seguidos (mismo patrón que bookings/tests/conftest.py).
"""

import pytest


@pytest.fixture(autouse=True)
def disable_throttling(settings):
    """
    Desactiva el throttling de DRF en todos los tests de cashbox.

    El rate limiting activado en el security review usa LocMemCache, cuyo estado
    persiste entre tests en la misma sesión de pytest. Esto causa 429 en llamadas
    repetidas a /api/auth/login/ durante el setUp() de TenantTestCase.
    """
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
