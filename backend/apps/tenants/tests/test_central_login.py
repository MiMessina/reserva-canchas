"""
Tests — Sprint 14: Login Centralizado.

Cobertura:
  1.  lookup_email con email en 0 tenants → lista vacía
  2.  lookup_email con email en 1 tenant → lista con 1 ítem
  3.  lookup_email con email en 2 tenants → lista con 2 ítems
  4.  central_login con credenciales correctas → retorna {code, redirect_url}
  5.  central_login con contraseña incorrecta → 401 INVALID_CREDENTIALS
  6.  central_login con tenant inactivo → 401 TENANT_INACTIVE
  7.  central_login con role=player → 403 ROLE_NOT_ALLOWED
  8.  exchange_code con code válido → retorna {access, refresh}
  9.  exchange_code con code ya usado → 400 CODE_ALREADY_USED
  10. exchange_code con code expirado → 400 CODE_EXPIRED
  11. Señal post_save → UserEmailIndex se crea al crear un User en un tenant
  12. Vía HTTP: lookup-email, central-login, exchange-code happy path
  13. Aislamiento: code no se puede usar dos veces (replay attack)

Estrategia de tests:
  - TenantTestCase para tests de señal (necesitan esquema de tenant disponible).
  - SafeTransactionTestCase (subclase con _fixture_teardown neutralizado) para tests
    que crean nuevos esquemas PG (DDL no puede correr dentro de la transacción de TestCase).
  - Los tests que solo tocan OneTimeCode/UserEmailIndex (schema public, sin DDL) pueden
    usar TestCase estándar con datos insertados directamente (sin crear esquemas nuevos).

Nota sobre TransactionTestCase:
  TransactionTestCase sin override de _fixture_teardown borra TODOS los datos del
  schema público (Tenant, PlatformAdmin, Domain). Siempre sobrescribir ese método.
  Ver sprint13_seed_on_mock.md §Lección.
"""

import secrets
from datetime import timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.tenants.models import Domain, OneTimeCode, Tenant, UserEmailIndex
from apps.tenants import services as tenant_services

# PUBLIC_SCHEMA_URLCONF — todos los endpoints auth-* viven aquí
PUBLIC_URLCONF = "config.urls_public"


# ---------------------------------------------------------------------------
# SafeTransactionTestCase
# ---------------------------------------------------------------------------

class SafeTransactionTestCase(TransactionTestCase):
    """
    TransactionTestCase que NO borra los datos del schema public en tearDown.

    TransactionTestCase por defecto llama a _fixture_teardown() que ejecuta
    TRUNCATE en todas las tablas (incluyendo Tenant, Domain, PlatformAdmin del
    schema public). Eso rompe otros tests.

    Override de _fixture_teardown para neutralizarlo. Los tests hijos son
    responsables de limpiar lo que crean en tearDown().

    Ver: sprint13_seed_on_mock.md §Lección aprendida.
    """

    def _fixture_teardown(self):
        """No borrar datos del schema public entre tests."""
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_tenant_and_user(
    schema_name: str,
    domain_name: str,
    admin_email: str,
    admin_password: str,
    role: str = "tenant_admin",
    is_active: bool = True,
):
    """
    Crea Tenant + Domain + usuario en el esquema dado.
    Solo debe llamarse desde SafeTransactionTestCase o TenantTestCase.
    No puede llamarse desde TestCase (el DDL aborta la transacción).
    Retorna (tenant, domain).
    """
    from django.core.management import call_command

    connection.set_schema_to_public()
    tenant = Tenant(schema_name=schema_name, name=f"Complejo {schema_name}", is_active=is_active)
    tenant.save()
    domain = Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

    # DDL — requiere estar fuera de una transacción normal de TestCase
    call_command("migrate_schemas", schema_name=schema_name, interactive=False, verbosity=0)

    with schema_context(schema_name):
        from apps.users.models import User
        User.objects.create_user(email=admin_email, password=admin_password, role=role)

    return tenant, domain


