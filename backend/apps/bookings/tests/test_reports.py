"""
Tests del endpoint GET /api/bookings/weekly-report/ — reporte semanal.

Cobertura:
  1. test_weekly_report_requires_auth        — sin JWT → 401
  2. test_weekly_report_player_forbidden     — player → 403
  3. test_weekly_report_operator_ok          — operator → 200 con estructura esperada
  4. test_weekly_report_default_range        — sin parámetros → 200
  5. test_weekly_report_max_days_exceeded    — más de 31 días → 400
  6. test_weekly_report_invalid_date         — fecha inválida → 400
  7. test_weekly_report_date_order_reversed  — date_from > date_to → 400
  8. test_weekly_report_counts_bookings      — 2 bookings con estados distintos → conteos correctos
  9. test_weekly_report_revenue_from_cash    — CashMovement positivo → revenue_confirmed correcto
  10. test_weekly_report_by_court_occupancy  — occupancy_pct calculado correctamente

Patrón: TenantTestCase + TenantClient (mismo que el resto de tests de bookings).
"""

from datetime import datetime, timezone as tz
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User

# Rango de fechas fijo para tests: semana del 2027-01-04 (lunes) al 2027-01-10 (domingo)
TEST_DATE_FROM = "2027-01-04"
TEST_DATE_TO = "2027-01-10"

# Datetime dentro del rango: 2027-01-04 (lunes) 14:00 UTC = 11:00 BA
SLOT_START = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
SLOT_END = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)


