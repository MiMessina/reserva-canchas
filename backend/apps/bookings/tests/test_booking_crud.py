"""
Tests CRUD del motor de reservas — Sprint 2

Cobertura:
  1.  test_guest_can_create_booking       — POST sin JWT con guest → 201 PENDING_PAYMENT
  2.  test_player_can_create_booking      — POST con JWT de player (sin guest) → 201
  3.  test_cannot_create_booking_in_past  — start_dt en pasado → 400 BOOKING_IN_PAST
  4.  test_cannot_create_outside_schedule — hora fuera de bloque → 400 OUTSIDE_SCHEDULE
  5.  test_cannot_book_inactive_court     — cancha inactiva → 400 COURT_INACTIVE
  6.  test_sequential_overbooking_rejected — dos POSTs seguidos al mismo slot → 201 + 400
  7.  test_operator_can_confirm_booking   — POST .../confirm/ → 200 + CashMovement creado
  8.  test_player_cannot_confirm_booking  — POST .../confirm/ como player → 403
  9.  test_cancel_pending_booking         — POST .../cancel/ → 200 CANCELLED
  10. test_cannot_cancel_completed_booking — INVALID_TRANSITION
  11. test_complete_confirmed_booking     — mock de now() → 200 COMPLETED
  12. test_availability_returns_slots     — GET /api/courts/{id}/availability/ → slots

Patrón: TenantTestCase + TenantClient (mismo que Sprint 1).
"""

