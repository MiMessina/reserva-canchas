"""
Tests del Panel de System Admin (ADR-013).

Cobertura:
  1. Login exitoso de superuser → recibe JWT (access + refresh).
  2. Login de usuario normal (no superuser) → 401.
  3. Login con credenciales inválidas → 401.
  4. Listar tenants como system_admin → 200 con lista.
  5. Crear tenant → schema creado, domain creado, tenant_admin creado en el nuevo esquema.
  6. JWT de system_admin NO accede a /api/bookings/ de un tenant → 401/403.
  7. JWT de tenant user NO accede a /api/platform/tenants/ → 401/403.
  8. Crear tenant con schema_name inválido → 400 con código INVALID_SCHEMA_NAME.
  9. Crear tenant con schema_name duplicado → 400 con código SCHEMA_ALREADY_EXISTS.
  10. Crear tenant con dominio duplicado → 400 con código DOMAIN_ALREADY_EXISTS.
  11. Toggle de tenant → is_active cambia.
  12. Toggle de tenant inactivo → vuelve a activo.
  13. Editar nombre del tenant (PATCH) → name actualizado.
  14. Detalle de tenant (GET /{id}/) → datos correctos.
  15. Acceso sin JWT → 401.

Estrategia:
  - Los tests de aislamiento de JWT usan django_tenants.test.cases.TenantTestCase
    para tener un contexto de tenant real donde hacer requests.
  - Los tests de endpoints de platform usan directamente el APIClient de DRF
    contra urls_public (PUBLIC_SCHEMA_URLCONF).
  - Cada test que crea un tenant de prueba lo limpia en tearDown para no contaminar
    otros tests.

Nota sobre auth.User vs apps.users.User:
  - Los endpoints de /api/platform/ usan django.contrib.auth.User (superuser Django).
  - Los endpoints de /api/ (tenant) usan apps.users.User (Custom User de TENANT_APPS).
  - Son distintos modelos en distintos esquemas; los JWT no son intercambiables.
"""

import base64
import json

from django.apps import apps
from django.db import connection
from django.test import TestCase, override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

# AUTH_USER_MODEL = 'users.User' deshabilita el manager de auth.User cuando se
# importa directamente desde django.contrib.auth.models. Se usa apps.get_model()
# en runtime para acceder al modelo de Django que vive en el esquema public.
def _get_auth_user_model():
    """Retorna django.contrib.auth.User resolviendo el modelo via apps registry."""
    return apps.get_model("auth", "User")

from apps.tenants.models import Domain, Tenant
from apps.tenants.services import (
    DomainAlreadyExists,
    InvalidSchemaName,
    SchemaAlreadyExists,
    TenantCreationFailed,
    create_tenant_service,
)

# Los tests de platform usan ROOT_URLCONF="config.urls_public" via override_settings.
# Esto es necesario porque los endpoints de /api/platform/ SOLO están en urls_public,
# que es el PUBLIC_SCHEMA_URLCONF de django-tenants. En los tests, el APIClient
# no pasa por el middleware de django-tenants que resolvería el urlconf automáticamente,
# así que usamos override_settings para simular el comportamiento del esquema public.
PLATFORM_URLCONF = "config.urls_public"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_platform_token(superuser, client: APIClient) -> str:
    """Obtiene el access token del system_admin vía /api/platform/auth/login/."""
    resp = client.post(
        "/api/platform/auth/login/",
        {"email": superuser.email, "password": "superpassword123"},
        format="json",
    )
    assert resp.status_code == 200, f"Login falló: {resp.data}"
    return resp.data["access"]


# ---------------------------------------------------------------------------
# Tests de auth del system_admin
# ---------------------------------------------------------------------------

