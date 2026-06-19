"""
Tests de autenticación JWT — POST /api/auth/login/

FIX R-08: el login se realiza con email+password (no username+password).
Contrato: POST /api/auth/login/ body={"email": "...", "password": "..."} → {access, refresh}.

Cobertura Sprint 0:
  - Login con email+password válidos retorna access + refresh tokens.
  - Login con contraseña incorrecta retorna 401.
  - Login con email inexistente retorna 401.
  - Login con campo `username` (contrato incorrecto) retorna 400 (campo requerido `email`).
  - Refresh con token válido retorna nuevo access token.
  - El payload del JWT contiene el claim `role` (agregado por EmailTokenObtainPairSerializer).

QA: expandir con:
  - Test de aislamiento: usuario del tenant A no puede autenticarse en tenant B.
  - Test de permisos: player no puede acceder a endpoints de operator.
"""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.users.models import User


class TestJWTAuth(TenantTestCase):
    """Tests de autenticación JWT bajo el esquema del tenant de prueba."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Crear usuario de prueba en el esquema del tenant (sin username — FIX R-08)
        self.user = User.objects.create_user(
            email="player@test.localhost",
            password="testpass123",
            role=User.Role.PLAYER,
        )

    def test_login_with_valid_credentials_returns_tokens(self):
        """Login exitoso con email+password retorna access y refresh tokens."""
        response = self.client.post(
            "/api/auth/login/",
            {"email": "player@test.localhost", "password": "testpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_login_with_invalid_password_returns_401(self):
        """Login con contraseña incorrecta retorna 401."""
        response = self.client.post(
            "/api/auth/login/",
            {"email": "player@test.localhost", "password": "wrongpassword"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_with_nonexistent_email_returns_401(self):
        """Login con email inexistente retorna 401."""
        response = self.client.post(
            "/api/auth/login/",
            {"email": "nobody@test.localhost", "password": "nopass"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_with_username_field_returns_400(self):
        """
        Login con el campo `username` en lugar de `email` retorna 400.
        Valida que el contrato es estrictamente email+password (FIX R-08).
        """
        response = self.client.post(
            "/api/auth/login/",
            {"username": "player@test.localhost", "password": "testpass123"},
            content_type="application/json",
        )
        # SimpleJWT devuelve 400 cuando falta el campo requerido (`email`)
        self.assertEqual(response.status_code, 400)

    def test_refresh_with_valid_token(self):
        """El token de refresh válido retorna un nuevo access token."""
        # Primero obtener tokens
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "player@test.localhost", "password": "testpass123"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        refresh_token = login_response.json()["refresh"]

        # Usar el refresh token
        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh_token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access", data)

    def test_jwt_payload_contains_role_claim(self):
        """
        El payload del JWT contiene el claim `role` (agregado por
        EmailTokenObtainPairSerializer.get_token).
        Permite que el frontend adapte la UI sin llamadas extra.
        La validación de permisos siempre ocurre en el backend.
        """
        import base64
        import json

        response = self.client.post(
            "/api/auth/login/",
            {"email": "player@test.localhost", "password": "testpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        access_token = response.json()["access"]

        # Decodificar el payload (sin verificar firma — solo para el test)
        payload_b64 = access_token.split(".")[1]
        # Agregar padding si es necesario
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        self.assertIn("role", payload)
        self.assertEqual(payload["role"], User.Role.PLAYER)

    def test_tenant_admin_role_is_accessible_after_login(self):
        """El admin puede loguearse y el access token está presente en la respuesta."""
        admin_user = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@test.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_login_fails_when_tenant_is_inactive(self):
        """
        Login de un usuario válido falla con 401 y código TENANT_INACTIVE
        cuando el tenant está desactivado (is_active=False).

        Verifica la regla de negocio: un tenant inactivo no permite login
        de sus usuarios (aunque el user.is_active sea True).
        """
        from apps.tenants.models import Tenant
        from django.db import connection

        # Desactivar el tenant activo del test
        tenant = Tenant.objects.get(schema_name=connection.schema_name)
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])

        try:
            response = self.client.post(
                "/api/auth/login/",
                {"email": "player@test.localhost", "password": "testpass123"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            data = response.json()
            # El error puede venir como {"detail": {...}} o directamente como el dict
            # dependiendo de cómo SimpleJWT serializa AuthenticationFailed con un dict.
            # Verificamos que el código TENANT_INACTIVE esté presente en la respuesta.
            response_str = str(data)
            self.assertIn("TENANT_INACTIVE", response_str)
        finally:
            # Restaurar el tenant activo para no romper otros tests
            tenant.is_active = True
            tenant.save(update_fields=["is_active"])

    def test_login_succeeds_when_tenant_is_active(self):
        """
        Login de un usuario válido retorna 200 cuando el tenant está activo.

        Verifica que la validación de tenant inactivo no bloquea el caso normal.
        """
        from apps.tenants.models import Tenant
        from django.db import connection

        # Confirmar que el tenant está activo (estado normal del test)
        tenant = Tenant.objects.get(schema_name=connection.schema_name)
        self.assertTrue(tenant.is_active, "El tenant debe estar activo para este test")

        response = self.client.post(
            "/api/auth/login/",
            {"email": "player@test.localhost", "password": "testpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
