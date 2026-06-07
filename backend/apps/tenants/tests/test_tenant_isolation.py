"""
Tests de aislamiento multi-tenant — Sprint 0 DoD (SPRINT_0.md §7)

Verifican que dos complejos (tenants) con esquemas PostgreSQL separados
no pueden ver ni acceder a los datos del otro.

Cobertura:
  1. Un User creado en el esquema de tenant_a NO existe en el esquema de tenant_b.
  2. Datos múltiples en tenant_a no se filtran en tenant_b (queryset vacío completo).
  3. Un User creado en tenant_b NO existe en el esquema de tenant_a.
  4. El healthcheck responde 200 desde el cliente de tenant_b.
  5. Credenciales de tenant_a no autentican en tenant_b (401).
  6. El mismo email puede existir en dos tenants sin conflicto.
  7. Roles son independientes entre tenants.

Referencias:
  - docs/SPRINT_0.md §7: "django-tenants aísla dos tenants de prueba"
  - docs/RBAC.md §5 y §7
  - ADR-001, ADR-007

Estrategia de setup:
  tenant_b se crea en setUpClass() (fuera de la transacción por-test) para que
  el middleware de django-tenants pueda resolverlo por hostname.
  TenantTestCase crea self.tenant (schema='test') automáticamente.
  Las transacciones por-test de TestCase limpian los Users entre tests sin
  necesidad de borrar/recrear los esquemas.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from apps.tenants.models import Domain, Tenant

User = get_user_model()


class TestTenantIsolation(TenantTestCase):
    """
    Aislamiento entre tenant_a (self.tenant, schema='test') y tenant_b
    (schema='test_tenant_b', creado en setUpClass).

    Por qué setUpClass / tearDownClass:
      TenantTestCase envuelve CADA test en una transacción que se rollbackea.
      Si creamos tenant_b dentro de setUp(), el Domain y el Tenant quedan
      en una transacción sin commitear: el middleware de django-tenants no
      puede resolverlos por hostname, devuelve 404 y los tests fallan.
      Al crear tenant_b en setUpClass() (que corre fuera de esa transacción)
      los datos se commiten realmente y el middleware los encuentra.
    """

    TENANT_B_SCHEMA = "test_tenant_b"
    TENANT_B_DOMAIN = "tenantb.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # crea cls.tenant (schema='test') y lo migra

        # Agregar dominio de tenant_b a ALLOWED_HOSTS igual que TenantTestCase.add_allowed_test_domain()
        from django.conf import settings
        if cls.TENANT_B_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [cls.TENANT_B_DOMAIN]

        # Crear tenant_b en el esquema public (commited, visible para middleware)
        connection.set_schema_to_public()
        cls.tenant_b = Tenant(schema_name=cls.TENANT_B_SCHEMA, name="Complejo B (test)")
        cls.tenant_b.save()  # auto_create_schema=True: crea y migra el esquema
        Domain.objects.create(
            domain=cls.TENANT_B_DOMAIN,
            tenant=cls.tenant_b,
            is_primary=True,
        )
        # Restaurar el esquema del tenant_a para los tests
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        # Borrar tenant_b y su esquema antes de que super() borre tenant_a
        connection.set_schema_to_public()
        try:
            Domain.objects.filter(tenant=cls.tenant_b).delete()
            cls.tenant_b.delete(force_drop=True)
        except Exception:
            pass
        # Limpiar ALLOWED_HOSTS
        from django.conf import settings
        if cls.TENANT_B_DOMAIN in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(cls.TENANT_B_DOMAIN)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # El middleware de django-tenants modifica connection.schema_name durante
        # la ejecución de requests. Hay que restaurarlo explícitamente antes de
        # cada test para que las queries ORM corran en el schema correcto (tenant_a).
        connection.set_tenant(self.tenant)
        self.client_a = TenantClient(self.tenant)
        self.client_b = TenantClient(self.tenant_b)

    # -----------------------------------------------------------------------
    # Caso 1: usuario de tenant_a no existe en tenant_b (ORM)
    # -----------------------------------------------------------------------

    def test_user_created_in_tenant_a_not_visible_in_tenant_b(self):
        """User creado en tenant_a no aparece en tenant_b."""
        User.objects.create_user(
            email="jugador@tenant-a.localhost",
            password="testpass123",
            role=User.Role.PLAYER,
        )

        with schema_context(self.TENANT_B_SCHEMA):
            exists_in_b = User.objects.filter(email="jugador@tenant-a.localhost").exists()
            count_in_b = User.objects.filter(email="jugador@tenant-a.localhost").count()

        self.assertFalse(exists_in_b, "FALLA: usuario de tenant_a visible en tenant_b.")
        self.assertEqual(count_in_b, 0)
        self.assertTrue(User.objects.filter(email="jugador@tenant-a.localhost").exists())

    # -----------------------------------------------------------------------
    # Caso 2: usuario de tenant_b no existe en tenant_a (inverso)
    # -----------------------------------------------------------------------

    def test_user_created_in_tenant_b_not_visible_in_tenant_a(self):
        """User creado en tenant_b no aparece en tenant_a."""
        with schema_context(self.TENANT_B_SCHEMA):
            User.objects.create_user(
                email="admin@tenant-b.localhost",
                password="adminpass123",
                role=User.Role.TENANT_ADMIN,
                is_staff=True,
            )

        exists_in_a = User.objects.filter(email="admin@tenant-b.localhost").exists()
        self.assertFalse(exists_in_a, "FALLA: usuario de tenant_b visible en tenant_a.")

        with schema_context(self.TENANT_B_SCHEMA):
            exists_in_b = User.objects.filter(email="admin@tenant-b.localhost").exists()
        self.assertTrue(exists_in_b)

    # -----------------------------------------------------------------------
    # Caso 3: queryset de tenant_b vacío cuando tenant_a tiene datos
    # -----------------------------------------------------------------------

    def test_tenant_b_queryset_empty_when_tenant_a_has_users(self):
        """Tabla de usuarios de tenant_b está vacía aunque tenant_a tenga datos."""
        User.objects.create_user(email="p1@a.localhost", password="pass", role=User.Role.PLAYER)
        User.objects.create_user(email="p2@a.localhost", password="pass", role=User.Role.PLAYER)
        User.objects.create_user(email="op@a.localhost", password="pass", role=User.Role.OPERATOR)

        with schema_context(self.TENANT_B_SCHEMA):
            count_b = User.objects.count()

        self.assertEqual(count_b, 0, f"FALLA: tenant_b muestra {count_b} usuarios de tenant_a.")

    # -----------------------------------------------------------------------
    # Caso 4: healthcheck responde 200 en ambos tenants
    # -----------------------------------------------------------------------

    def test_healthcheck_responds_in_both_tenants(self):
        """GET /api/health/ devuelve 200 desde client_a y client_b."""
        response_a = self.client_a.get("/api/health/")
        response_b = self.client_b.get("/api/health/")

        self.assertEqual(response_a.status_code, 200, f"Healthcheck falló en tenant_a: {response_a.status_code}")
        self.assertEqual(response_b.status_code, 200, f"Healthcheck falló en tenant_b: {response_b.status_code}")

    # -----------------------------------------------------------------------
    # Caso 5: credenciales de tenant_a no autentican en tenant_b (HTTP)
    # -----------------------------------------------------------------------

    def test_credentials_of_tenant_a_do_not_authenticate_in_tenant_b(self):
        """Login con credenciales de tenant_a desde client_b → 401."""
        User.objects.create_user(
            email="crossuser@tenant-a.localhost",
            password="secret123",
            role=User.Role.PLAYER,
        )

        response = self.client_b.post(
            "/api/auth/login/",
            {"email": "crossuser@tenant-a.localhost", "password": "secret123"},
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
            f"FALLA: login de tenant_a devolvió {response.status_code} en tenant_b (esperado 401).",
        )

    # -----------------------------------------------------------------------
    # Caso 6: el mismo email puede existir en dos tenants (sin conflicto)
    # -----------------------------------------------------------------------

    def test_same_email_can_exist_independently_in_each_tenant(self):
        """El mismo email existe en ambos tenants; ambos logins retornan 200."""
        shared_email = "recepcionista@complejo.com"
        shared_password = "pass1234"

        User.objects.create_user(email=shared_email, password=shared_password, role=User.Role.OPERATOR)

        with schema_context(self.TENANT_B_SCHEMA):
            User.objects.create_user(email=shared_email, password=shared_password, role=User.Role.OPERATOR)

        response_a = self.client_a.post(
            "/api/auth/login/",
            {"email": shared_email, "password": shared_password},
            content_type="application/json",
        )
        response_b = self.client_b.post(
            "/api/auth/login/",
            {"email": shared_email, "password": shared_password},
            content_type="application/json",
        )

        self.assertEqual(response_a.status_code, 200, f"Login en tenant_a falló: {response_a.content}")
        self.assertEqual(response_b.status_code, 200, f"Login en tenant_b falló: {response_b.content}")

        token_a = response_a.json().get("access", "")
        token_b = response_b.json().get("access", "")
        self.assertNotEqual(token_a, token_b, "Los tokens deben ser distintos (usuarios en esquemas distintos).")

    # -----------------------------------------------------------------------
    # Caso 7: roles independientes entre tenants
    # -----------------------------------------------------------------------

    def test_roles_are_independent_between_tenants(self):
        """tenant_admin en A y player en B no se mezclan entre esquemas."""
        User.objects.create_user(email="admin@complejoa.com", password="pass", role=User.Role.TENANT_ADMIN)

        with schema_context(self.TENANT_B_SCHEMA):
            User.objects.create_user(email="player@complejob.com", password="pass", role=User.Role.PLAYER)

        exists_player_b_in_a = User.objects.filter(email="player@complejob.com").exists()
        with schema_context(self.TENANT_B_SCHEMA):
            exists_admin_a_in_b = User.objects.filter(email="admin@complejoa.com").exists()

        self.assertFalse(exists_player_b_in_a, "FALLA: player de tenant_b visible en tenant_a.")
        self.assertFalse(exists_admin_a_in_b, "FALLA: admin de tenant_a visible en tenant_b.")