def _delete_tenant(schema_name: str):
    """Limpia un tenant de prueba."""
    connection.set_schema_to_public()
    try:
        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant:
            Domain.objects.filter(tenant=tenant).delete()
            tenant.delete(force_drop=True)
    except Exception:
        pass
    try:
        UserEmailIndex.objects.filter(schema_name=schema_name).delete()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests 1-3: lookup_email — solo toca UserEmailIndex y Tenant (schema public)
# Sin DDL → TestCase estándar.
# ---------------------------------------------------------------------------

class TestLookupEmailService(TestCase):
    """
    Tests unitarios de lookup_email().
    No crean esquemas nuevos: solo insertan registros en UserEmailIndex y Tenant
    en el schema public (dentro de la transacción de TestCase).
    """

    def setUp(self):
        connection.set_schema_to_public()

        # Tenant de fixtures (sin esquema PG real — solo la fila en la tabla Tenant)
        self.tenant_a = Tenant.objects.create(
            schema_name="lu_tenant_a",
            name="Lookup Tenant A",
            is_active=True,
        )
        Domain.objects.create(
            domain="lu-tenant-a.localhost",
            tenant=self.tenant_a,
            is_primary=True,
        )
        self.tenant_b = Tenant.objects.create(
            schema_name="lu_tenant_b",
            name="Lookup Tenant B",
            is_active=True,
        )
        Domain.objects.create(
            domain="lu-tenant-b.localhost",
            tenant=self.tenant_b,
            is_primary=True,
        )
        self.tenant_inactive = Tenant.objects.create(
            schema_name="lu_tenant_inactive",
            name="Lookup Tenant Inactive",
            is_active=False,
        )
        Domain.objects.create(
            domain="lu-tenant-inactive.localhost",
            tenant=self.tenant_inactive,
            is_primary=True,
        )

    # ------------------------------------------------------------------
    # Test 1
    # ------------------------------------------------------------------

    def test_lookup_email_no_match_returns_empty_list(self):
        """lookup_email con email que no existe en ningún tenant → []."""
        result = tenant_services.lookup_email("noexiste@nowhere.com")
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Test 2
    # ------------------------------------------------------------------

    def test_lookup_email_one_tenant_returns_list_with_one_item(self):
        """lookup_email con email en 1 tenant → lista de 1 ítem."""
        email = "shared@single.com"
        UserEmailIndex.objects.create(email=email, schema_name=self.tenant_a.schema_name)

        result = tenant_services.lookup_email(email)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["schema_name"], self.tenant_a.schema_name)
        self.assertIn("tenant_name", result[0])
        self.assertIn("domain", result[0])

    # ------------------------------------------------------------------
    # Test 3
    # ------------------------------------------------------------------

    def test_lookup_email_two_tenants_returns_list_with_two_items(self):
        """lookup_email con mismo email en 2 tenants → lista de 2 ítems."""
        email = "shared@two.com"
        UserEmailIndex.objects.create(email=email, schema_name=self.tenant_a.schema_name)
        UserEmailIndex.objects.create(email=email, schema_name=self.tenant_b.schema_name)

        result = tenant_services.lookup_email(email)
        schemas_found = {item["schema_name"] for item in result}
        self.assertIn(self.tenant_a.schema_name, schemas_found)
        self.assertIn(self.tenant_b.schema_name, schemas_found)
        self.assertEqual(len(result), 2)

    def test_lookup_email_inactive_tenant_excluded(self):
        """lookup_email no incluye tenants inactivos."""
        email = "admin@inactive-lookup.com"
        UserEmailIndex.objects.create(email=email, schema_name=self.tenant_inactive.schema_name)

        result = tenant_services.lookup_email(email)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Tests 4-10: central_login y exchange_code — necesitan esquemas reales (DDL)
# → SafeTransactionTestCase
# ---------------------------------------------------------------------------

