"""
Tests del toggle mock/producción del visor de conversaciones del bot (Sprint 10).

Cobertura:
  1. Tenant.bot_mode default es 'production'.
  2. Tenant.BotMode.choices contiene exactamente 'mock' y 'production'.
  3. get_bot_mode() retorna el valor del tenant activo (sin restart).
  4. GET /api/bot/conversations/ en modo mock → solo mensajes [DEMO], bot_mode='mock'.
  5. GET /api/bot/conversations/ en modo production → excluye [DEMO], bot_mode='production'.
  6. Respuesta siempre tiene claves bot_mode y conversations.
  7. Sin JWT → 401.
  8. Logs con is_active=False no aparecen aunque sean [DEMO].
  9. PATCH /api/platform/tenants/{id}/ persiste bot_mode (integración platform-admin).
  10. PATCH con valor inválido → 400.
  11. GET /api/platform/tenants/ incluye campo bot_mode.

Patrones aplicados:
  - TenantTestCase para contexto de tenant real.
  - JWT generado con RefreshToken.for_user() en setUp (evita TenantClient para login,
    que falla cuando connection.tenant está activo y tenants_domain está vacío en ese schema).
  - HTTP_HOST explícito en TenantClient: el dominio se obtiene en schema público antes
    de set_tenant(), porque tenants_domain solo está poblado en public (apps.tenants en
    TENANT_APPS crea la tabla pero no la llena en cada esquema de tenant).
  - Tenant.save() ANTES de connection.set_tenant() — Tenant vive en public.
  - PlatformAdmin (no auth.User) para tests de platform — el login de /api/platform/
    autentica contra PlatformAdmin.objects, no contra auth.User (swapped).
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings  # TestCase: solo para TestTenantBotModeDefault
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.agent.models import BOT_DEMO_MARKER, BotConversationLog
from apps.tenants.models import Domain, PlatformAdmin, Tenant
from apps.tenants.selectors import get_bot_mode

PLATFORM_URLCONF = "config.urls_public"


# ---------------------------------------------------------------------------
# 1 & 2. Modelo: bot_mode default y choices
# ---------------------------------------------------------------------------

class TestTenantBotModeDefault(TestCase):
    """Tenant.bot_mode debe ser 'production' en todos los tenants nuevos."""

    def setUp(self):
        connection.set_schema_to_public()
        self.tenant = Tenant(schema_name="t_botmode_default", name="Test BotMode Default")
        self.tenant.save()
        Domain.objects.create(
            domain="botmode-default.localhost",
            tenant=self.tenant,
            is_primary=True,
        )

    def tearDown(self):
        connection.set_schema_to_public()
        Domain.objects.filter(tenant=self.tenant).delete()
        try:
            self.tenant.delete(force_drop=True)
        except Exception:
            pass

    def test_bot_mode_default_is_production(self):
        """Un Tenant recién creado tiene bot_mode='production'."""
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.bot_mode, "production")

    def test_bot_mode_choices_are_valid(self):
        """BotMode.choices contiene exactamente 'mock' y 'production'."""
        valid = {c[0] for c in Tenant.BotMode.choices}
        self.assertIn("mock", valid)
        self.assertIn("production", valid)
        self.assertEqual(len(valid), 2)


# ---------------------------------------------------------------------------
# 3. Selector: get_bot_mode()
# ---------------------------------------------------------------------------

class TestGetBotModeSelector(TenantTestCase):
    """
    get_bot_mode() lee connection.tenant.bot_mode del tenant activo.

    Patrón: Tenant.save() en schema público → luego set_tenant() para simular request.
    """

    def test_get_bot_mode_returns_production_by_default(self):
        """Con bot_mode='production' (default), get_bot_mode() retorna 'production'."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode"])
        connection.set_tenant(self.tenant)
        self.assertEqual(get_bot_mode(), "production")

    def test_get_bot_mode_returns_mock_after_update(self):
        """Tras cambiar bot_mode a 'mock', get_bot_mode() retorna 'mock' sin restart."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = "mock"
        self.tenant.save(update_fields=["bot_mode"])
        self.tenant.refresh_from_db()
        connection.set_tenant(self.tenant)
        self.assertEqual(get_bot_mode(), "mock")


# ---------------------------------------------------------------------------
# 4, 5, 6, 7, 8. Vista: GET /api/bot/conversations/
# ---------------------------------------------------------------------------

class TestBotConversationsView(TenantTestCase):
    """
    Tests de GET /api/bot/conversations/ con filtro por bot_mode.

    setUp obtiene el dominio del tenant EN SCHEMA PÚBLICO antes de activar el
    tenant, para que HTTP_HOST funcione correctamente en TenantClient.

    El JWT se genera directamente con RefreshToken.for_user() en lugar de
    hacer POST /api/auth/login/ desde TenantClient, porque TenantClient.generic()
    llama a get_primary_domain() internamente y falla si tenants_domain está vacío
    en el schema del tenant activo.
    """

    def setUp(self):
        super().setUp()

        # Obtener dominio del tenant en schema público (donde tenants_domain está poblado)
        connection.set_schema_to_public()
        primary = self.tenant.domains.filter(is_primary=True).first()
        self.tenant_domain = primary.domain if primary else "tenant.test.com"

        # Activar tenant para crear datos de test
        connection.set_tenant(self.tenant)

        User = get_user_model()
        self.admin = User.objects.create_user(
            email="admin@botview.test",
            password="testpass123",
            role="tenant_admin",
        )

        self.demo_log = BotConversationLog.objects.create(
            phone="5491100000001@c.us",
            player_name="Demo Player",
            direction="inbound",
            message=f"{BOT_DEMO_MARKER} Hola, quiero reservar",
        )
        self.real_log = BotConversationLog.objects.create(
            phone="5491100000002@c.us",
            player_name="Real Player",
            direction="inbound",
            message="Hola, quiero reservar",
        )

        # JWT directo — evita TenantClient.post() en setUp
        refresh = RefreshToken.for_user(self.admin)
        self.token = str(refresh.access_token)

    def _get_conversations(self) -> dict:
        """GET /api/bot/conversations/ autenticado, con HTTP_HOST explícito."""
        connection.set_tenant(self.tenant)
        client = TenantClient(self.tenant)
        resp = client.get(
            "/api/bot/conversations/",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_HOST=self.tenant_domain,
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.content}")
        connection.set_tenant(self.tenant)
        return resp.json()

    def _set_bot_mode(self, mode: str):
        """Cambia bot_mode en schema público y reactiva el tenant."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = mode
        self.tenant.save(update_fields=["bot_mode"])
        self.tenant.refresh_from_db()
        connection.set_tenant(self.tenant)

    # --- Forma de respuesta ---

    def test_response_has_bot_mode_and_conversations_keys(self):
        """La respuesta siempre incluye las claves bot_mode y conversations."""
        data = self._get_conversations()
        self.assertIn("bot_mode", data)
        self.assertIn("conversations", data)

    # --- Modo mock ---

    def test_mock_mode_returns_only_demo_messages(self):
        """En modo mock, conversations solo contiene mensajes [DEMO]."""
        self._set_bot_mode("mock")
        data = self._get_conversations()

        self.assertEqual(data["bot_mode"], "mock")
        phones = {c["phone"] for c in data["conversations"]}
        self.assertIn(self.demo_log.phone, phones)
        self.assertNotIn(self.real_log.phone, phones)

    def test_mock_mode_excludes_real_messages(self):
        """En modo mock ningún mensaje está sin prefijo [DEMO]."""
        self._set_bot_mode("mock")
        data = self._get_conversations()

        all_messages = [msg for conv in data["conversations"] for msg in conv["messages"]]
        for msg in all_messages:
            self.assertTrue(
                msg["message"].startswith(BOT_DEMO_MARKER),
                f"Mensaje sin prefijo [DEMO] en modo mock: {msg['message']!r}",
            )

    # --- Modo production ---

    def test_production_mode_returns_only_real_messages(self):
        """En modo production, conversations solo contiene mensajes sin [DEMO]."""
        self._set_bot_mode("production")
        data = self._get_conversations()

        self.assertEqual(data["bot_mode"], "production")
        phones = {c["phone"] for c in data["conversations"]}
        self.assertIn(self.real_log.phone, phones)
        self.assertNotIn(self.demo_log.phone, phones)

    def test_production_mode_excludes_demo_messages(self):
        """En modo production ningún mensaje tiene prefijo [DEMO]."""
        self._set_bot_mode("production")
        data = self._get_conversations()

        all_messages = [msg for conv in data["conversations"] for msg in conv["messages"]]
        for msg in all_messages:
            self.assertFalse(
                msg["message"].startswith(BOT_DEMO_MARKER),
                f"Mensaje [DEMO] apareció en modo production: {msg['message']!r}",
            )

    # --- Autenticación ---

    def test_unauthenticated_returns_401(self):
        """GET /api/bot/conversations/ sin JWT → 401."""
        connection.set_tenant(self.tenant)
        client = TenantClient(self.tenant)
        resp = client.get(
            "/api/bot/conversations/",
            HTTP_HOST=self.tenant_domain,
        )
        self.assertIn(resp.status_code, [401, 403])

    # --- Soft-delete ---

    def test_soft_deleted_logs_not_shown_in_mock_mode(self):
        """Logs con is_active=False no aparecen aunque sean [DEMO]."""
        self._set_bot_mode("mock")
        self.demo_log.is_active = False
        self.demo_log.save(update_fields=["is_active"])

        data = self._get_conversations()
        phones = {c["phone"] for c in data["conversations"]}
        self.assertNotIn(self.demo_log.phone, phones)

        # Restaurar
        self.demo_log.is_active = True
        self.demo_log.save(update_fields=["is_active"])


