"""
Tests del endpoint GET /api/cash-movements/summary/ — resumen diario de caja.

Cobertura:
  1. test_summary_empty_day           — sin movimientos → todos los totales = 0.
  2. test_summary_with_ingresos       — movimiento positivo → total == ingresos, count == 1.
  3. test_summary_with_devolucion     — movimiento negativo → devoluciones < 0, neto correcto.
  4. test_summary_requires_auth       — sin JWT → 401.
  5. test_summary_requires_operator   — player → 403.
  6. test_summary_default_date        — sin ?date → usa hoy en BA (no falla).
  7. test_summary_invalid_date        — ?date=invalido → 400 VALIDATION_ERROR.

Patrón: TenantTestCase + TenantClient (mismo que el resto de tests de Sprint 2).
"""

from datetime import datetime, timezone as tz
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestCashDailySummary(TenantTestCase):
    """Tests del endpoint GET /api/cash-movements/summary/."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Usuarios
        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@test.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@test.localhost",
            password="playerpass123",
            role=User.Role.PLAYER,
        )

        # Tokens JWT
        self.operator_token = self._get_token("operator@test.localhost", "oppass123")
        self.player_token = self._get_token("player@test.localhost", "playerpass123")

        # Cancha y bloque horario base
        self.court = Court.objects.create(
            name="Cancha Summary Test",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        self.block = ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
            open_time="08:00",
            close_time="22:00",
        )

        # Turno futuro base para crear bookings (lunes 2027-01-04 14:00 UTC)
        self.valid_start = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        self.valid_end = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)

        # Fecha de test (coincide con el día de valid_start en BA: 2027-01-04)
        self.test_date = "2027-01-04"

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló para {email}: {response.content}")
        return response.json()["access"]

    def _auth_headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _get_summary(self, date_str=None, token=None):
        """GET /api/cash-movements/summary/ con fecha y token opcionales."""
        url = "/api/cash-movements/summary/"
        if date_str:
            url = f"{url}?date={date_str}"
        headers = self._auth_headers(token) if token else {}
        return self.client.get(url, **headers)

    def _make_booking(self, status=Booking.Status.CONFIRMED):
        """Crea una reserva en el estado indicado."""
        booking = Booking.objects.create(
            court=self.court,
            guest_name="Jugador Test",
            guest_phone="1122334455",
            start_dt=self.valid_start,
            end_dt=self.valid_end,
            status=status,
            price=Decimal("5000.00"),
        )
        return booking

    def _make_cash_movement(self, booking, amount, created_at=None):
        """Crea un CashMovement con el monto indicado."""
        # created_at por defecto: dentro del día de test (2027-01-04 UTC)
        if created_at is None:
            # 17:00 UTC = 14:00 BA el 2027-01-04, dentro del rango del test
            created_at = datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc)

        movement = CashMovement(
            booking=booking,
            operator=self.operator,
            amount=amount,
            notes="Test movement",
        )
        movement.save()
        # Forzar created_at ya que auto_now_add no se puede pasar en create()
        CashMovement.objects.filter(pk=movement.pk).update(created_at=created_at)
        return CashMovement.objects.get(pk=movement.pk)

    # -----------------------------------------------------------------------
    # Caso 1: día sin movimientos — todos los totales = 0
    # -----------------------------------------------------------------------

    def test_summary_empty_day(self):
        """Sin movimientos para la fecha → todos los totales = 0, counts = 0."""
        response = self._get_summary(date_str=self.test_date, token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(data["date"], self.test_date)
        self.assertEqual(Decimal(data["total"]), Decimal("0"))
        self.assertEqual(Decimal(data["ingresos"]), Decimal("0"))
        self.assertEqual(Decimal(data["devoluciones"]), Decimal("0"))
        self.assertEqual(data["movements_count"], 0)
        self.assertEqual(data["ingresos_count"], 0)
        self.assertEqual(data["devoluciones_count"], 0)

    # -----------------------------------------------------------------------
    # Caso 2: un movimiento positivo (ingreso por seña confirmada)
    # -----------------------------------------------------------------------

    def test_summary_with_ingresos(self):
        """Un CashMovement positivo: total == ingresos, movements_count == 1."""
        booking = self._make_booking()
        self._make_cash_movement(booking, amount=Decimal("5000.00"))

        response = self._get_summary(date_str=self.test_date, token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(Decimal(data["total"]), Decimal("5000.00"))
        self.assertEqual(Decimal(data["ingresos"]), Decimal("5000.00"))
        self.assertEqual(Decimal(data["devoluciones"]), Decimal("0"))
        self.assertEqual(data["movements_count"], 1)
        self.assertEqual(data["ingresos_count"], 1)
        self.assertEqual(data["devoluciones_count"], 0)

    # -----------------------------------------------------------------------
    # Caso 3: movimiento negativo (devolución por cancelación)
    # -----------------------------------------------------------------------

    def test_summary_with_devolucion(self):
        """Un movimiento negativo: devoluciones < 0, neto es la suma correcta."""
        booking = self._make_booking()
        self._make_cash_movement(booking, amount=Decimal("5000.00"))
        self._make_cash_movement(booking, amount=Decimal("-2500.00"))

        response = self._get_summary(date_str=self.test_date, token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(Decimal(data["total"]), Decimal("2500.00"))
        self.assertEqual(Decimal(data["ingresos"]), Decimal("5000.00"))
        self.assertEqual(Decimal(data["devoluciones"]), Decimal("-2500.00"))
        self.assertEqual(data["movements_count"], 2)
        self.assertEqual(data["ingresos_count"], 1)
        self.assertEqual(data["devoluciones_count"], 1)

    # -----------------------------------------------------------------------
    # Caso 4: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_summary_requires_auth(self):
        """GET sin JWT → 401 Unauthorized."""
        response = self._get_summary(date_str=self.test_date, token=None)
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 5: player → 403
    # -----------------------------------------------------------------------

    def test_summary_requires_operator_role(self):
        """GET con JWT de player → 403 Forbidden."""
        response = self._get_summary(date_str=self.test_date, token=self.player_token)
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 6: sin ?date → usa hoy en BA (no falla, retorna 200)
    # -----------------------------------------------------------------------

    def test_summary_default_date(self):
        """Sin parámetro date → default a hoy en BA → 200 con totales (vacíos o no)."""
        response = self._get_summary(date_str=None, token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        # Debe incluir el campo date (hoy en BA, no chequeamos el valor exacto)
        self.assertIn("date", data)
        self.assertIn("total", data)
        self.assertIn("movements_count", data)

    # -----------------------------------------------------------------------
    # Caso 7: ?date=invalido → 400 VALIDATION_ERROR
    # -----------------------------------------------------------------------

    def test_summary_invalid_date(self):
        """?date con formato inválido → 400 con código VALIDATION_ERROR."""
        response = self._get_summary(date_str="invalido", token=self.operator_token)
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
