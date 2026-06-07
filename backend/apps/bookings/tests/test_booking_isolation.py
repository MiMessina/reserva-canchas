"""
Tests de aislamiento multi-tenant — Booking y CashMovement — Sprint 2

Replica el patrón de apps/courts/tests/test_courts_isolation.py.

Cobertura:
  1. Booking creada en tenant_a NO es visible en tenant_b vía ORM (schema_context).
  2. GET /api/bookings/{id}/ de tenant_a desde cliente de tenant_b → 404.
  3. CashMovement creado en tenant_a NO es visible en tenant_b vía ORM.

Estrategia de setup:
  - tenant_b se crea en setUpClass() para que el middleware lo resuelva.
  - TenantTestCase crea self.tenant (schema='test') automáticamente.
  - setUp() restaura connection.set_tenant(self.tenant) antes de cada test.

Referencias:
  - docs/RBAC.md §5, §7
  - ADR-001, ADR-007
  - apps/courts/tests/test_courts_isolation.py (patrón de referencia)
"""

from datetime import datetime, timezone as tz

from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock
from apps.tenants.models import Domain, Tenant
from apps.users.models import User


class TestBookingIsolation(TenantTestCase):
    """
    Aislamiento de Booking y CashMovement entre tenant_a (self.tenant) y tenant_b.
    """

    TENANT_B_SCHEMA = "test_booking_tenant_b"
    TENANT_B_DOMAIN = "booking-b.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from django.conf import settings
        if cls.TENANT_B_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [cls.TENANT_B_DOMAIN]

        connection.set_schema_to_public()
        cls.tenant_b = Tenant(
            schema_name=cls.TENANT_B_SCHEMA,
            name="Complejo B (booking test)",
        )
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
        from django.conf import settings
        if cls.TENANT_B_DOMAIN in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(cls.TENANT_B_DOMAIN)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)

        self.client_a = TenantClient(self.tenant)
        self.client_b = TenantClient(self.tenant_b)

        # Admin en tenant_a
        self.admin_a = User.objects.create_user(
            email="admin@booking-a.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        login_a = self.client_a.post(
            "/api/auth/login/",
            {"email": "admin@booking-a.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token_a = login_a.json()["access"]

        # Admin en tenant_b
        with schema_context(self.TENANT_B_SCHEMA):
            self.admin_b = User.objects.create_user(
                email="admin@booking-b.localhost",
                password="adminpass123",
                role=User.Role.TENANT_ADMIN,
                is_staff=True,
            )
        login_b = self.client_b.post(
            "/api/auth/login/",
            {"email": "admin@booking-b.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token_b = login_b.json()["access"]

        # IMPORTANTE: restaurar al esquema de tenant_a después de los requests de login
        connection.set_tenant(self.tenant)

        # Cancha y bloque en tenant_a
        self.court_a = Court.objects.create(
            name="Cancha Aislamiento A",
            court_type="futbol_5",
            surface="",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=self.court_a,
            weekday=0,  # lunes
            open_time="08:00",
            close_time="22:00",
        )

        # Cancha en tenant_b (para tests de aislamiento ORM)
        with schema_context(self.TENANT_B_SCHEMA):
            self.court_b = Court.objects.create(
                name="Cancha Aislamiento B",
                court_type="padel",
                surface="",
                base_price="3000.00",
                slot_duration_minutes=60,
            )

        connection.set_tenant(self.tenant)

    # -----------------------------------------------------------------------
    # Caso 1: Booking de tenant_a no visible en tenant_b (ORM)
    # -----------------------------------------------------------------------

    def test_booking_in_tenant_a_not_visible_in_tenant_b_orm(self):
        """Booking creada en esquema A no aparece en esquema B vía ORM."""
        start = datetime(2027, 1, 4, 11, 0, tzinfo=tz.utc)
        booking_a = Booking.objects.create(
            court=self.court_a,
            guest_name="Jugador Tenant A",
            guest_phone="111",
            start_dt=start,
            end_dt=start.replace(hour=12),
            price="5000.00",
            status=Booking.Status.PENDING_PAYMENT,
        )

        with schema_context(self.TENANT_B_SCHEMA):
            exists_in_b = Booking.objects.filter(guest_name="Jugador Tenant A").exists()

        self.assertFalse(
            exists_in_b,
            "FALLA: Booking de tenant_a visible en tenant_b.",
        )
        # En tenant_a sigue existiendo
        self.assertTrue(Booking.objects.filter(pk=booking_a.pk).exists())

    # -----------------------------------------------------------------------
    # Caso 2: GET /api/bookings/{id}/ de tenant_a desde cliente de tenant_b → 404
    # -----------------------------------------------------------------------

    def test_booking_in_tenant_a_returns_404_via_tenant_b_client(self):
        """GET /api/bookings/{id}/ de tenant_a usando el cliente de tenant_b → 404."""
        start = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        booking_a = Booking.objects.create(
            court=self.court_a,
            guest_name="Jugador HTTP A",
            guest_phone="222",
            start_dt=start,
            end_dt=start.replace(hour=15),
            price="5000.00",
            status=Booking.Status.PENDING_PAYMENT,
        )

        connection.set_tenant(self.tenant)

        # tenant_b intenta acceder con su propio cliente y token
        response = self.client_b.get(
            f"/api/bookings/{booking_a.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
        )
        self.assertEqual(
            response.status_code,
            404,
            f"FALLA: cliente de tenant_b obtuvo {response.status_code} en lugar de 404.",
        )

    # -----------------------------------------------------------------------
    # Caso 3: CashMovement de tenant_a no visible en tenant_b (ORM)
    # -----------------------------------------------------------------------

    def test_cash_movement_in_tenant_a_not_visible_in_tenant_b_orm(self):
        """CashMovement creado en esquema A no aparece en esquema B vía ORM."""
        # Crear booking y CashMovement en tenant_a
        start = datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc)
        booking_a = Booking.objects.create(
            court=self.court_a,
            user=self.admin_a,
            start_dt=start,
            end_dt=start.replace(hour=17),
            price="5000.00",
            status=Booking.Status.CONFIRMED,
        )
        CashMovement.objects.create(
            booking=booking_a,
            operator=self.admin_a,
            amount="5000.00",
            notes="Test aislamiento",
        )

        with schema_context(self.TENANT_B_SCHEMA):
            count_in_b = CashMovement.objects.filter(notes="Test aislamiento").count()

        self.assertEqual(
            count_in_b,
            0,
            f"FALLA: CashMovement de tenant_a visible en tenant_b ({count_in_b} movimientos).",
        )