class TestCentralLoginService(SafeTransactionTestCase):
    """
    Tests unitarios de central_login().
    Crea esquemas PG reales → SafeTransactionTestCase.
    """

    def setUp(self):
        connection.set_schema_to_public()
        self._schemas_to_cleanup = []

    def tearDown(self):
        for schema in self._schemas_to_cleanup:
            _delete_tenant(schema)
        connection.set_schema_to_public()

    def _register(self, schema: str):
        if schema not in self._schemas_to_cleanup:
            self._schemas_to_cleanup.append(schema)

    # ------------------------------------------------------------------
    # Test 4
    # ------------------------------------------------------------------

    def test_central_login_valid_credentials_returns_code_and_redirect(self):
        """central_login con credenciales correctas → {code, redirect_url}."""
        schema = "clsvcloginok"
        email = "admin@clsvcloginok.com"
        password = "securepass123"
        self._register(schema)
        _create_tenant_and_user(schema, f"{schema}.localhost", email, password, role="tenant_admin")

        connection.set_schema_to_public()
        result = tenant_services.central_login(email=email, password=password, schema_name=schema)

        self.assertIn("code", result)
        self.assertIn("redirect_url", result)
        self.assertTrue(len(result["code"]) > 10)
        self.assertIn(schema, result["redirect_url"])

        # Verificar que el OTC existe en la DB
        self.assertTrue(OneTimeCode.objects.filter(code=result["code"]).exists())

    # ------------------------------------------------------------------
    # Test 5
    # ------------------------------------------------------------------

    def test_central_login_wrong_password_raises_invalid_credentials(self):
        """central_login con contraseña incorrecta → ValueError('INVALID_CREDENTIALS')."""
        schema = "clsvcbadpw"
        email = "admin@clsvcbadpw.com"
        self._register(schema)
        _create_tenant_and_user(schema, f"{schema}.localhost", email, "correctpass", role="tenant_admin")

        connection.set_schema_to_public()
        with self.assertRaises(ValueError) as ctx:
            tenant_services.central_login(email=email, password="wrongpass", schema_name=schema)
        self.assertEqual(str(ctx.exception), "INVALID_CREDENTIALS")

    # ------------------------------------------------------------------
    # Test 6
    # ------------------------------------------------------------------

    def test_central_login_inactive_tenant_raises_tenant_inactive(self):
        """central_login con tenant inactivo → ValueError('TENANT_INACTIVE')."""
        schema = "clsvcinactive"
        email = "admin@clsvcinactive.com"
        self._register(schema)
        _create_tenant_and_user(
            schema, f"{schema}.localhost", email, "pass12345",
            role="tenant_admin", is_active=False,
        )

        connection.set_schema_to_public()
        with self.assertRaises(ValueError) as ctx:
            tenant_services.central_login(email=email, password="pass12345", schema_name=schema)
        self.assertEqual(str(ctx.exception), "TENANT_INACTIVE")

    # ------------------------------------------------------------------
    # Test 7
    # ------------------------------------------------------------------

    def test_central_login_player_role_raises_role_not_allowed(self):
        """central_login con role=player → ValueError('ROLE_NOT_ALLOWED')."""
        schema = "clsvcplayer"
        email = "player@clsvcplayer.com"
        self._register(schema)
        _create_tenant_and_user(schema, f"{schema}.localhost", email, "pass12345", role="player")

        connection.set_schema_to_public()
        with self.assertRaises(ValueError) as ctx:
            tenant_services.central_login(email=email, password="pass12345", schema_name=schema)
        self.assertEqual(str(ctx.exception), "ROLE_NOT_ALLOWED")

    def test_central_login_operator_role_allowed(self):
        """central_login con role=operator → funciona correctamente."""
        schema = "clsvcoper"
        email = "cajero@clsvcoper.com"
        self._register(schema)
        _create_tenant_and_user(schema, f"{schema}.localhost", email, "pass12345", role="operator")

        connection.set_schema_to_public()
        result = tenant_services.central_login(email=email, password="pass12345", schema_name=schema)
        self.assertIn("code", result)


