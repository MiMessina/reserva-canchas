"""
Tests de grilla multi-cancha del día — Feature 3

Cobertura:
  1.  test_daily_grid_requires_auth        — sin JWT → 401
  2.  test_daily_grid_requires_operator    — player → 403
  3.  test_daily_grid_returns_all_courts   — retorna todas las canchas activas
  4.  test_daily_grid_inactive_court_excluded — cancha inactiva no aparece
  5.  test_daily_grid_slot_structure       — cada slot tiene los campos requeridos
  6.  test_daily_grid_available_slot       — slot sin reserva → status=AVAILABLE
  7.  test_daily_grid_confirmed_slot       — slot con CONFIRMED → status=CONFIRMED + booking_id
  8.  test_daily_grid_pending_slot         — slot con PENDING_PAYMENT → status=PENDING_PAYMENT
  9.  test_daily_grid_cancelled_frees_slot — CANCELLED no ocupa el slot → AVAILABLE
  10. test_daily_grid_no_schedule_block    — cancha sin bloque → slots vacíos
  11. test_daily_grid_default_date         — sin ?date usa hoy en BA
  12. test_daily_grid_invalid_date         — ?date=bad → 400
  13. test_daily_grid_includes_guest_name  — booking con guest_name aparece en el slot
  14. test_daily_grid_user_name_fallback   — booking con user → usa nombre completo o email
  15. test_daily_grid_includes_past_slots  — admin ve slots ya pasados (no filtra)
"""