from datetime import datetime, timezone as tz
from unittest.mock import patch

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestBookingCRUD(TenantTestCase):
    """Tests de operaciones sobre Booking."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Usuarios con distintos roles
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
        self.admin_token = self._get_token("admin@test.localhost", "adminpass123")
        self.operator_token = self._get_token("operator@test.localhost", "oppass123")
        self.player_token = self._get_token("player@test.localhost", "playerpass123")

        # Cancha activa con slot de 60 minutos
        self.court = Court.objects.create(
            name="Cancha Test",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )

        # ScheduleBlock: lunes (0) 08:00-22:00
        self.block = ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
            open_time="08:00",
            close_time="22:00",
        )

        # Datetime futuro para tests: lunes 2027-01-04 14:00 UTC
        # (2027-01-04 es lunes; en Buenos Aires = 11:00, dentro del bloque)
        self.valid_start = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)

    def _get_token(self, email, password):
        """Obtiene JWT access token."""
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló para {email}: {response.content}")
        return response.json()["access"]

    def _headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _post_booking(self, data, token=None):
        """Helper: crea una reserva vía POST /api/bookings/."""
        headers = self._headers(token) if token else {}
        return self.client.post(
            "/api/bookings/",
            data,
            content_type="application/json",
            **headers,
        )

    # -----------------------------------------------------------------------
    # Caso 1: invitado puede crear reserva sin JWT
    # -----------------------------------------------------------------------

    def test_guest_can_create_booking(self):
        """POST /api/bookings/ sin JWT con guest_name+phone → 201 PENDING_PAYMENT."""
        response = self._post_booking({
            "court": self.court.pk,
            "start_dt": self.valid_start.isoformat(),
            "guest_name": "Juan Jugador",
            "guest_phone": "1122334455",
        })
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["status"], "PENDING_PAYMENT")
        self.assertEqual(data["guest_name"], "Juan Jugador")
        self.assertIsNone(data["user"])
        self.assertEqual(data["price"], "5000.00")

    # -----------------------------------------------------------------------
    # Caso 2: player autenticado puede crear reserva sin guest_*
    # -----------------------------------------------------------------------

    def test_player_can_create_booking(self):
        """POST /api/bookings/ con JWT de player (sin guest) → 201 PENDING_PAYMENT."""
        # Usar un slot diferente para no solapar con otros tests
        start = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)
        response = self._post_booking(
            {
                "court": self.court.pk,
                "start_dt": start.isoformat(),
            },
            token=self.player_token,
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["status"], "PENDING_PAYMENT")
        self.assertEqual(data["user"], self.player.pk)
        self.assertEqual(data["guest_name"], "")

    # -----------------------------------------------------------------------
    # Caso 3: no se puede reservar en el pasado
    # -----------------------------------------------------------------------

    def test_cannot_create_booking_in_past(self):
        """POST con start_dt en el pasado → 400 BOOKING_IN_PAST."""
        past_dt = datetime(2020, 1, 6, 14, 0, tzinfo=tz.utc)
        response = self._post_booking({
            "court": self.court.pk,
            "start_dt": past_dt.isoformat(),
            "guest_name": "Pepe",
            "guest_phone": "111",
        })
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "BOOKING_IN_PAST")

    # -----------------------------------------------------------------------
    # Caso 4: no se puede reservar fuera del ScheduleBlock
    # -----------------------------------------------------------------------

    def test_cannot_create_booking_outside_schedule(self):
        """POST con start_dt fuera del bloque horario → 400 OUTSIDE_SCHEDULE."""
        # 2027-01-04 lunes; 06:00 UTC = 03:00 BA — fuera del bloque 08:00-22:00 BA
        outside_start = datetime(2027, 1, 4, 6, 0, tzinfo=tz.utc)
        response = self._post_booking({
            "court": self.court.pk,
            "start_dt": outside_start.isoformat(),
            "guest_name": "Ana",
            "guest_phone": "222",
        })
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "OUTSIDE_SCHEDULE")

    # -----------------------------------------------------------------------
    # Caso 5: cancha inactiva es rechazada
    # -----------------------------------------------------------------------

    def test_cannot_book_inactive_court(self):
        """POST con cancha inactiva → 400 COURT_INACTIVE."""
        inactive_court = Court.objects.create(
            name="Cancha Inactiva",
            court_type="padel",
            surface="",
            base_price="3000.00",
            slot_duration_minutes=60,
            is_active=False,
        )
        response = self._post_booking({
            "court": inactive_court.pk,
            "start_dt": self.valid_start.isoformat(),
            "guest_name": "Carlos",
            "guest_phone": "333",
        })
        # El serializer rechaza la cancha inactiva antes del service
        # (PrimaryKeyRelatedField filtra is_active=True)
        self.assertEqual(response.status_code, 400, response.content)

    # -----------------------------------------------------------------------
    # Caso 6: overbooking secuencial rechazado
    # -----------------------------------------------------------------------

    def test_sequential_overbooking_rejected(self):
        """Dos POSTs al mismo slot → primero 201, segundo 400 SLOT_ALREADY_BOOKED."""
        slot = datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc)
        payload = {
            "court": self.court.pk,
            "start_dt": slot.isoformat(),
            "guest_name": "Primero",
            "guest_phone": "444",
        }

        response1 = self._post_booking(payload)
        self.assertEqual(response1.status_code, 201, response1.content)

        payload["guest_name"] = "Segundo"
        response2 = self._post_booking(payload)
        self.assertEqual(response2.status_code, 400, response2.content)
        data2 = response2.json()
        self.assertEqual(data2["error"]["code"], "SLOT_ALREADY_BOOKED")

    # -----------------------------------------------------------------------
    # Caso 7: operator puede confirmar una reserva
    # -----------------------------------------------------------------------

    def test_operator_can_confirm_booking(self):
        """POST .../confirm/ como operator → 200 CONFIRMED + CashMovement creado."""
        # Crear reserva primero
        slot = datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc)
        create_resp = self._post_booking({
            "court": self.court.pk,
            "start_dt": slot.isoformat(),
            "guest_name": "Confirmable",
            "guest_phone": "555",
        })
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        # Confirmar como operator
        confirm_resp = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(confirm_resp.status_code, 200, confirm_resp.content)
        self.assertEqual(confirm_resp.json()["status"], "CONFIRMED")

        # Verificar CashMovement creado
        movement_count = CashMovement.objects.filter(booking_id=booking_id).count()
        self.assertEqual(movement_count, 1, "Se esperaba 1 CashMovement tras confirmar.")

    # -----------------------------------------------------------------------
    # Caso 8: player no puede confirmar una reserva
    # -----------------------------------------------------------------------

    def test_player_cannot_confirm_booking(self):
        """POST .../confirm/ como player → 403."""
        slot = datetime(2027, 1, 4, 18, 0, tzinfo=tz.utc)
        create_resp = self._post_booking({
            "court": self.court.pk,
            "start_dt": slot.isoformat(),
            "guest_name": "Noconfirmable",
            "guest_phone": "666",
        })
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 9: cancelar una reserva pendiente
    # -----------------------------------------------------------------------

    def test_cancel_pending_booking(self):
        """POST .../cancel/ → 200 CANCELLED."""
        slot = datetime(2027, 1, 4, 19, 0, tzinfo=tz.utc)
        create_resp = self._post_booking({
            "court": self.court.pk,
            "start_dt": slot.isoformat(),
            "guest_name": "Cancelable",
            "guest_phone": "777",
        })
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        cancel_resp = self.client.post(
            f"/api/bookings/{booking_id}/cancel/",
            {"reason": "El jugador no pudo asistir."},
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.content)
        self.assertEqual(cancel_resp.json()["status"], "CANCELLED")
        self.assertIn("El jugador no pudo asistir", cancel_resp.json()["cancellation_reason"])

    # -----------------------------------------------------------------------
    # Caso 10: no se puede cancelar una reserva COMPLETED
    # -----------------------------------------------------------------------

    def test_cannot_cancel_completed_booking(self):
        """POST .../cancel/ sobre COMPLETED → 400 INVALID_TRANSITION."""
        # Crear reserva directamente en DB con status COMPLETED para el test
        slot = datetime(2027, 1, 4, 20, 0, tzinfo=tz.utc)
        booking = Booking.objects.create(
            court=self.court,
            guest_name="Completado",
            guest_phone="888",
            start_dt=slot,
            end_dt=slot.replace(hour=21),
            price="5000.00",
            status=Booking.Status.COMPLETED,
        )

        cancel_resp = self.client.post(
            f"/api/bookings/{booking.pk}/cancel/",
            {"reason": "Intentar cancelar completada"},
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(cancel_resp.status_code, 400, cancel_resp.content)
        self.assertEqual(cancel_resp.json()["error"]["code"], "INVALID_TRANSITION")

    # -----------------------------------------------------------------------
    # Caso 11: completar una reserva confirmada cuyo end_dt ya pasó
    # -----------------------------------------------------------------------

    def test_complete_confirmed_booking(self):
        """POST .../complete/ con end_dt en el pasado (mock) → 200 COMPLETED."""
        # Crear reserva en estado CONFIRMED directamente
        past_start = datetime(2026, 1, 5, 14, 0, tzinfo=tz.utc)
        past_end = datetime(2026, 1, 5, 15, 0, tzinfo=tz.utc)
        booking = Booking.objects.create(
            court=self.court,
            user=self.operator,
            start_dt=past_start,
            end_dt=past_end,
            price="5000.00",
            status=Booking.Status.CONFIRMED,
        )

        # end_dt es en el pasado, complete_booking debe funcionar sin mock
        complete_resp = self.client.post(
            f"/api/bookings/{booking.pk}/complete/",
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(complete_resp.status_code, 200, complete_resp.content)
        self.assertEqual(complete_resp.json()["status"], "COMPLETED")

    # -----------------------------------------------------------------------
    # Caso 12: grilla de disponibilidad retorna slots
    # -----------------------------------------------------------------------

    def test_availability_returns_slots(self):
        """GET /api/courts/{id}/availability/?date=... → lista de slots con is_available."""
        # 2027-01-04 es lunes (weekday=0), tiene ScheduleBlock 08:00-22:00
        response = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date=2027-01-04",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["date"], "2027-01-04")
        self.assertEqual(data["court"], self.court.pk)
        self.assertIn("slots", data)
        slots = data["slots"]
        # Con bloque 08:00-22:00 y slot de 60 min → 14 slots
        self.assertEqual(len(slots), 14, f"Se esperaban 14 slots, hubo {len(slots)}: {slots}")
        # Todos tienen is_available y start_dt/end_dt
        for slot in slots:
            self.assertIn("is_available", slot)
            self.assertIn("start_dt", slot)
            self.assertIn("end_dt", slot)

    def test_availability_marks_booked_slot_unavailable(self):
        """Un slot ya reservado aparece como is_available=False en la grilla."""
        # Reservar el slot de las 14:00 UTC (= 11:00 BA)
        slot_start = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        Booking.objects.create(
            court=self.court,
            guest_name="Ocupado",
            guest_phone="999",
            start_dt=slot_start,
            end_dt=slot_start.replace(hour=15),
            price="5000.00",
            status=Booking.Status.PENDING_PAYMENT,
        )

        response = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date=2027-01-04",
        )
        self.assertEqual(response.status_code, 200)
        slots = response.json()["slots"]

        # Buscar el slot de las 14:00 UTC
        slot_14 = next((s for s in slots if "2027-01-04T14:00:00" in s["start_dt"]), None)
        self.assertIsNotNone(slot_14, "El slot de las 14:00 UTC no fue encontrado.")
        self.assertFalse(slot_14["is_available"], "El slot reservado debe estar como no disponible.")

    def test_availability_no_date_param_returns_400(self):
        """GET /api/courts/{id}/availability/ sin ?date → 400 VALIDATION_ERROR."""
        response = self.client.get(f"/api/courts/{self.court.pk}/availability/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_availability_invalid_date_returns_400(self):
        """GET /api/courts/{id}/availability/?date=not-a-date → 400 VALIDATION_ERROR."""
        response = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date=not-a-date"
        )
        self.assertEqual(response.status_code, 400)