class TestExchangeCodeService(SafeTransactionTestCase):
    """
    Tests unitarios de exchange_code().
    Necesita esquemas reales para obtener OTCs válidos → SafeTransactionTestCase.
    """

    def setUp(self):
        connection.set_schema_to_public()
        self._schemas_to_cleanup = []

    def tearDown(self):
        for schema in self._schemas_to_cleanup:
            _delete_tenant(schema)
        connection.set_schema_to_public()

    def _register(self, schema: str):
        if schema not in self._schemas_to_cleanup:
            self._schemas_to_cleanup.append(schema)

    def _setup_tenant_and_get_code(self, schema: str, email: str) -> str:
        """Crea tenant + usuario y genera un OTC válido. Retorna el code."""
        password = "pass12345"
        self._register(schema)
        _create_tenant_and_user(schema, f"{schema}.localhost", email, password, role="tenant_admin")

        connection.set_schema_to_public()
        result = tenant_services.central_login(email=email, password=password, schema_name=schema)
        return result["code"]

    # ------------------------------------------------------------------
    # Test 8
    # ------------------------------------------------------------------

    def test_exchange_code_valid_returns_access_and_refresh(self):
        """exchange_code con code válido → {access, refresh} JWT."""
        code = self._setup_tenant_and_get_code("clexchok", "admin@clexchok.com")

        connection.set_schema_to_public()
        result = tenant_services.exchange_code(code)

        self.assertIn("access", result)
        self.assertIn("refresh", result)
        self.assertTrue(len(result["access"]) > 50)
        self.assertTrue(len(result["refresh"]) > 50)

    # ------------------------------------------------------------------
    # Test 9
    # ------------------------------------------------------------------

    def test_exchange_code_already_used_raises(self):
        """exchange_code con code ya usado → ValueError('CODE_ALREADY_USED')."""
        code = self._setup_tenant_and_get_code("clexchused", "admin@clexchused.com")

        connection.set_schema_to_public()
        tenant_services.exchange_code(code)  # primer uso OK

        with self.assertRaises(ValueError) as ctx:
            tenant_services.exchange_code(code)
        self.assertEqual(str(ctx.exception), "CODE_ALREADY_USED")

    # ------------------------------------------------------------------
    # Test 10
    # ------------------------------------------------------------------

    def test_exchange_code_expired_raises(self):
        """exchange_code con code expirado → ValueError('CODE_EXPIRED')."""
        code_str = self._setup_tenant_and_get_code("clexchexpired", "admin@clexchexpired.com")

        connection.set_schema_to_public()
        OneTimeCode.objects.filter(code=code_str).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        with self.assertRaises(ValueError) as ctx:
            tenant_services.exchange_code(code_str)
        self.assertEqual(str(ctx.exception), "CODE_EXPIRED")

    def test_exchange_code_not_found_raises(self):
        """exchange_code con code inexistente → ValueError('CODE_NOT_FOUND')."""
        with self.assertRaises(ValueError) as ctx:
            tenant_services.exchange_code("codigo-que-no-existe-en-db-XYZ123")
        self.assertEqual(str(ctx.exception), "CODE_NOT_FOUND")

    # ------------------------------------------------------------------
    # Test 13: replay attack
    # ------------------------------------------------------------------

    def test_exchange_code_cannot_be_replayed(self):
        """Un OTC usado queda marcado y no puede reutilizarse (anti-replay)."""
        code = self._setup_tenant_and_get_code("clexchreplay", "admin@clexchreplay.com")

        connection.set_schema_to_public()
        tenant_services.exchange_code(code)

        # Verificar flag used=True
        otc = OneTimeCode.objects.get(code=code)
        self.assertTrue(otc.used)

        # No se puede reutilizar
        with self.assertRaises(ValueError) as ctx:
            tenant_services.exchange_code(code)
        self.assertEqual(str(ctx.exception), "CODE_ALREADY_USED")


# ---------------------------------------------------------------------------
# Test 11: Señal post_save → TenantTestCase (tiene esquema 'test' disponible)
# ---------------------------------------------------------------------------

