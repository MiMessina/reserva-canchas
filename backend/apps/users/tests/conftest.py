"""
conftest.py — fixtures para tests de la app users.

QA: agregar aquí fixtures de usuarios de prueba para los tests de:
  - Autenticación JWT (login, refresh).
  - Permisos RBAC (player no puede confirmar, operator puede confirmar).
  - Aislamiento: usuario de tenant A no se autentica en tenant B.
"""

import pytest


@pytest.fixture(autouse=True)
def disable_throttling(settings):
    """
    Desactiva el throttling de DRF para todos los tests de users.

    El rate limiting usa LocMemCache cuyo estado persiste entre tests en la
    misma sesión de pytest. Sin esto, llamadas repetidas a /api/auth/login/
    en setUp() generan 429 al correr la suite completa.
    """
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
