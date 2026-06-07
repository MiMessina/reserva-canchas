"""
Tests de aislamiento multi-tenant — Courts y ScheduleBlocks — Sprint 1

Replica EXACTAMENTE el patrón de apps/tenants/tests/test_tenant_isolation.py.

Cobertura:
  1. Court creada en tenant_a NO es visible en tenant_b vía ORM (schema_context).
  2. GET /api/courts/{id} de tenant_a desde cliente de tenant_b → 404.
  3. Court creada en tenant_b NO aparece en el listado de tenant_a.
  4. ScheduleBlock creado en tenant_a NO es visible en tenant_b vía ORM.
  5. El listado de canchas de tenant_b está vacío cuando tenant_a tiene canchas.

Estrategia de setup (misma que test_tenant_isolation.py):
  - tenant_b se crea en setUpClass() para que el middleware lo resuelva.
  - TenantTestCase crea self.tenant (schema='test') automáticamente.
  - setUp() restaura connection.set_tenant(self.tenant) antes de cada test.

Referencias:
  - docs/RBAC.md §5, §7
  - ADR-001, ADR-007
  - apps/tenants/tests/test_tenant_isolation.py (patrón de referencia)
"""

from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from apps.courts.models import Court, ScheduleBlock
from apps.tenants.models import Domain, Tenant
from apps.users.models import User