class TestUserEmailIndexSignal(TenantTestCase):
    """
    Test 11 — Señal post_save.

    Verifica que al crear un User en un esquema tenant, la señal
    sync_user_email_index actualiza UserEmailIndex en schema public.
    Usa TenantTestCase porque necesita un esquema de tenant activo (self.tenant).
    """

    def test_signal_creates_email_index_on_user_save(self):
        """Crear un User en el tenant → UserEmailIndex se crea en schema public."""
        email = "signal_test@complejo.com"

        connection.set_tenant(self.tenant)
        from apps.users.models import User
        User.objects.create_user(email=email, password="testpass123", role="tenant_admin")

        connection.set_schema_to_public()
        entry = UserEmailIndex.objects.filter(
            email=email,
            schema_name=self.tenant.schema_name,
        ).first()

        self.assertIsNotNone(
            entry,
            f"UserEmailIndex no se creó para email={email} schema={self.tenant.schema_name}",
        )

    def test_signal_updates_email_index_on_user_update_is_idempotent(self):
        """Actualizar un User en el tenant → UserEmailIndex no se duplica (update_or_create)."""
        email = "signal_update@complejo.com"
        connection.set_tenant(self.tenant)

        from apps.users.models import User
        user = User.objects.create_user(email=email, password="pass", role="operator")

        # Actualizar → dispara post_save de nuevo
        user.first_name = "Juan"
        user.save()

        connection.set_schema_to_public()
        count = UserEmailIndex.objects.filter(
            email=email,
            schema_name=self.tenant.schema_name,
        ).count()
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# Tests HTTP — Endpoints vía PUBLIC_SCHEMA_URLCONF
# Tests 4-10 vía HTTP + aislamiento de tenant
# ---------------------------------------------------------------------------