# ---------------------------------------------------------------------------
# 9, 10, 11. Platform-admin: PATCH y GET bot_mode
# ---------------------------------------------------------------------------

class TestBotModePlatformPatch(TenantTestCase):
    """
    PATCH /api/platform/tenants/{id}/ acepta y persiste bot_mode.
    GET  /api/platform/tenants/       incluye bot_mode en la respuesta.

    Hereda de TenantTestCase para que la creación de schemas sea gestionada
    correctamente (TestCase wrapping transaccional es incompatible con DDL
    de esquemas PostgreSQL). Los endpoints de /api/platform/ se acceden con
    override_settings(ROOT_URLCONF=PLATFORM_URLCONF) por método.

    Usa PlatformAdmin (no auth.User) — el login de /api/platform/auth/login/
    autentica contra PlatformAdmin.objects. auth.User está swapped a users.User
    y su manager está desactivado.

    El tenant que se edita es self.tenant (del TenantTestCase) — no se crea
    uno nuevo para evitar el conflicto DDL / transacción de TestCase.
    """

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()

        self.platform_admin = PlatformAdmin(email="sysadmin_botmode@platform.local")
        self.platform_admin.set_password("superpassword123")
        self.platform_admin.save()

        self.platform_client = APIClient()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.post(
                "/api/platform/auth/login/",
                {"email": "sysadmin_botmode@platform.local", "password": "superpassword123"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Login falló: {resp.data}")
        self.platform_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def tearDown(self):
        connection.set_schema_to_public()
        PlatformAdmin.objects.filter(email="sysadmin_botmode@platform.local").delete()
        connection.set_tenant(self.tenant)
        super().tearDown()

    def test_patch_bot_mode_to_mock(self):
        """PATCH bot_mode='mock' → persiste en la DB."""
        connection.set_schema_to_public()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "mock"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.bot_mode, "mock")

        # Restaurar default para no afectar otros tests
        self.tenant.bot_mode = "production"
        self.tenant.save(update_fields=["bot_mode"])

    def test_patch_bot_mode_to_production(self):
        """PATCH bot_mode='production' desde mock → persiste en la DB."""
        connection.set_schema_to_public()
        self.tenant.bot_mode = "mock"
        self.tenant.save(update_fields=["bot_mode"])

        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "production"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, f"Expected 200: {resp.data}")
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.bot_mode, "production")

    def test_patch_invalid_bot_mode_returns_400(self):
        """PATCH bot_mode con valor inválido → 400."""
        connection.set_schema_to_public()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.patch(
                f"/api/platform/tenants/{self.tenant.pk}/",
                {"bot_mode": "invalid_value"},
                format="json",
            )
        self.assertEqual(resp.status_code, 400, f"Expected 400: {resp.data}")

    def test_list_tenants_includes_bot_mode_field(self):
        """GET /api/platform/tenants/ incluye el campo bot_mode en cada tenant."""
        connection.set_schema_to_public()
        with override_settings(ROOT_URLCONF=PLATFORM_URLCONF):
            resp = self.platform_client.get("/api/platform/tenants/")
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        results = data.get("results", data) if isinstance(data, dict) else data
        if results:
            self.assertIn("bot_mode", results[0], "bot_mode ausente en la lista de tenants")
