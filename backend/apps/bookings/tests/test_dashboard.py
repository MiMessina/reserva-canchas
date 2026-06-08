"""
Tests del endpoint GET /api/dashboard/ — resumen del día para el panel de inicio.

Cobertura:
  1. test_dashboard_returns_200_for_operator    — operador autenticado → 200 con campos correctos.
  2. test_dashboard_returns_401_unauthenticated — sin JWT → 401.
  3. test_dashboard_returns_403_for_player      — jugador → 403.
  4. test_dashboard_counts_bookings_today       — 1 booking PENDING_PAYMENT hoy → pending_payment == 1.
  5. test_dashboard_courts_total                — courts_total == canchas activas del tenant.

Patrón: TenantTestCase + TenantClient (mismo que el resto de tests de bookings).
"""

from datetime import datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestDashboard(TenantTestCase):
    """Tests del endpoint GET /api/dashboard/."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Usuarios
        self.operator = User.objects.create_user(
            email="operator@test.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.player = User.objects.create_user(
            email="player@test.localhost",
            password="playerpass123",
            role=User.Role.PLAYER,
        )

        # Tokens JWT
        self.operator_token = self._get_token("operator@test.localhost", "oppass123")
        self.admin_token = self._get_token("admin@test.localhost", "adminpass123")
        self.player_token = self._get_token("player@test.localhost", "playerpass123")

        # Cancha activa base
        self.court = Court.objects.create(
            name="Cancha Dashboard Test",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        # ScheduleBlock lunes 08:00–22:00 (weekday=0)
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,
            open_time="08:00",
            close_time="22:00",
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(
            response.status_code, 200,
            f"Login falló para {email}: {response.content}",
        )
        return response.json()["access"]

    def _auth_headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _get_dashboard(self, token=None):
        headers = self._auth_headers(token) if token else {}
        return self.client.get("/api/dashboard/", **headers)

    def _make_booking(self, start_dt, status=Booking.Status.PENDING_PAYMENT):
        """Crea una reserva de invitado con el estado indicado."""
        end_dt = datetime(
            start_dt.year, start_dt.month, start_dt.day,
            start_dt.hour + 1, start_dt.minute,
            tzinfo=start_dt.tzinfo,
        )
        return Booking.objects.create(
            court=self.court,
            guest_name="Jugador Test",
            guest_phone="1122334455",
            start_dt=start_dt,
            end_dt=end_dt,
            status=status,
            price=Decimal("5000.00"),
        )

    # -----------------------------------------------------------------------
    # Caso 1: operador autenticado → 200 con todos los campos del contrato
    # -----------------------------------------------------------------------

    def test_dashboard_returns_200_for_operator(self):
        """GET /api/dashboard/ con token de operator → 200 con estructura correcta."""
        response = self._get_dashboard(token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        # Verificar presencia de todos los campos del contrato
        self.assertIn("bookings_today", data)
        self.assertIn("courts_total", data)
        self.assertIn("courts_occupied_now", data)
        self.assertIn("cashbox_today", data)

        # bookings_today tiene todos los subcampos
        bt = data["bookings_today"]
        for field in ("pending_payment", "confirmed", "completed", "cancelled", "total"):
            self.assertIn(field, bt, f"Falta campo bookings_today.{field}")

        # cashbox_today tiene los mismos campos que /api/cash-movements/summary/
        ct = data["cashbox_today"]
        for field in ("date", "total", "ingresos", "devoluciones",
                      "movements_count", "ingresos_count", "devoluciones_count"):
            self.assertIn(field, ct, f"Falta campo cashbox_today.{field}")

        # Tipo correcto de los campos numéricos
        self.assertIsInstance(data["courts_total"], int)
        self.assertIsInstance(data["courts_occupied_now"], int)

    # -----------------------------------------------------------------------
    # Caso 2: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_dashboard_returns_401_unauthenticated(self):
        """GET /api/dashboard/ sin JWT → 401 Unauthorized."""
        response = self._get_dashboard(token=None)
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 3: jugador → 403
    # -----------------------------------------------------------------------

    def test_dashboard_returns_403_for_player(self):
        """GET /api/dashboard/ con JWT de player → 403 Forbidden."""
        response = self._get_dashboard(token=self.player_token)
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 4: booking de hoy en PENDING_PAYMENT aparece en el conteo
    # -----------------------------------------------------------------------

    def test_dashboard_counts_bookings_today(self):
        """
        1 booking en PENDING_PAYMENT cuyo start_dt es hoy (en UTC) →
        bookings_today.pending_payment == 1, total == 1.

        Se parchea datetime.now en el selector para que "hoy" coincida
        con el start_dt de la reserva creada (2027-01-04, lunes, 14:00 UTC).
        Usamos patch de la función now() directamente para no romper el resto
        de la clase datetime que usa el ORM.
        """
        # Lunes 2027-01-04 14:00 UTC = 11:00 BA → dentro del bloque 08:00-22:00
        booking_start = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        self._make_booking(start_dt=booking_start, status=Booking.Status.PENDING_PAYMENT)

        # Parchear datetime.now en el selector para que "hoy" = 2027-01-04 15:00 UTC
        # (dentro del mismo día BA que el booking, después de su start_dt)
        fake_now = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)

        with patch("apps.bookings.selectors.datetime") as mock_dt:
            # now() retorna el instante falso; todo lo demás se delega al original
            mock_dt.now.return_value = fake_now
            mock_dt.combine = datetime.combine
            mock_dt.fromisoformat = datetime.fromisoformat
            # Los argumentos de los filtros son datetime reales (construidos en el selector
            # a partir de fake_now.astimezone(BUENOS_AIRES).date()); los pasamos
            # tal cual porque son instancias de datetime, no del mock.
            # El truco es que el selector construye day_start_ba / day_end_ba usando
            # el constructor de datetime directamente, no via mock_dt(). Por eso el
            # patch no interfiere con los valores pasados al ORM.
            # Sin embargo, la clase datetime es reemplazada en el namespace del módulo,
            # entonces `datetime(year, month, ...)` dentro del selector llama a mock_dt().
            # Para evitar eso, delegamos también el constructor:
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            response = self._get_dashboard(token=self.operator_token)

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        bt = data["bookings_today"]
        self.assertEqual(bt["pending_payment"], 1, "Debe haber 1 booking PENDING_PAYMENT hoy")
        self.assertEqual(bt["total"], 1, "Total de bookings hoy debe ser 1")
        self.assertEqual(bt["confirmed"], 0)
        self.assertEqual(bt["completed"], 0)
        self.assertEqual(bt["cancelled"], 0)

    # -----------------------------------------------------------------------
    # Caso 5: courts_total == canchas activas del tenant
    # -----------------------------------------------------------------------

    def test_dashboard_courts_total(self):
        """
        courts_total debe ser igual a la cantidad de Court activas del tenant.
        Se crea una segunda cancha activa y una inactiva; solo las activas cuentan.
        """
        # Cancha activa adicional
        Court.objects.create(
            name="Segunda Cancha",
            court_type="padel",
            surface="cesped",
            base_price="3000.00",
            slot_duration_minutes=90,
            is_active=True,
        )
        # Cancha inactiva (no debe contar)
        Court.objects.create(
            name="Cancha Inactiva",
            court_type="futbol_5",
            surface="cemento",
            base_price="2000.00",
            slot_duration_minutes=60,
            is_active=False,
        )

        response = self._get_dashboard(token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        # setUp crea 1 cancha activa; aquí sumamos 1 activa + 1 inactiva → 2 activas total
        active_count = Court.objects.filter(is_active=True).count()
        self.assertEqual(data["courts_total"], active_count)
        self.assertGreaterEqual(data["courts_total"], 2)
