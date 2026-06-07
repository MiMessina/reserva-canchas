"""
conftest.py — fixtures para tests de la app users.

QA: agregar aquí fixtures de usuarios de prueba para los tests de:
  - Autenticación JWT (login, refresh).
  - Permisos RBAC (player no puede confirmar, operator puede confirmar).
  - Aislamiento: usuario de tenant A no se autentica en tenant B.
"""