class TestCourtsIsolation(TenantTestCase):
    """
    Aislamiento de Courts entre tenant_a (self.tenant) y tenant_b.

    setUpClass crea tenant_b fuera de la transacción por-test para que el
    middleware de django-tenants pueda resolverlo por hostname.
    """

    TENANT_B_SCHEMA = "test_courts_tenant_b"
    TENANT_B_DOMAIN = "courts-b.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # crea cls.tenant (schema='test') y lo migra

        from django.conf import settings
        if cls.TENANT_B_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [cls.TENANT_B_DOMAIN]

        # Crear tenant_b (commited, visible para middleware)
        connection.set_schema_to_public()
        cls.tenant_b = Tenant(schema_name=cls.TENANT_B_SCHEMA, name="Complejo B (courts test)")
        cls.tenant_b.save()  # auto_create_schema=True: crea y migra el esquema
        Domain.objects.create(
            domain=cls.TENANT_B_DOMAIN,
            tenant=cls.tenant_b,
            is_primary=True,
        )
        # Restaurar al schema de tenant_a
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        try:
            Domain.objects.filter(tenant=cls.tenant_b).delete()
            cls.tenant_b.delete(force_drop=True)
        except Exception:
            pass
        from django.conf import settings
        if cls.TENANT_B_DOMAIN in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(cls.TENANT_B_DOMAIN)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Restaurar al schema de tenant_a antes de cada test
        connection.set_tenant(self.tenant)
        self.client_a = TenantClient(self.tenant)
        self.client_b = TenantClient(self.tenant_b)

        # Crear admin en tenant_a para autenticarse
        self.admin_a = User.objects.create_user(
            email="admin@courts-a.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        login_a = self.client_a.post(
            "/api/auth/login/",
            {"email": "admin@courts-a.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token_a = login_a.json()["access"]

        # Crear admin en tenant_b para autenticarse
        with schema_context(self.TENANT_B_SCHEMA):
            self.admin_b = User.objects.create_user(
                email="admin@courts-b.localhost",
                password="adminpass123",
                role=User.Role.TENANT_ADMIN,
                is_staff=True,
            )
        login_b = self.client_b.post(
            "/api/auth/login/",
            {"email": "admin@courts-b.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token_b = login_b.json()["access"]

        # IMPORTANTE: TenantClient ejecuta requests que cambian el search_path
        # vía TenantMainMiddleware. Hay que restaurar la conexión al schema de
        # tenant_a explícitamente AL FINAL del setUp, después de todos los requests.
        connection.set_tenant(self.tenant)

    def _create_court_via_api(self, client, token, name="Cancha Iso"):
        """Crea una cancha vía API y retorna el id."""
        response = client.post(
            "/api/courts/",
            {
                "name": name,
                "court_type": "futbol_5",
                "surface": "",
                "base_price": "4000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201, f"Error creando cancha: {response.content}")
        return response.json()["id"]

    # -----------------------------------------------------------------------
    # Caso 1: Court de tenant_a no visible en tenant_b (ORM)
    # -----------------------------------------------------------------------

    def test_court_created_in_tenant_a_not_visible_in_tenant_b_orm(self):
        """Court creada en esquema A no aparece en esquema B vía ORM."""
        # Crear cancha directamente en el ORM de tenant_a
        court_a = Court.objects.create(
            name="Cancha Solo A",
            court_type="padel",
            surface="moqueta",
            base_price="5000.00",
            slot_duration_minutes=90,
        )

        with schema_context(self.TENANT_B_SCHEMA):
            exists_in_b = Court.objects.filter(name="Cancha Solo A").exists()

        self.assertFalse(exists_in_b, "FALLA: Court de tenant_a visible en tenant_b.")
        # En tenant_a sigue existiendo
        self.assertTrue(Court.objects.filter(pk=court_a.pk).exists())

    # -----------------------------------------------------------------------
    # Caso 2: GET /api/courts/{id} de tenant_a desde cliente de tenant_b → 404
    # -----------------------------------------------------------------------

    def test_court_from_tenant_a_returns_404_via_tenant_b_client(self):
        """GET /api/courts/{id} de tenant_a usando el cliente de tenant_b → 404."""
        court_id = self._create_court_via_api(self.client_a, self.token_a, name="Cancha HTTP A")

        # Intentar acceder con el cliente de tenant_b
        response = self.client_b.get(
            f"/api/courts/{court_id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
        )
        self.assertEqual(
            response.status_code,
            404,
            f"FALLA: cliente de tenant_b obtuvo {response.status_code} en lugar de 404.",
        )

    # -----------------------------------------------------------------------
    # Caso 3: Court de tenant_b no aparece en listado de tenant_a
    # -----------------------------------------------------------------------

    def test_court_created_in_tenant_b_not_in_tenant_a_list(self):
        """Court creada en tenant_b no aparece en el listado de tenant_a."""
        with schema_context(self.TENANT_B_SCHEMA):
            Court.objects.create(
                name="Cancha Solo B",
                court_type="futbol_7",
                surface="",
                base_price="3000.00",
                slot_duration_minutes=60,
            )

        # Listar canchas en tenant_a
        response = self.client_a.get(
            "/api/courts/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", response.json())
        names = [c["name"] for c in results]
        self.assertNotIn("Cancha Solo B", names, "FALLA: cancha de tenant_b visible en listado de tenant_a.")

    # -----------------------------------------------------------------------
    # Caso 4: ScheduleBlock de tenant_a no visible en tenant_b (ORM)
    # -----------------------------------------------------------------------

    def test_schedule_block_created_in_tenant_a_not_visible_in_tenant_b(self):
        """ScheduleBlock creado en esquema A no aparece en esquema B vía ORM."""
        court_a = Court.objects.create(
            name="Cancha Para Bloque",
            court_type="padel",
            surface="",
            base_price="2000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=court_a,
            weekday=0,
            open_time="08:00",
            close_time="12:00",
        )

        with schema_context(self.TENANT_B_SCHEMA):
            count_in_b = ScheduleBlock.objects.count()

        self.assertEqual(count_in_b, 0, f"FALLA: ScheduleBlock de tenant_a visible en tenant_b ({count_in_b} bloques).")

    # -----------------------------------------------------------------------
    # Caso 5: GET /api/schedule-blocks/{id} de tenant_a desde cliente de tenant_b → 404
    # -----------------------------------------------------------------------

    def test_schedule_block_from_tenant_a_returns_404_via_tenant_b_client(self):
        """GET /api/schedule-blocks/{id} de tenant_a usando cliente de tenant_b → 404."""
        court_a = Court.objects.create(
            name="Cancha Bloque HTTP",
            court_type="padel",
            surface="",
            base_price="3000.00",
            slot_duration_minutes=60,
        )
        block_a = ScheduleBlock.objects.create(
            court=court_a,
            weekday=1,
            open_time="09:00",
            close_time="13:00",
        )

        connection.set_tenant(self.tenant)

        response = self.client_b.get(
            f"/api/schedule-blocks/{block_a.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
        )
        self.assertEqual(
            response.status_code,
            404,
            f"FALLA: cliente de tenant_b obtuvo {response.status_code} en lugar de 404.",
        )

    # -----------------------------------------------------------------------
    # Caso 6: listado de canchas de tenant_b vacío cuando tenant_a tiene canchas
    # -----------------------------------------------------------------------

    def test_tenant_b_courts_empty_when_tenant_a_has_courts(self):
        """Tabla de canchas de tenant_b vacía aunque tenant_a tenga canchas."""
        Court.objects.create(
            name="Cancha A1", court_type="futbol_5", surface="", base_price="1000.00", slot_duration_minutes=60
        )
        Court.objects.create(
            name="Cancha A2", court_type="padel", surface="", base_price="2000.00", slot_duration_minutes=90
        )

        with schema_context(self.TENANT_B_SCHEMA):
            count_b = Court.objects.count()

        self.assertEqual(count_b, 0, f"FALLA: tenant_b muestra {count_b} canchas de tenant_a.")
