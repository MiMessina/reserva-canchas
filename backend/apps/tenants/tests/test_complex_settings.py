"""
Tests de ComplexSettings — configuración del complejo por tenant.

Cobertura:
  1. GET /api/settings/ sin login retorna 200 con la config del tenant.
  2. GET /api/settings/ cuando no existe config retorna objeto con campos vacíos (no 404).
  3. PATCH /api/settings/ como tenant_admin actualiza los campos.
  4. PATCH /api/settings/ como operator retorna 403.
  5. PATCH /api/settings/ como player retorna 403.
  6. Aislamiento: config del tenant A no es visible desde tenant B.

Referencias:
  - docs/RBAC.md §4: solo tenant_admin puede modificar configuración del complejo.
  - docs/WORKFLOW.md: GET es público (AllowAny), acotado al tenant del dominio.
  - ADR-001: aislamiento por esquema PostgreSQL.
  - ADR-007: usuarios por tenant.

Estrategia:
  TenantTestCase gestiona el ciclo de vida del esquema de prueba (self.tenant,
  schema='test'). Para el test de aislamiento se crea tenant_b en setUpClass()
  (fuera de la transacción por-test) siguiendo el mismo patrón de test_tenant_isolation.py.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.tenants.models import ComplexSettings, Domain, Tenant

User = get_user_model()

# Dominio creado por TenantTestCase.setUpClass() para self.tenant
TENANT_A_HOST = "tenant.test.com"


class TestComplexSettingsGet(TenantTestCase):
    """Tests de lectura (GET) del endpoint de configuración del complejo."""

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)
        # APIClient con HTTP_HOST explícito evita el bug de get_primary_domain()
        # cuando connection.set_tenant() está activo (django-tenants 3.6.1)
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = TENANT_A_HOST
        ComplexSettings.objects.all().delete()

    # -----------------------------------------------------------------------
    # Caso 1: GET público retorna 200
    # -----------------------------------------------------------------------

    def test_get_settings_public(self):
        """GET /api/settings/ sin login retorna 200 con la config del tenant."""
        ComplexSettings.objects.create(
            complex_name="Complejo Los Pinos",
            phone="+5491112345678",
            instagram="complejolospinos",
        )

        response = self.client.get("/api/settings/")

        self.assertEqual(response.status_code, 200, f"Esperado 200, obtenido {response.status_code}: {response.content}")
        data = response.json()
        self.assertEqual(data["complex_name"], "Complejo Los Pinos")
        self.assertEqual(data["phone"], "+5491112345678")
        self.assertEqual(data["instagram"], "complejolospinos")

    # -----------------------------------------------------------------------
    # Caso 2: GET cuando no existe config retorna objeto con campos vacíos
    # -----------------------------------------------------------------------

    def test_get_settings_creates_if_not_exists(self):
        """GET cuando no existe config retorna objeto con campos vacíos (no 404)."""
        # Verificamos que no hay config previa
        self.assertEqual(ComplexSettings.objects.count(), 0)

        response = self.client.get("/api/settings/")

        self.assertEqual(response.status_code, 200, f"Esperado 200, obtenido {response.status_code}: {response.content}")
        data = response.json()
        # El service crea la instancia con complex_name vacío
        self.assertEqual(data["complex_name"], "")
        self.assertEqual(data["cbu_alias"], "")
        self.assertEqual(data["cbu_number"], "")
        self.assertEqual(data["account_holder"], "")
        self.assertEqual(data["phone"], "")
        self.assertEqual(data["instagram"], "")
        self.assertEqual(data["whatsapp"], "")
        # Debe haberse creado en la DB
        self.assertEqual(ComplexSettings.objects.count(), 1)


class TestComplexSettingsPatch(TenantTestCase):
    """Tests de escritura (PATCH) del endpoint de configuración del complejo."""

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = TENANT_A_HOST
        ComplexSettings.objects.all().delete()

        # Usuarios para los tests de permisos
        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
        )
        self.operator = User.objects.create_user(
            email="operator@test.localhost",
            password="operpass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@test.localhost",
            password="playerpass123",
            role=User.Role.PLAYER,
        )

    def _get_token(self, email, password):
        """Helper: obtiene JWT para el usuario dado."""
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló para {email}: {response.content}")
        return response.json()["access"]

    # -----------------------------------------------------------------------
    # Caso 3: PATCH como tenant_admin actualiza campos
    # -----------------------------------------------------------------------

    def test_patch_settings_as_admin(self):
        """tenant_admin puede actualizar campos de la configuración."""
        token = self._get_token("admin@test.localhost", "adminpass123")

        payload = {
            "complex_name": "Complejo Los Pinos",
            "cbu_alias": "complejo.pinos",
            "cbu_number": "0000003100025611011234",
            "account_holder": "Juan Perez",
            "phone": "+5491112345678",
            "instagram": "complejolospinos",
            "whatsapp": "+5491112345678",
            "payment_instructions": "Transferí al CBU y enviá comprobante.",
        }

        response = self.client.patch(
            "/api/settings/",
            payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200, f"Esperado 200, obtenido {response.status_code}: {response.content}")
        data = response.json()
        self.assertEqual(data["complex_name"], "Complejo Los Pinos")
        self.assertEqual(data["cbu_alias"], "complejo.pinos")
        self.assertEqual(data["phone"], "+5491112345678")

        # Verificar persistencia en DB
        obj = ComplexSettings.objects.get()
        self.assertEqual(obj.complex_name, "Complejo Los Pinos")
        self.assertEqual(obj.cbu_alias, "complejo.pinos")

    def test_patch_settings_partial_update(self):
        """PATCH parcial: solo se actualizan los campos enviados, los demás no cambian."""
        # Crear config inicial
        ComplexSettings.objects.create(
            complex_name="Nombre Inicial",
            phone="+5491100000000",
            instagram="insta_inicial",
        )

        token = self._get_token("admin@test.localhost", "adminpass123")

        # Solo actualizar el teléfono
        response = self.client.patch(
            "/api/settings/",
            {"phone": "+5491199999999"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # El teléfono se actualizó
        self.assertEqual(data["phone"], "+5491199999999")
        # El nombre y el instagram no cambiaron
        self.assertEqual(data["complex_name"], "Nombre Inicial")
        self.assertEqual(data["instagram"], "insta_inicial")

    # -----------------------------------------------------------------------
    # Caso 4: PATCH como operator retorna 403
    # -----------------------------------------------------------------------

    def test_patch_settings_as_operator_forbidden(self):
        """operator recibe 403 al intentar modificar la configuración del complejo."""
        token = self._get_token("operator@test.localhost", "operpass123")

        response = self.client.patch(
            "/api/settings/",
            {"complex_name": "Intento no autorizado"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code,
            403,
            f"Esperado 403 para operator, obtenido {response.status_code}: {response.content}",
        )

    # -----------------------------------------------------------------------
    # Caso 5: PATCH como player retorna 403
    # -----------------------------------------------------------------------

    def test_patch_settings_as_player_forbidden(self):
        """player recibe 403 al intentar modificar la configuración del complejo."""
        token = self._get_token("player@test.localhost", "playerpass123")

        response = self.client.patch(
            "/api/settings/",
            {"complex_name": "Intento no autorizado"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code,
            403,
            f"Esperado 403 para player, obtenido {response.status_code}: {response.content}",
        )

    def test_patch_settings_unauthenticated_forbidden(self):
        """Sin token retorna 401."""
        response = self.client.patch(
            "/api/settings/",
            {"complex_name": "Sin auth"},
            content_type="application/json",
        )

        self.assertIn(
            response.status_code,
            [401, 403],
            f"Esperado 401/403 sin auth, obtenido {response.status_code}: {response.content}",
        )


class TestComplexSettingsTenantIsolation(TenantTestCase):
    """
    Test de aislamiento: la config del tenant A no es visible desde tenant B.

    Estrategia:
      tenant_b se crea en setUpClass() fuera de la transacción por-test,
      siguiendo el mismo patrón de TestTenantIsolation (test_tenant_isolation.py).
    """

    TENANT_B_SCHEMA = "test_settings_tenant_b"
    TENANT_B_DOMAIN = "settings-tenantb.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from django.conf import settings as django_settings
        if cls.TENANT_B_DOMAIN not in django_settings.ALLOWED_HOSTS:
            django_settings.ALLOWED_HOSTS += [cls.TENANT_B_DOMAIN]

        connection.set_schema_to_public()
        cls.tenant_b = Tenant(schema_name=cls.TENANT_B_SCHEMA, name="Complejo B (settings test)")
        cls.tenant_b.save()
        Domain.objects.create(
            domain=cls.TENANT_B_DOMAIN,
            tenant=cls.tenant_b,
            is_primary=True,
        )
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        try:
            Domain.objects.filter(tenant=cls.tenant_b).delete()
            cls.tenant_b.delete(force_drop=True)
        except Exception:
            pass
        from django.conf import settings as django_settings
        if cls.TENANT_B_DOMAIN in django_settings.ALLOWED_HOSTS:
            django_settings.ALLOWED_HOSTS.remove(cls.TENANT_B_DOMAIN)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)
        ComplexSettings.objects.all().delete()
        with schema_context(self.TENANT_B_SCHEMA):
            ComplexSettings.objects.all().delete()

        self.client_a = APIClient()
        self.client_a.defaults["HTTP_HOST"] = TENANT_A_HOST
        self.client_b = APIClient()
        self.client_b.defaults["HTTP_HOST"] = self.TENANT_B_DOMAIN

    # -----------------------------------------------------------------------
    # Caso 6: aislamiento — config de tenant A no visible desde tenant B
    # -----------------------------------------------------------------------

    def test_tenant_isolation(self):
        """
        Config del tenant A no es visible desde tenant B (y viceversa).

        Verifica:
          - GET desde client_a retorna la config de tenant A.
          - GET desde client_b retorna su propia config (con campos vacíos,
            no los datos de tenant A).
          - La config de tenant A no aparece en el esquema de tenant B.
        """
        # Crear config en tenant A (esquema activo = self.tenant)
        ComplexSettings.objects.create(
            complex_name="Complejo A - Solo mío",
            cbu_alias="complejo.a",
            phone="+5491100000001",
        )

        # GET desde tenant A: debe retornar SU config
        response_a = self.client_a.get("/api/settings/")
        self.assertEqual(response_a.status_code, 200)
        data_a = response_a.json()
        self.assertEqual(data_a["complex_name"], "Complejo A - Solo mío")
        self.assertEqual(data_a["cbu_alias"], "complejo.a")

        # GET desde tenant B: NO debe retornar los datos de tenant A
        response_b = self.client_b.get("/api/settings/")
        self.assertEqual(response_b.status_code, 200)
        data_b = response_b.json()
        # Tenant B tiene su propia config vacía (creada por get_or_create)
        self.assertEqual(data_b["complex_name"], "", "FALLA: tenant B puede ver el nombre de tenant A.")
        self.assertEqual(data_b["cbu_alias"], "", "FALLA: tenant B puede ver el CBU de tenant A.")

        # Verificar directamente en el esquema de tenant B que no hay datos de A
        with schema_context(self.TENANT_B_SCHEMA):
            count_b = ComplexSettings.objects.filter(complex_name="Complejo A - Solo mío").count()
        self.assertEqual(count_b, 0, "FALLA: config de tenant A existe en el esquema de tenant B.")

    def test_tenant_b_can_have_independent_settings(self):
        """Cada tenant puede tener su propia config independiente."""
        # Config en tenant A
        ComplexSettings.objects.create(complex_name="Complejo Alpha", instagram="alpha_complejo")

        # Config en tenant B
        with schema_context(self.TENANT_B_SCHEMA):
            ComplexSettings.objects.create(complex_name="Complejo Beta", instagram="beta_complejo")

        # Tenant A solo ve su config
        response_a = self.client_a.get("/api/settings/")
        self.assertEqual(response_a.json()["complex_name"], "Complejo Alpha")
        self.assertEqual(response_a.json()["instagram"], "alpha_complejo")

        # Tenant B solo ve su config
        response_b = self.client_b.get("/api/settings/")
        self.assertEqual(response_b.json()["complex_name"], "Complejo Beta")
        self.assertEqual(response_b.json()["instagram"], "beta_complejo")