class TestWeeklyReport(TenantTestCase):
    """Tests del endpoint GET /api/bookings/weekly-report/."""

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

        # Cancha activa
        self.court = Court.objects.create(
            name="Cancha Report Test",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        # ScheduleBlock lunes 08:00-22:00
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
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

    def _get_report(self, date_from=None, date_to=None, token=None):
        """GET /api/bookings/weekly-report/ con parámetros opcionales."""
        params = []
        if date_from:
            params.append(f"date_from={date_from}")
        if date_to:
            params.append(f"date_to={date_to}")
        url = "/api/bookings/weekly-report/"
        if params:
            url = f"{url}?{'&'.join(params)}"
        headers = self._auth_headers(token) if token else {}
        return self.client.get(url, **headers)

    def _make_booking(self, start_dt=SLOT_START, end_dt=SLOT_END,
                      status=Booking.Status.PENDING_PAYMENT, court=None):
        """Crea una reserva de invitado con el estado indicado."""
        return Booking.objects.create(
            court=court or self.court,
            guest_name="Jugador Test",
            guest_phone="1122334455",
            start_dt=start_dt,
            end_dt=end_dt,
            status=status,
            price=Decimal("5000.00"),
        )

    def _make_cash_movement(self, booking, amount, created_at=None):
        """Crea un CashMovement, forzando created_at si se indica."""
        if created_at is None:
            # Dentro del rango de test: 2027-01-04 17:00 UTC = 14:00 BA
            created_at = datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc)
        movement = CashMovement(
            booking=booking,
            operator=self.operator,
            amount=amount,
            notes="Test movement",
        )
        movement.save()
        CashMovement.objects.filter(pk=movement.pk).update(created_at=created_at)
        return CashMovement.objects.get(pk=movement.pk)

    # -----------------------------------------------------------------------
    # Caso 1: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_weekly_report_requires_auth(self):
        """GET /api/bookings/weekly-report/ sin JWT → 401 Unauthorized."""
        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=None
        )
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 2: player → 403
    # -----------------------------------------------------------------------

    def test_weekly_report_player_forbidden(self):
        """GET con JWT de player → 403 Forbidden."""
        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.player_token
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 3: operator → 200 con estructura esperada
    # -----------------------------------------------------------------------

    def test_weekly_report_operator_ok(self):
        """GET con JWT de operator y rango válido → 200 con todos los campos del contrato."""
        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.operator_token
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        # Campos raíz del contrato
        self.assertIn("date_from", data)
        self.assertIn("date_to", data)
        self.assertIn("totals", data)
        self.assertIn("by_day", data)
        self.assertIn("by_court", data)

        self.assertEqual(data["date_from"], TEST_DATE_FROM)
        self.assertEqual(data["date_to"], TEST_DATE_TO)

        # Estructura de totals
        totals = data["totals"]
        for field in ("bookings_total", "confirmed", "cancelled", "completed",
                      "pending_payment", "revenue_confirmed"):
            self.assertIn(field, totals, f"Falta campo totals.{field}")

        # by_day tiene un elemento por cada día del rango (7 días: 04 al 10 enero)
        self.assertEqual(len(data["by_day"]), 7, f"Se esperaban 7 días, hay {len(data['by_day'])}")

        # Estructura de cada elemento de by_day
        for day_item in data["by_day"]:
            for field in ("date", "bookings_total", "confirmed", "cancelled",
                          "completed", "pending_payment", "revenue_confirmed"):
                self.assertIn(field, day_item, f"Falta campo by_day[].{field}")

        # by_court tiene al menos 1 elemento (la cancha creada en setUp)
        self.assertGreaterEqual(len(data["by_court"]), 1)

        # Estructura de cada elemento de by_court
        for court_item in data["by_court"]:
            for field in ("court_id", "court_name", "court_type", "bookings_total",
                          "confirmed_or_completed", "occupancy_pct", "revenue_confirmed"):
                self.assertIn(field, court_item, f"Falta campo by_court[].{field}")

    # -----------------------------------------------------------------------
    # Caso 4: sin parámetros → 200 (usa semana actual, no falla)
    # -----------------------------------------------------------------------

    def test_weekly_report_default_range(self):
        """GET sin parámetros date_from/date_to → 200 con semana actual."""
        response = self._get_report(token=self.operator_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        # Debe tener date_from y date_to con fechas válidas YYYY-MM-DD
        self.assertIn("date_from", data)
        self.assertIn("date_to", data)
        # by_day debe tener 7 elementos (lunes a domingo de la semana actual)
        self.assertEqual(len(data["by_day"]), 7)

    # -----------------------------------------------------------------------
    # Caso 5: más de 31 días → 400
    # -----------------------------------------------------------------------

    def test_weekly_report_max_days_exceeded(self):
        """date_to - date_from > 31 días → 400 VALIDATION_ERROR."""
        response = self._get_report(
            date_from="2027-01-01", date_to="2027-02-15", token=self.operator_token
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("31", data["error"]["message"])

    # -----------------------------------------------------------------------
    # Caso 6: fecha inválida → 400
    # -----------------------------------------------------------------------

    def test_weekly_report_invalid_date(self):
        """date_from con formato inválido → 400 VALIDATION_ERROR."""
        response = self._get_report(
            date_from="not-a-date", date_to=TEST_DATE_TO, token=self.operator_token
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 7: date_from > date_to → 400
    # -----------------------------------------------------------------------

    def test_weekly_report_date_order_reversed(self):
        """date_from posterior a date_to → 400 VALIDATION_ERROR."""
        response = self._get_report(
            date_from="2027-01-10", date_to="2027-01-04", token=self.operator_token
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 8: conteos de bookings correctos
    # -----------------------------------------------------------------------

    def test_weekly_report_counts_bookings(self):
        """
        2 bookings en el rango: uno CONFIRMED, uno CANCELLED.
        totals.bookings_total == 2, confirmed == 1, cancelled == 1.
        El día correspondiente (2027-01-04) tiene bookings_total == 2.
        """
        # Usar slots distintos para no solapar (no usa select_for_update; creación directa en DB)
        start_a = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        end_a = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)
        start_b = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)
        end_b = datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc)

        self._make_booking(start_dt=start_a, end_dt=end_a, status=Booking.Status.CONFIRMED)
        self._make_booking(start_dt=start_b, end_dt=end_b, status=Booking.Status.CANCELLED)

        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.operator_token
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        totals = data["totals"]
        self.assertEqual(totals["bookings_total"], 2)
        self.assertEqual(totals["confirmed"], 1)
        self.assertEqual(totals["cancelled"], 1)
        self.assertEqual(totals["completed"], 0)
        self.assertEqual(totals["pending_payment"], 0)

        # El día 2027-01-04 debe tener 2 reservas
        day_04 = next((d for d in data["by_day"] if d["date"] == "2027-01-04"), None)
        self.assertIsNotNone(day_04, "El día 2027-01-04 no está en by_day")
        self.assertEqual(day_04["bookings_total"], 2)
        self.assertEqual(day_04["confirmed"], 1)
        self.assertEqual(day_04["cancelled"], 1)

    # -----------------------------------------------------------------------
    # Caso 9: revenue_confirmed desde CashMovement
    # -----------------------------------------------------------------------

    def test_weekly_report_revenue_from_cash(self):
        """
        1 CashMovement positivo de $5000 en el rango →
        totals.revenue_confirmed == "5000.00".
        Un movimiento negativo (-$2500) no suma al revenue_confirmed.
        """
        booking = self._make_booking(status=Booking.Status.CONFIRMED)
        # Movimiento positivo (ingreso)
        self._make_cash_movement(
            booking, amount=Decimal("5000.00"),
            created_at=datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc)
        )
        # Movimiento negativo (devolución) — no debe sumar a revenue_confirmed
        self._make_cash_movement(
            booking, amount=Decimal("-2500.00"),
            created_at=datetime(2027, 1, 4, 18, 0, tzinfo=tz.utc)
        )

        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.operator_token
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        # revenue_confirmed solo suma los positivos
        self.assertEqual(
            Decimal(data["totals"]["revenue_confirmed"]), Decimal("5000.00"),
            "revenue_confirmed debe ser solo la suma de movimientos positivos"
        )

        # El día 2027-01-04 también debe tener revenue_confirmed == 5000
        day_04 = next((d for d in data["by_day"] if d["date"] == "2027-01-04"), None)
        self.assertIsNotNone(day_04)
        self.assertEqual(
            Decimal(day_04["revenue_confirmed"]), Decimal("5000.00")
        )

    # -----------------------------------------------------------------------
    # Caso 10: occupancy_pct calculado correctamente en by_court
    # -----------------------------------------------------------------------

    def test_weekly_report_by_court_occupancy(self):
        """
        4 bookings para la cancha del setUp: 3 CONFIRMED/COMPLETED + 1 PENDING_PAYMENT.
        occupancy_pct = 3 / 4 * 100 = 75.0.
        """
        starts = [
            (datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc), datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc), Booking.Status.CONFIRMED),
            (datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc), datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc), Booking.Status.COMPLETED),
            (datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc), datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc), Booking.Status.CONFIRMED),
            (datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc), datetime(2027, 1, 4, 18, 0, tzinfo=tz.utc), Booking.Status.PENDING_PAYMENT),
        ]
        for s, e, st in starts:
            self._make_booking(start_dt=s, end_dt=e, status=st)

        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.operator_token
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        court_data = next(
            (c for c in data["by_court"] if c["court_id"] == self.court.pk), None
        )
        self.assertIsNotNone(court_data, "La cancha del setUp no aparece en by_court")
        self.assertEqual(court_data["bookings_total"], 4)
        self.assertEqual(court_data["confirmed_or_completed"], 3)
        self.assertAlmostEqual(court_data["occupancy_pct"], 75.0, places=1)

    # -----------------------------------------------------------------------
    # Caso extra: admin también puede acceder
    # -----------------------------------------------------------------------

    def test_weekly_report_admin_ok(self):
        """GET con JWT de admin → 200."""
        response = self._get_report(
            date_from=TEST_DATE_FROM, date_to=TEST_DATE_TO, token=self.admin_token
        )
        self.assertEqual(response.status_code, 200, response.content)

    # -----------------------------------------------------------------------
    # Caso extra: rango de exactamente 31 días es válido
    # -----------------------------------------------------------------------

    def test_weekly_report_exactly_31_days_ok(self):
        """Rango de exactamente 31 días → 200 (no supera el límite)."""
        response = self._get_report(
            date_from="2027-01-01", date_to="2027-01-31", token=self.operator_token
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(len(data["by_day"]), 31)

    # -----------------------------------------------------------------------
    # Caso extra: rango de 32 días es rechazado
    # -----------------------------------------------------------------------

    def test_weekly_report_32_days_rejected(self):
        """Rango de 32 días → 400 (supera el límite de 31)."""
        response = self._get_report(
            date_from="2027-01-01", date_to="2027-02-01", token=self.operator_token
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
