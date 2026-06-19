"""
Tests del seed automático de conversaciones demo al activar bot_mode='mock' (Sprint 13).

Cobertura:
  1. PATCH bot_mode='mock' vía platform-admin → conversaciones [DEMO] en el esquema.
  2. Segundo PATCH a 'mock' no duplica las conversaciones (idempotencia).
  3. Crear tenant con bot_mode='mock' → ya tiene conversaciones [DEMO].
  4. Crear tenant con bot_mode='production' → sin conversaciones [DEMO].

Patrones:
  - Tests 1 y 2 usan TenantTestCase (self.tenant del framework) + PlatformAdmin para PATCH.
  - Tests 3 y 4 usan TestCase + create_tenant_service() directamente.
  - HTTP_HOST explícito en todos los requests de TenantClient (ver feedback_http_host_isolation_tests).
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
# 1 & 2. PATCH via platform-admin — seed y idempotencia
# ---------------------------------------------------------------------------

class TestSeedOnPlatformPatch(TenantTestCase):
    """
    Verifica que PATCH bot_mode='mock' desde platform-admin dispara el seed automático.
    """

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()

        # Asegurar que el tenant parte de production
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode"])

        self.platform_admin = PlatformAdmin(email="sysadmin_seed@platform.local")
        self.platform_admin.set_password("superpassword123")
        self.platform_admin.save()

        self.client_platform = APIClient()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.client_platform.post(
                "/api/platform/auth/login/",
                {"email": "sysadmin_seed@platform.local", "password": "superpassword123"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Login platform falló: {resp.data}")
        self.client_platform.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def tearDown(self):
        connection.set_schema_to_public()
        PlatformAdmin.objects.filter(email="sysadmin_seed@platform.local").delete()
        # Limpiar datos demo del esquema del tenant para no afectar otros tests
        with schema_context(self.tenant.schema_name):
            BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).delete()
        # Restaurar bot_mode
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode"])
        connection.set_tenant(self.tenant)
        super().tearDown()

    def test_patch_mock_seeds_conversations(self):
        """PATCH bot_mode='mock' → el esquema tiene conversaciones [DEMO]."""
        connection.set_schema_to_public()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.client_platform.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")

        with schema_context(self.tenant.schema_name):
            demo_count = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()
        self.assertGreater(demo_count, 0, "No se sembraron conversaciones [DEMO] al activar mock.")

    def test_patch_mock_is_idempotent(self):
        """Segundo PATCH a 'mock' no duplica las conversaciones."""
        connection.set_schema_to_public()

        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            self.client_platform.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )

        with schema_context(self.tenant.schema_name):
            count_after_first = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()

        # Volver a production y luego a mock — el seed ya existe, no debe duplicar
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            self.client_platform.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "production"},
                format="json",
            )
            self.client_platform.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )

        with schema_context(self.tenant.schema_name):
            count_after_second = BotConversationLog.objects.filter(
                message__startswith=BOT_DEMO_MARKER
            ).count()

        self.assertEqual(
            count_after_first,
            count_after_second,
            "El segundo PATCH a mock duplicó las conversaciones de demo.",
        )


# ---------------------------------------------------------------------------
# 3 & 4. create_tenant_service() — seed al crear tenant
# ---------------------------------------------------------------------------

class TestSeedOnTenantCreate(TransactionTestCase):
    """
    Verifica que create_tenant_service() siembra [DEMO] si bot_mode='mock',
    y no siembra nada si bot_mode='production'.

    Usa TransactionTestCase (no TestCase) porque crea/elimina esquemas reales
    vía DDL — operaciones incompatibles con el wrapeo transaccional de TestCase.
    """

    SCHEMA_MOCK = "t_seed_mock"
    SCHEMA_PROD = "t_seed_prod"

    def tearDown(self):
        connection.set_schema_to_public()
        for schema in [self.SCHEMA_MOCK, self.SCHEMA_PROD]:
            try:
                tenant = Tenant.objects.get(schema_name=schema)
                tenant.delete(force_drop=True)
            except Tenant.DoesNotExist:
                pass

    def test_create_tenant_with_mock_seeds_conversations(self):
        """Nuevo tenant con bot_mode='mock' → esquema tiene conversaciones [DEMO] al crearse."""
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
        self.assertGreater(
            demo_count, 0,
            "No se sembraron conversaciones [DEMO] al crear tenant con bot_mode='mock'.",
        )

    def test_create_tenant_with_production_has_no_demo(self):
        """Nuevo tenant con bot_mode='production' → esquema sin conversaciones [DEMO]."""
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
        self.assertEqual(
            demo_count, 0,
            "Se sembraron conversaciones [DEMO] en un tenant con bot_mode='production'.",
        )