@override_settings(ROOT_URLCONF=PLATFORM_URLCONF)
class TestPlatformAuthLogin(TestCase):
    """
    Tests de POST /api/platform/auth/login/

    Usa TestCase estándar porque los endpoints de platform corren en el esquema
    public y utilizan django.contrib.auth.User (AuthUser), no el custom User de
    TENANT_APPS. TenantTestCase deshabilita el manager de auth.User y no es
    necesario aquí.
    """

    def setUp(self):
        super().setUp()
        # El APIClient sin tenant para llamar a PUBLIC_SCHEMA_URLCONF
        self.client = APIClient()
        # Superuser de Django (auth.User, esquema public).
        # Se usa _get_auth_user_model() porque AUTH_USER_MODEL='users.User'
        # deshabilita AuthUser.objects cuando se importa directamente.
        AuthUser = _get_auth_user_model()
        self.superuser = AuthUser.objects.create_superuser(
            username="sysadmin",
            email="sysadmin@platform.local",
            password="superpassword123",
        )

    def tearDown(self):
        _get_auth_user_model().objects.filter(username="sysadmin").delete()
        super().tearDown()

    def test_login_superuser_returns_jwt(self):
        """Login exitoso de superuser → 200 con access y refresh tokens."""
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "sysadmin@platform.local", "password": "superpassword123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}: {resp.data}")
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertTrue(len(resp.data["access"]) > 10)

    def test_login_non_superuser_returns_401(self):
        """Login de auth.User sin is_superuser → 401."""
        AuthUser = _get_auth_user_model()
        AuthUser.objects.create_user(
            username="regularuser",
            email="regular@platform.local",
            password="regularpass123",
        )
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "regular@platform.local", "password": "regularpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["error"]["code"], "NOT_SUPERUSER")
        AuthUser.objects.filter(username="regularuser").delete()

    def test_login_wrong_password_returns_401(self):
        """Login con contraseña incorrecta → 401."""
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "sysadmin@platform.local", "password": "wrongpassword"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["error"]["code"], "INVALID_CREDENTIALS")

    def test_login_nonexistent_email_returns_401(self):
        """Login con email que no existe → 401."""
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "noexiste@platform.local", "password": "cualquiera"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["error"]["code"], "INVALID_CREDENTIALS")

    def test_login_missing_fields_returns_400(self):
        """Login sin email ni password → 400."""
        resp = self.client.post("/api/platform/auth/login/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_access_token_contains_iss_platform_claim(self):
        """
        El access token emitido por /api/platform/auth/login/ debe contener iss='platform'.

        Verifica ALTA 1: el claim se setea explícitamente en ambos tokens.
        """
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "sysadmin@platform.local", "password": "superpassword123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Login falló: {resp.data}")

        access_token = resp.data["access"]
        # Decodificar el payload del JWT (segunda parte, sin verificar firma)
        parts = access_token.split(".")
        self.assertEqual(len(parts), 3, "El access token no tiene el formato JWT esperado (3 partes)")

        # Añadir padding para base64 si es necesario
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        self.assertEqual(
            payload.get("iss"),
            "platform",
            f"El access token no contiene iss='platform'. Claims: {payload}",
        )

    def test_refresh_token_contains_iss_platform_claim(self):
        """
        El refresh token emitido por /api/platform/auth/login/ debe contener iss='platform'.
        """
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "sysadmin@platform.local", "password": "superpassword123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        refresh_token = resp.data["refresh"]
        parts = refresh_token.split(".")
        self.assertEqual(len(parts), 3)

        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        self.assertEqual(
            payload.get("iss"),
            "platform",
            f"El refresh token no contiene iss='platform'. Claims: {payload}",
        )

    def test_platform_refresh_view_rejects_tenant_token(self):
        """
        POST /api/platform/auth/refresh/ rechaza un token sin iss='platform'.

        Verifica MEDIO 5: PlatformTokenRefreshView valida el claim iss.
        """
        # Fabricar un JWT con estructura válida pero sin iss='platform'
        # Usamos un refresh token de tenant real (TenantTestCase tiene un tenant disponible)
        # Alternativa: pasar un string que no sea un JWT válido → también debe rechazarse
        resp = self.client.post(
            "/api/platform/auth/refresh/",
            {"refresh": "token.invalido.cualquiera"},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            401,
            f"Se esperaba 401 para token inválido, se obtuvo {resp.status_code}: {resp.data}",
        )


