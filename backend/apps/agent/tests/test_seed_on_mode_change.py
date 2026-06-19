"""
Tests — Seed automático de conversaciones demo al activar bot_mode='mock'.

Cubre:
  1. PATCH bot_mode='mock' → seed automático en el esquema del tenant.
  2. PATCH bot_mode='mock' por segunda vez → idempotente (no duplica).
  3. Crear tenant con bot_mode='mock' → esquema ya tiene conversaciones [DEMO].
  4. Crear tenant con bot_mode='production' → sin conversaciones [DEMO].

Tests 1-2: TenantTestCase + override_settings(ROOT_URLCONF=PLATFORM_URLCONF).
           Usa PlatformAdmin (no auth.User) — patrón de Sprint 10.
Tests 3-4: TransactionTestCase (create_tenant_service hace DDL con CREATE SCHEMA).
           _fixture_teardown() se sobreescribe para evitar flush del esquema público.
"""

from django.db import connection
from django.test import TransactionTestCase, override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.agent.models import BOT_DEMO_MARKER, BotConversationLog
from apps.tenants.models import Domain, PlatformAdmin, Tenant
from apps.tenants.services import create_tenant_service

PLATFORM_URLCONF = "config.urls_public"


# ---------------------------------------------------------------------------
# Tests 1 y 2 — PATCH bot_mode (TenantTestCase + PlatformAdmin)
# ---------------------------------------------------------------------------

class TestSeedOnPlatformPatch(TenantTestCase):
    """
    Verifica que PATCH bot_mode='mock' dispara el seed automático.

    Patrón Sprint 10:
      - PlatformAdmin para autenticar contra /api/platform/
      - override_settings(ROOT_URLCONF=PLATFORM_URLCONF) en cada llamada a la platform API
      - TenantTestCase: no crea DDL adicional, no borra el esquema público
    """

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()
        self.platform_admin = PlatformAdmin(email="sysadmin_seed@platform.local")
        self.platform_admin.set_password("superpassword123")
        self.platform_admin.save()

        self.platform_client = APIClient()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.post(
                "/api/platform/auth/login/",
                {"email": "sysadmin_seed@platform.local", "password": "superpassword123"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Login falló: {resp.data}")
        self.platform_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def tearDown(self):
        connection.set_schema_to_public()
        PlatformAdmin.objects.filter(email="sysadmin_seed@platform.local").delete()
        connection.set_tenant(self.tenant)
        super().tearDown()

    def test_patch_mock_seeds_conversations(self):
        """PATCH bot_mode='mock' → seed automático de conversaciones demo."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode", "updated_at"])

        with schema_context(self.tenant.schema_name):
            BotConversationLog.objects.filter(message__startswith=BOT_DEMO_MARKER).delete()

        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, resp.data)

        with schema_context(self.tenant.schema_name):
            demo_count = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()
        self.assertGreater(demo_count, 0)

    def test_patch_mock_is_idempotent(self):
        """PATCH bot_mode='mock' dos veces → no duplica conversaciones."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode", "updated_at"])

        with schema_context(self.tenant.schema_name):
            BotConversationLog.objects.filter(message__startswith=BOT_DEMO_MARKER).delete()

        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )
        with schema_context(self.tenant.schema_name):
            count_after_first = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()

        # Segundo PATCH (ya está en mock → no debe volver a insertar)
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )
        with schema_context(self.tenant.schema_name):
            count_after_second = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()

        self.assertEqual(count_after_first, count_after_second)


# ---------------------------------------------------------------------------
# Tests 3 y 4 — create_tenant_service (TransactionTestCase + override)
# ---------------------------------------------------------------------------

class TestSeedOnTenantCreate(TransactionTestCase):
    """
    Verifica que create_tenant_service siembra el seed cuando bot_mode='mock'.

    Usa TransactionTestCase porque create_tenant_service() hace DDL (CREATE SCHEMA),
    incompatible con el wrapeo transaccional de TestCase.

    _fixture_teardown() se sobreescribe para evitar que Django haga flush del esquema
    público al finalizar cada test, lo que borraría Tenant y PlatformAdmin de producción.
    La limpieza se delega enteramente al tearDown manual.
    """

    SCHEMA_MOCK = "t_seed_mock"
    SCHEMA_PROD = "t_seed_prod"

    def _fixture_teardown(self):
        # Previene el flush automático del esquema público.
        # La limpieza de los schemas de prueba la hace tearDown.
        pass

    def tearDown(self):
        connection.set_schema_to_public()
        for schema in [self.SCHEMA_MOCK, self.SCHEMA_PROD]:
            try:
                tenant = Tenant.objects.get(schema_name=schema)
                tenant.delete(force_drop=True)
            except Tenant.DoesNotExist:
                pass

    def test_create_tenant_with_mock_seeds_conversations(self):
        """Nuevo tenant con bot_mode='mock' → esquema ya tiene conversaciones [DEMO]."""
        connection.set_schema_to_public()
        create_tenant_service(
            name="Seed Mock Test",
            schema_name=self.SCHEMA_MOCK,
            domain="t-seed-mock.localhost",
            admin_email="admin@seedmock.local",
            admin_password="pass1234!",
            bot_mode="mock",
        )
        with schema_context(self.SCHEMA_MOCK):
            demo_count = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()
        self.assertGreater(demo_count, 0)

    def test_create_tenant_with_production_has_no_demo(self):
        """Nuevo tenant con bot_mode='production' → sin conversaciones [DEMO]."""
        connection.set_schema_to_public()
        create_tenant_service(
            name="Seed Prod Test",
            schema_name=self.SCHEMA_PROD,
            domain="t-seed-prod.localhost",
            admin_email="admin@seedprod.local",
            admin_password="pass1234!",
            bot_mode="production",
        )
        with schema_context(self.SCHEMA_PROD):
            demo_count = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()
        self.assertEqual(demo_count, 0)