@override_settings(ROOT_URLCONF=PUBLIC_URLCONF)
class TestCentralLoginHTTP(SafeTransactionTestCase):
    """
    Tests HTTP de los 3 endpoints del login centralizado.

    Usa SafeTransactionTestCase (necesita crear esquemas PG con DDL).
    override_settings simula el urlconf del schema public.

    Crea un único tenant de prueba en setUp y lo reutiliza entre tests.
    Los tests individuales que necesitan tenants adicionales los crean y limpian.
    """

    def setUp(self):
        connection.set_schema_to_public()
        self._schemas_to_cleanup = []
        self.client = APIClient()

        # Tenant de prueba principal
        # Nota: el schema_name puede tener guiones bajos, pero la dirección de email
        # NO puede tener underscores en el dominio (Django 5 rechaza eso).
        # Usamos "clhttpmain" como schema y "clhttpmain.com" en el email.
        schema = "clhttpmain"
        self._register(schema)
        self.schema = schema
        self.email = "admin@clhttpmain.com"
        self.password = "securepass123"
        self.tenant, self.domain = _create_tenant_and_user(
            schema, f"{schema}.localhost", self.email, self.password, role="tenant_admin"
        )
        # Insertar en el índice (la señal se dispara en schema_context)
        connection.set_schema_to_public()
        UserEmailIndex.objects.get_or_create(email=self.email, schema_name=schema)

    def tearDown(self):
        connection.set_schema_to_public()
        OneTimeCode.objects.all().delete()
        for schema in self._schemas_to_cleanup:
            _delete_tenant(schema)
        connection.set_schema_to_public()

    def _register(self, schema: str):
        if schema not in self._schemas_to_cleanup:
            self._schemas_to_cleanup.append(schema)

    def _get_code(self) -> str:
        """Obtiene un OTC válido vía central-login."""
        connection.set_schema_to_public()
        resp = self.client.post(
            "/api/auth/central-login/",
            {"email": self.email, "password": self.password, "schema_name": self.schema},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"central-login falló: {resp.data}")
        return resp.data["code"]

    # ------------------------------------------------------------------
    # lookup-email
    # ------------------------------------------------------------------

    def test_lookup_email_endpoint_returns_200_with_results(self):
        """POST /api/auth/lookup-email/ con email existente → 200 con lista."""
        resp = self.client.post(
            "/api/auth/lookup-email/",
            {"email": self.email},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["schema_name"], self.schema)

    def test_lookup_email_endpoint_empty_returns_200_with_empty_list(self):
        """POST /api/auth/lookup-email/ con email inexistente → 200 con []."""
        resp = self.client.post(
            "/api/auth/lookup-email/",
            {"email": "nobody@nowhere.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_lookup_email_endpoint_invalid_email_returns_400(self):
        """POST /api/auth/lookup-email/ con email inválido → 400."""
        resp = self.client.post(
            "/api/auth/lookup-email/",
            {"email": "not-an-email"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # central-login
    # ------------------------------------------------------------------

    def test_central_login_endpoint_success(self):
        """POST /api/auth/central-login/ con creds válidas → 200 {code, redirect_url}."""
        resp = self.client.post(
            "/api/auth/central-login/",
            {"email": self.email, "password": self.password, "schema_name": self.schema},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertIn("code", resp.data)
        self.assertIn("redirect_url", resp.data)

    def test_central_login_endpoint_wrong_password_returns_401(self):
        """POST /api/auth/central-login/ con contraseña incorrecta → 401."""
        resp = self.client.post(
            "/api/auth/central-login/",
            {"email": self.email, "password": "wrongpass", "schema_name": self.schema},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["error"]["code"], "INVALID_CREDENTIALS")

    def test_central_login_endpoint_inactive_tenant_returns_401(self):
        """POST /api/auth/central-login/ con tenant inactivo → 401 TENANT_INACTIVE."""
        schema = "clhttpinactive"
        self._register(schema)
        email = "admin@clhttpinactive.com"
        _create_tenant_and_user(
            schema, f"{schema}.localhost", email, "pass12345",
            role="tenant_admin", is_active=False,
        )
        connection.set_schema_to_public()

        resp = self.client.post(
            "/api/auth/central-login/",
            {"email": email, "password": "pass12345", "schema_name": schema},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["error"]["code"], "TENANT_INACTIVE")

    def test_central_login_endpoint_player_role_returns_403(self):
        """POST /api/auth/central-login/ con role=player → 403 ROLE_NOT_ALLOWED."""
        schema = "clhttpplayer"
        self._register(schema)
        email = "player@clhttpplayer.com"
        _create_tenant_and_user(schema, f"{schema}.localhost", email, "pass12345", role="player")
        connection.set_schema_to_public()

        resp = self.client.post(
            "/api/auth/central-login/",
            {"email": email, "password": "pass12345", "schema_name": schema},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["error"]["code"], "ROLE_NOT_ALLOWED")

    # ------------------------------------------------------------------
    # exchange-code
    # ------------------------------------------------------------------

    def test_exchange_code_endpoint_success(self):
        """POST /api/auth/exchange-code/ con code válido → 200 {access, refresh}."""
        code = self._get_code()
        resp = self.client.post(
            "/api/auth/exchange-code/",
            {"code": code},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_exchange_code_endpoint_already_used_returns_400(self):
        """POST /api/auth/exchange-code/ con code ya usado → 400 CODE_ALREADY_USED."""
        code = self._get_code()
        self.client.post("/api/auth/exchange-code/", {"code": code}, format="json")
        resp = self.client.post("/api/auth/exchange-code/", {"code": code}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["error"]["code"], "CODE_ALREADY_USED")

    def test_exchange_code_endpoint_expired_returns_400(self):
        """POST /api/auth/exchange-code/ con code expirado → 400 CODE_EXPIRED."""
        code = self._get_code()
        connection.set_schema_to_public()
        OneTimeCode.objects.filter(code=code).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        resp = self.client.post("/api/auth/exchange-code/", {"code": code}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["error"]["code"], "CODE_EXPIRED")

    def test_exchange_code_endpoint_invalid_code_returns_400(self):
        """POST /api/auth/exchange-code/ con code inexistente → 400 CODE_NOT_FOUND."""
        resp = self.client.post(
            "/api/auth/exchange-code/",
            {"code": "no-existe-este-codigo-XYZ99999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["error"]["code"], "CODE_NOT_FOUND")