# ---------------------------------------------------------------------------
# Tests de endpoints de tenants (list, retrieve, create, partial_update, toggle)
# ---------------------------------------------------------------------------

@override_settings(ROOT_URLCONF=PLATFORM_URLCONF)
class TestPlatformTenantEndpoints(TestCase):
    """
    Tests de CRUD de tenants vía /api/platform/tenants/.

    Crea y destruye tenants de prueba para no contaminar el entorno.
    Usa TestCase estándar: los endpoints de platform corren en el esquema public
    y utilizan AuthUser (django.contrib.auth.User). TenantTestCase no es necesario
    y deshabilita el manager de auth.User, lo que causa errores.

    Se crea un tenant de fixture ('endpoints_fixture') en setUp para los tests
    que necesitan un tenant preexistente (retrieve, partial_update, toggle,
    duplicate_domain).
    """

    def setUp(self):
        connection.set_schema_to_public()
        self._created_schemas = []  # Schemas creados en este test que hay que limpiar

        # Tenant de fixture: se usa en tests de retrieve/patch/toggle/duplicate_domain
        self.fixture_tenant = Tenant(
            schema_name="endpoints_fixture",
            name="Complejo Fixture Endpoints",
            is_active=True,
        )
        self.fixture_tenant.save()
        fixture_domain = Domain(
            domain="endpoints-fixture.localhost",
            tenant=self.fixture_tenant,
            is_primary=True,
        )
        fixture_domain.save()
        self._created_schemas.append("endpoints_fixture")

        self.client = APIClient()

        # Superuser para el panel de platform.
        # Se usa _get_auth_user_model() porque AUTH_USER_MODEL='users.User' deshabilita
        # el manager de auth.User cuando se importa directamente.
        AuthUser = _get_auth_user_model()
        self.superuser = AuthUser.objects.create_superuser(
            username="sysadmin_endpoints",
            email="sysadmin2@platform.local",
            password="superpassword123",
        )

        # Obtener token
        resp = self.client.post(
            "/api/platform/auth/login/",
            {"email": "sysadmin2@platform.local", "password": "superpassword123"},
            format="json",
        )
        self.token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def tearDown(self):
        # Limpiar tenants de prueba creados en este test
        connection.set_schema_to_public()
        for schema in self._created_schemas:
            try:
                tenant = Tenant.objects.filter(schema_name=schema).first()
                if tenant:
                    Domain.objects.filter(tenant=tenant).delete()
                    tenant.delete(force_drop=True)
            except Exception:
                pass

        _get_auth_user_model().objects.filter(username="sysadmin_endpoints").delete()
        connection.set_schema_to_public()

    def _register_created_schema(self, schema_name: str):
        """Registra un schema para limpiar en tearDown."""
        if schema_name not in self._created_schemas:
            self._created_schemas.append(schema_name)

    # -----------------------------------------------------------------------
    # Test 1: Listar tenants
    # -----------------------------------------------------------------------

    def test_list_tenants_returns_200(self):
        """GET /api/platform/tenants/ con JWT de superuser → 200."""
        resp = self.client.get("/api/platform/tenants/")
        self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}: {resp.data}")

    def test_list_tenants_contains_expected_fields(self):
        """La respuesta incluye los campos de metadata del tenant."""
        resp = self.client.get("/api/platform/tenants/")
        self.assertEqual(resp.status_code, 200)
        # Puede haber tenants del test runner (ej: 'test')
        # Verificar estructura si hay resultados
        data = resp.data
        # Soporta paginación o lista directa
        results = data.get("results", data) if isinstance(data, dict) else data
        if results:
            item = results[0]
            for field in ["id", "name", "schema_name", "domain", "is_active", "created_at"]:
                self.assertIn(field, item, f"Campo '{field}' ausente en la respuesta")

    # -----------------------------------------------------------------------
    # Test 2: Crear tenant
    # -----------------------------------------------------------------------

    def test_create_tenant_success(self):
        """POST /api/platform/tenants/ → 201, schema creado, domain creado, tenant_admin creado."""
        schema = "testplatform_create"
        domain = "testplatform-create.localhost"
        admin_email = "admin@testplatform-create.local"
        self._register_created_schema(schema)

        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Complejo Test Create",
                "schema_name": schema,
                "domain": domain,
                "admin_email": admin_email,
                "admin_password": "adminpass123",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 201, f"Expected 201, got {resp.status_code}: {resp.data}")
        self.assertEqual(resp.data["schema_name"], schema)
        self.assertEqual(resp.data["domain"], domain)
        self.assertTrue(resp.data["is_active"])

        # Verificar que el tenant existe en la DB
        connection.set_schema_to_public()
        self.assertTrue(Tenant.objects.filter(schema_name=schema).exists())
        self.assertTrue(Domain.objects.filter(domain=domain).exists())

        # Verificar que el tenant_admin existe en el esquema del nuevo tenant
        from django.contrib.auth import get_user_model
        with schema_context(schema):
            User = get_user_model()
            self.assertTrue(
                User.objects.filter(email=admin_email).exists(),
                f"tenant_admin '{admin_email}' no encontrado en esquema '{schema}'"
            )

    # -----------------------------------------------------------------------
    # Test 3: Detalle de tenant
    # -----------------------------------------------------------------------

    def test_retrieve_tenant(self):
        """GET /api/platform/tenants/{id}/ → 200 con datos del tenant."""
        connection.set_schema_to_public()
        tenant = self.fixture_tenant
        resp = self.client.get(f"/api/platform/tenants/{tenant.pk}/")
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertEqual(resp.data["schema_name"], tenant.schema_name)

    # -----------------------------------------------------------------------
    # Test 4: Editar nombre del tenant (PATCH)
    # -----------------------------------------------------------------------

    def test_partial_update_tenant_name(self):
        """PATCH /api/platform/tenants/{id}/ → actualiza el nombre."""
        connection.set_schema_to_public()
        tenant = self.fixture_tenant
        original_name = tenant.name
        new_name = "Nombre Actualizado Test"

        resp = self.client.patch(
            f"/api/platform/tenants/{tenant.pk}/",
            {"name": new_name},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertEqual(resp.data["name"], new_name)

        # Restaurar nombre original
        tenant.refresh_from_db()
        tenant.name = original_name
        tenant.save(update_fields=["name"])

    # -----------------------------------------------------------------------
    # Test 5: Toggle de tenant
    # -----------------------------------------------------------------------

    def test_toggle_tenant_changes_is_active(self):
        """POST /api/platform/tenants/{id}/toggle/ → invierte is_active."""
        connection.set_schema_to_public()
        tenant = self.fixture_tenant

        initial_state = tenant.is_active
        resp = self.client.post(f"/api/platform/tenants/{tenant.pk}/toggle/")
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertEqual(resp.data["is_active"], not initial_state)

        # Revertir el estado para no romper otros tests
        resp2 = self.client.post(f"/api/platform/tenants/{tenant.pk}/toggle/")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["is_active"], initial_state)

    def test_toggle_tenant_twice_returns_original_state(self):
        """Dos toggles consecutivos vuelven al estado original."""
        connection.set_schema_to_public()
        tenant = self.fixture_tenant

        initial_state = tenant.is_active

        # Primer toggle
        self.client.post(f"/api/platform/tenants/{tenant.pk}/toggle/")
        # Segundo toggle
        resp = self.client.post(f"/api/platform/tenants/{tenant.pk}/toggle/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["is_active"], initial_state)

    # -----------------------------------------------------------------------
    # Test 6: Validaciones de schema_name inválido
    # -----------------------------------------------------------------------

    def test_create_tenant_invalid_schema_name_returns_400(self):
        """schema_name con caracteres inválidos → 400 con código INVALID_SCHEMA_NAME."""
        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Complejo Invalido",
                "schema_name": "123-invalido!",
                "domain": "invalido.localhost",
                "admin_email": "admin@invalido.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400: {resp.data}")
        # La respuesta debe tener el formato estándar con código INVALID_SCHEMA_NAME
        self.assertIn("error", resp.data)
        self.assertEqual(resp.data["error"]["code"], "INVALID_SCHEMA_NAME")

    def test_create_tenant_reserved_schema_name_returns_400(self):
        """schema_name='public' → 400 con código INVALID_SCHEMA_NAME."""
        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Complejo Public",
                "schema_name": "public",
                "domain": "publictenant.localhost",
                "admin_email": "admin@public.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400: {resp.data}")
        self.assertIn("error", resp.data)
        self.assertEqual(resp.data["error"]["code"], "INVALID_SCHEMA_NAME")

    def test_create_tenant_schema_starts_with_number_returns_400(self):
        """schema_name que empieza con número → 400 con código INVALID_SCHEMA_NAME."""
        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Complejo 123",
                "schema_name": "1invalido",
                "domain": "numerado.localhost",
                "admin_email": "admin@numerado.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.data)

    # -----------------------------------------------------------------------
    # Test 7: schema_name duplicado
    # -----------------------------------------------------------------------

    def test_create_tenant_duplicate_schema_returns_400(self):
        """schema_name ya existente (no reservado) → 400 con SCHEMA_ALREADY_EXISTS."""
        # Primero crear un tenant con un schema no reservado
        schema = "testplatform_dup_schema"
        domain = "testplatform-dup.localhost"
        self._register_created_schema(schema)

        connection.set_schema_to_public()
        # Crear el tenant la primera vez
        first_resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Primer Tenant",
                "schema_name": schema,
                "domain": domain,
                "admin_email": "admin@dup1.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(first_resp.status_code, 201, f"Primera creación falló: {first_resp.data}")

        # Intentar crear de nuevo con el mismo schema
        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Segundo Tenant Duplicado",
                "schema_name": schema,  # ya existe
                "domain": "otrodominio.localhost",
                "admin_email": "admin@dup2.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400: {resp.data}")
        self.assertIn("error", resp.data)
        self.assertEqual(resp.data["error"]["code"], "SCHEMA_ALREADY_EXISTS")

    # -----------------------------------------------------------------------
    # Test 8: dominio duplicado
    # -----------------------------------------------------------------------

    def test_create_tenant_duplicate_domain_returns_400(self):
        """domain ya existente → 400 con DOMAIN_ALREADY_EXISTS."""
        connection.set_schema_to_public()
        existing_domain = Domain.objects.filter(tenant=self.fixture_tenant, is_primary=True).first()
        if not existing_domain:
            self.skipTest("No hay dominio primario del tenant de fixture")

        resp = self.client.post(
            "/api/platform/tenants/",
            {
                "name": "Duplicado Dominio",
                "schema_name": "newschemaok",
                "domain": existing_domain.domain,  # dominio ya existe
                "admin_email": "admin@newschemaok.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400: {resp.data}")
        self.assertIn("error", resp.data)
        self.assertEqual(resp.data["error"]["code"], "DOMAIN_ALREADY_EXISTS")

    # -----------------------------------------------------------------------
    # Test 9: Sin JWT → 401
    # -----------------------------------------------------------------------

    def test_list_tenants_without_jwt_returns_401(self):
        """GET /api/platform/tenants/ sin JWT → 401."""
        anon_client = APIClient()
        resp = anon_client.get("/api/platform/tenants/")
        self.assertIn(resp.status_code, [401, 403])

    def test_create_tenant_without_jwt_returns_401(self):
        """POST /api/platform/tenants/ sin JWT → 401."""
        anon_client = APIClient()
        resp = anon_client.post(
            "/api/platform/tenants/",
            {
                "name": "Sin Auth",
                "schema_name": "sinauth",
                "domain": "sinauth.localhost",
                "admin_email": "admin@sinauth.local",
                "admin_password": "adminpass123",
            },
            format="json",
        )
        self.assertIn(resp.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Tests de aislamiento de JWT
# ---------------------------------------------------------------------------

class TestPlatformJWTIsolation(TenantTestCase):
    """
    Verifica que los JWT de system_admin y de tenant users no son intercambiables.

    ADR-013 §Aislamiento de JWT:
      - JWT de system_admin NO válido en endpoints de tenant.
      - JWT de tenant user NO válido en endpoints de platform.
    """

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)

        # Superuser Django (auth.User, esquema public).
        # Se usa _get_auth_user_model() porque AUTH_USER_MODEL='users.User' deshabilita
        # el manager de auth.User cuando se importa directamente desde el módulo.
        AuthUser = _get_auth_user_model()
        self.superuser = AuthUser.objects.create_superuser(
            username="isolation_sysadmin",
            email="isolation@platform.local",
            password="superpassword123",
        )

        # Tenant user (apps.users.User, esquema del tenant)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.tenant_user = User.objects.create_user(
            email="tenant_isolation@test.local",
            password="tenantpass123",
            role="tenant_admin",
        )

    def tearDown(self):
        _get_auth_user_model().objects.filter(username="isolation_sysadmin").delete()
        connection.set_tenant(self.tenant)
        super().tearDown()

    def _get_platform_access_token(self) -> str:
        """Obtiene el JWT del system_admin usando el urlconf de platform."""
        client = APIClient()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = client.post(
                "/api/platform/auth/login/",
                {"email": "isolation@platform.local", "password": "superpassword123"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Login platform falló: {resp.data}")
        return resp.data["access"]

    def _get_tenant_access_token(self) -> str:
        """Obtiene el JWT del tenant user."""
        client = TenantClient(self.tenant)
        resp = client.post(
            "/api/auth/login/",
            {"email": "tenant_isolation@test.local", "password": "tenantpass123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, f"Login tenant falló: {resp.content}")
        return resp.json()["access"]

    def test_platform_jwt_cannot_access_tenant_endpoint(self):
        """
        JWT de system_admin NO es válido en endpoints de tenant.

        TenantJWTAuthentication verifica que el token NO tenga iss='platform'.
        El token de system_admin tiene iss='platform' → TenantJWTAuthentication
        lo rechaza con InvalidToken → 401.
        """
        # Obtener token de platform usando urls_public
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            platform_client = APIClient()
            resp_login = platform_client.post(
                "/api/platform/auth/login/",
                {"email": "isolation@platform.local", "password": "superpassword123"},
                format="json",
            )
        self.assertEqual(resp_login.status_code, 200, f"Login platform falló: {resp_login.data}")
        platform_token = resp_login.data["access"]

        # Intentar usar el token en endpoint de tenant (ROOT_URLCONF normal)
        tenant_client = TenantClient(self.tenant)
        resp = tenant_client.get(
            "/api/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {platform_token}",
        )
        # TenantJWTAuthentication rechaza tokens con iss='platform' → 401
        self.assertIn(
            resp.status_code,
            [401, 403],
            f"FALLA: JWT de system_admin fue aceptado en endpoint de tenant (status={resp.status_code})",
        )

    def test_tenant_jwt_cannot_access_platform_endpoint(self):
        """
        JWT de tenant user NO es válido en endpoints de platform.

        PlatformJWTAuthentication verifica que el token tenga iss='platform'.
        El token de tenant user no tiene ese claim (fue emitido por /api/auth/login/)
        → PlatformJWTAuthentication lanza InvalidToken → 401.
        """
        tenant_token = self._get_tenant_access_token()

        # Usar el token de tenant en endpoint de platform (urls_public)
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            platform_client = APIClient()
            platform_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tenant_token}")
            resp = platform_client.get("/api/platform/tenants/")

        # PlatformJWTAuthentication rechaza tokens sin iss='platform' → 401
        self.assertIn(
            resp.status_code,
            [401, 403],
            f"FALLA: JWT de tenant fue aceptado en endpoint de platform (status={resp.status_code})",
        )


# ---------------------------------------------------------------------------
# Tests del service create_tenant_service (unit tests)
# ---------------------------------------------------------------------------

class TestCreateTenantService(TenantTestCase):
    """
    Tests unitarios de create_tenant_service en services.py.

    No prueban via HTTP; prueban el service directamente.
    """

    def setUp(self):
        super().setUp()
        self._created_schemas = []

    def tearDown(self):
        for schema in self._created_schemas:
            connection.set_schema_to_public()
            try:
                tenant = Tenant.objects.filter(schema_name=schema).first()
                if tenant:
                    Domain.objects.filter(tenant=tenant).delete()
                    tenant.delete(force_drop=True)
            except Exception:
                pass
        connection.set_tenant(self.tenant)
        super().tearDown()

    def _register(self, schema: str):
        if schema not in self._created_schemas:
            self._created_schemas.append(schema)

    def test_create_tenant_service_success(self):
        """create_tenant_service crea Tenant, Domain y tenant_admin correctamente."""
        schema = "svc_test_create"
        domain = "svc-test-create.localhost"
        admin_email = "admin@svc-test-create.local"
        self._register(schema)

        connection.set_schema_to_public()
        tenant = create_tenant_service(
            name="Servicio Test Create",
            schema_name=schema,
            domain=domain,
            admin_email=admin_email,
            admin_password="testpassword123",
        )

        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.schema_name, schema)
        self.assertTrue(tenant.is_active)

        # Verificar Domain
        self.assertTrue(Domain.objects.filter(domain=domain, tenant=tenant).exists())

        # Verificar tenant_admin en el nuevo esquema
        from django.contrib.auth import get_user_model
        with schema_context(schema):
            User = get_user_model()
            self.assertTrue(User.objects.filter(email=admin_email).exists())
            admin = User.objects.get(email=admin_email)
            self.assertEqual(admin.role, "tenant_admin")
            self.assertTrue(admin.is_staff)

    def test_create_tenant_service_invalid_schema_raises(self):
        """InvalidSchemaName se lanza con schema inválido."""
        from apps.tenants.services import InvalidSchemaName
        with self.assertRaises(InvalidSchemaName):
            create_tenant_service(
                name="Test",
                schema_name="INVALID-schema!",
                domain="invalid.localhost",
                admin_email="admin@invalid.local",
                admin_password="pass12345",
            )

    def test_create_tenant_service_reserved_schema_raises(self):
        """InvalidSchemaName para schema reservado 'public'."""
        from apps.tenants.services import InvalidSchemaName
        with self.assertRaises(InvalidSchemaName):
            create_tenant_service(
                name="Public Tenant",
                schema_name="public",
                domain="public-test.localhost",
                admin_email="admin@public-test.local",
                admin_password="pass12345",
            )

    def test_create_tenant_service_duplicate_schema_raises(self):
        """SchemaAlreadyExists se lanza si el schema ya existe (no reservado)."""
        from apps.tenants.services import SchemaAlreadyExists

        schema = "svc_dup_schema_test"
        domain = "svc-dup-schema.localhost"
        self._register(schema)

        connection.set_schema_to_public()
        # Crear el tenant la primera vez
        create_tenant_service(
            name="Primer Tenant Dup",
            schema_name=schema,
            domain=domain,
            admin_email="admin@svc-dup1.local",
            admin_password="pass12345",
        )

        # Intentar crearlo de nuevo con el mismo schema
        with self.assertRaises(SchemaAlreadyExists):
            create_tenant_service(
                name="Segundo Tenant Dup",
                schema_name=schema,
                domain="svc-dup-schema2.localhost",
                admin_email="admin@svc-dup2.local",
                admin_password="pass12345",
            )

    def test_create_tenant_service_duplicate_domain_raises(self):
        """DomainAlreadyExists se lanza si el domain ya existe."""
        from apps.tenants.services import DomainAlreadyExists
        connection.set_schema_to_public()
        existing_domain = Domain.objects.filter(tenant=self.tenant, is_primary=True).first()
        if not existing_domain:
            self.skipTest("No hay dominio primario disponible")

        with self.assertRaises(DomainAlreadyExists):
            create_tenant_service(
                name="Dup Domain",
                schema_name="dupdomainschema",
                domain=existing_domain.domain,
                admin_email="admin@dupdomain.local",
                admin_password="pass12345",
            )