from datetime import datetime, timezone as tz

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestDailyGrid(TenantTestCase):
    """Tests del endpoint GET /api/bookings/daily-grid/."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="op@grid.test",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@grid.test",
            password="playerpass",
            role=User.Role.PLAYER,
        )

        self.operator_token = self._get_token("op@grid.test", "oppass123")

        # Cancha activa: lunes (2026-06-08 es lunes)
        self.court = Court.objects.create(
            name="Cancha Grid",
            court_type="futbol_5",
            surface="sintetico",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        # ScheduleBlock: lunes 11:00-14:00 → 3 slots de 60 min
        self.block = ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
            open_time="11:00",
            close_time="14:00",
        )
        # BA -3 hs UTC: 11:00 BA = 14:00 UTC
        # Slots esperados: 14:00-15:00, 15:00-16:00, 16:00-17:00 UTC

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló: {response.content}")
        return response.json()["access"]

    def _headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _get_grid(self, date="2026-06-08", token=None):
        headers = self._headers(token or self.operator_token)
        return self.client.get(
            f"/api/bookings/daily-grid/?date={date}",
            **headers,
        )

    # -----------------------------------------------------------------------
    # Caso 1: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_daily_grid_requires_auth(self):
        response = self.client.get("/api/bookings/daily-grid/?date=2026-06-08")
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 2: player → 403
    # -----------------------------------------------------------------------

    def test_daily_grid_requires_operator(self):
        player_token = self._get_token("player@grid.test", "playerpass")
        response = self._get_grid(token=player_token)
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 3: retorna todas las canchas activas
    # -----------------------------------------------------------------------

    def test_daily_grid_returns_all_courts(self):
        # Crear una segunda cancha activa
        Court.objects.create(
            name="Cancha Grid 2",
            court_type="padel",
            surface="",
            base_price="3000.00",
            slot_duration_minutes=60,
        )
        response = self._get_grid()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        court_names = [c["name"] for c in data["courts"]]
        self.assertIn("Cancha Grid", court_names)
        self.assertIn("Cancha Grid 2", court_names)

    # -----------------------------------------------------------------------
    # Caso 4: cancha inactiva no aparece
    # -----------------------------------------------------------------------

    def test_daily_grid_inactive_court_excluded(self):
        Court.objects.create(
            name="Cancha Inactiva Grid",
            court_type="padel",
            surface="",
            base_price="3000.00",
            slot_duration_minutes=60,
            is_active=False,
        )
        response = self._get_grid()
        data = response.json()
        court_names = [c["name"] for c in data["courts"]]
        self.assertNotIn("Cancha Inactiva Grid", court_names)

    # -----------------------------------------------------------------------
    # Caso 5: estructura de cada slot
    # -----------------------------------------------------------------------

    def test_daily_grid_slot_structure(self):
        response = self._get_grid()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")
        self.assertGreater(len(court_data["slots"]), 0)

        slot = court_data["slots"][0]
        required_keys = {"start_dt", "end_dt", "status", "booking_id", "guest_name", "price"}
        self.assertEqual(set(slot.keys()), required_keys)

    # -----------------------------------------------------------------------
    # Caso 6: slot sin reserva → status AVAILABLE
    # -----------------------------------------------------------------------

    def test_daily_grid_available_slot(self):
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")
        available_slots = [s for s in court_data["slots"] if s["status"] == "AVAILABLE"]
        self.assertEqual(len(available_slots), 3, "Deben ser 3 slots disponibles")
        for slot in available_slots:
            self.assertIsNone(slot["booking_id"])
            self.assertIsNone(slot["guest_name"])
            self.assertIsNone(slot["price"])

    # -----------------------------------------------------------------------
    # Caso 7: slot con CONFIRMED → status CONFIRMED + booking_id
    # -----------------------------------------------------------------------

    def test_daily_grid_confirmed_slot(self):
        # Reservar el primer slot: 14:00-15:00 UTC (= 11:00-12:00 BA)
        booking = Booking.objects.create(
            court=self.court,
            guest_name="Confirmado",
            guest_phone="111",
            start_dt=datetime(2026, 6, 8, 14, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 15, 0, tzinfo=tz.utc),
            status=Booking.Status.CONFIRMED,
            price="5000.00",
        )
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")

        slot_14 = next(
            (s for s in court_data["slots"] if "2026-06-08T14:00:00" in s["start_dt"]),
            None,
        )
        self.assertIsNotNone(slot_14, "No se encontró el slot de las 14:00 UTC")
        self.assertEqual(slot_14["status"], "CONFIRMED")
        self.assertEqual(slot_14["booking_id"], booking.pk)
        self.assertEqual(slot_14["guest_name"], "Confirmado")
        self.assertEqual(slot_14["price"], "5000.00")

    # -----------------------------------------------------------------------
    # Caso 8: slot con PENDING_PAYMENT → status PENDING_PAYMENT
    # -----------------------------------------------------------------------

    def test_daily_grid_pending_slot(self):
        Booking.objects.create(
            court=self.court,
            guest_name="Pendiente",
            guest_phone="222",
            start_dt=datetime(2026, 6, 8, 15, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 16, 0, tzinfo=tz.utc),
            status=Booking.Status.PENDING_PAYMENT,
            price="5000.00",
        )
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")

        slot_15 = next(
            (s for s in court_data["slots"] if "2026-06-08T15:00:00" in s["start_dt"]),
            None,
        )
        self.assertIsNotNone(slot_15)
        self.assertEqual(slot_15["status"], "PENDING_PAYMENT")

    # -----------------------------------------------------------------------
    # Caso 9: CANCELLED no ocupa el slot → AVAILABLE
    # -----------------------------------------------------------------------

    def test_daily_grid_cancelled_frees_slot(self):
        Booking.objects.create(
            court=self.court,
            guest_name="Cancelado",
            guest_phone="333",
            start_dt=datetime(2026, 6, 8, 16, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 17, 0, tzinfo=tz.utc),
            status=Booking.Status.CANCELLED,
            price="5000.00",
        )
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")

        slot_16 = next(
            (s for s in court_data["slots"] if "2026-06-08T16:00:00" in s["start_dt"]),
            None,
        )
        self.assertIsNotNone(slot_16)
        self.assertEqual(slot_16["status"], "AVAILABLE")

    # -----------------------------------------------------------------------
    # Caso 10: cancha sin bloque → slots vacíos
    # -----------------------------------------------------------------------

    def test_daily_grid_no_schedule_block(self):
        court_sin_bloque = Court.objects.create(
            name="Sin Bloque",
            court_type="padel",
            surface="",
            base_price="3000.00",
            slot_duration_minutes=60,
        )
        response = self._get_grid()
        data = response.json()
        court_data = next((c for c in data["courts"] if c["name"] == "Sin Bloque"), None)
        self.assertIsNotNone(court_data)
        self.assertEqual(court_data["slots"], [])

    # -----------------------------------------------------------------------
    # Caso 11: sin ?date usa hoy en BA (no falla)
    # -----------------------------------------------------------------------

    def test_daily_grid_default_date(self):
        response = self.client.get(
            "/api/bookings/daily-grid/",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertIn("date", data)
        self.assertIn("courts", data)

    # -----------------------------------------------------------------------
    # Caso 12: ?date inválida → 400
    # -----------------------------------------------------------------------

    def test_daily_grid_invalid_date(self):
        response = self.client.get(
            "/api/bookings/daily-grid/?date=not-a-date",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 13: booking con guest_name aparece en slot.guest_name
    # -----------------------------------------------------------------------

    def test_daily_grid_includes_guest_name(self):
        Booking.objects.create(
            court=self.court,
            guest_name="Juan Perez",
            guest_phone="444",
            start_dt=datetime(2026, 6, 8, 14, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 15, 0, tzinfo=tz.utc),
            status=Booking.Status.PENDING_PAYMENT,
            price="5000.00",
        )
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")
        slot = next(s for s in court_data["slots"] if "14:00:00" in s["start_dt"])
        self.assertEqual(slot["guest_name"], "Juan Perez")

    # -----------------------------------------------------------------------
    # Caso 14: booking con user registrado → usa nombre completo o email
    # -----------------------------------------------------------------------

    def test_daily_grid_user_name_fallback(self):
        user = User.objects.create_user(
            email="jugador@grid.test",
            password="pass",
            role=User.Role.PLAYER,
            first_name="Ana",
            last_name="Garcia",
        )
        Booking.objects.create(
            court=self.court,
            user=user,
            guest_name="",
            guest_phone="",
            start_dt=datetime(2026, 6, 8, 14, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 15, 0, tzinfo=tz.utc),
            status=Booking.Status.CONFIRMED,
            price="5000.00",
        )
        response = self._get_grid()
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")
        slot = next(s for s in court_data["slots"] if "14:00:00" in s["start_dt"])
        # Con first_name y last_name debe retornar el nombre completo
        self.assertEqual(slot["guest_name"], "Ana Garcia")

    # -----------------------------------------------------------------------
    # Caso 15: el admin ve slots pasados (no se filtran)
    # -----------------------------------------------------------------------

    def test_daily_grid_includes_past_slots(self):
        """get_daily_grid NO filtra slots pasados (a diferencia de get_availability).

        2026-06-08 es una fecha en el pasado relativo a la fecha actual del test
        (2026-06-08 < hoy: 2026-06-08). El admin debe ver todos los slots del día.
        """
        response = self._get_grid(date="2026-06-08")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        court_data = next(c for c in data["courts"] if c["name"] == "Cancha Grid")
        # Con bloque 11:00-14:00 BA (= 14:00-17:00 UTC) → 3 slots, todos pasados
        self.assertEqual(
            len(court_data["slots"]),
            3,
            "El admin debe ver los 3 slots aunque sean del pasado",
        )
