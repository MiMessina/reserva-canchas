"""
Tests de "Mis reservas" (guest-lookup) y cancelación pública — app bookings

Cobertura:
  1. test_guest_lookup_returns_active_bookings  — devuelve PENDING_PAYMENT y CONFIRMED, no CANCELLED
  2. test_guest_lookup_empty_if_no_results      — lista vacía si no hay reservas
  3. test_guest_lookup_requires_phone           — sin ?phone= → 400
  4. test_guest_lookup_phone_too_short          — phone < 6 chars → 400
  5. test_cancel_guest_ok                       — phone correcto cancela → 200
  6. test_cancel_guest_wrong_phone              — phone incorrecto → 403
  7. test_cancel_guest_already_cancelled        — ya cancelada → 409
  8. test_cancel_guest_already_completed        — ya completada → 409
  9. test_cancel_guest_missing_phone            — body sin guest_phone → 400
  10. test_cancel_guest_booking_not_found       — booking inexistente → 404

Patrón: TenantTestCase + TenantClient.
"""

from datetime import datetime, timedelta, timezone as tz
from unittest.mock import patch

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


# ---------------------------------------------------------------------------
# Helpers de setup compartidos
# ---------------------------------------------------------------------------

def _make_future_start(weekday=0, hour=14):
    """
    Retorna un datetime futuro con el weekday e hora indicados.
    2027-01-04 es lunes (weekday=0). Se avanza semanas según el weekday.
    """
    base = datetime(2027, 1, 4, hour, 0, 0, tzinfo=tz.utc)  # 2027-01-04 = lunes
    offset = (weekday - 0) % 7
    return base + timedelta(days=offset)


class TestGuestLookup(TenantTestCase):
    """Tests del endpoint GET /api/bookings/guest-lookup/?phone=XXXX"""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="operator@guestlookup.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.operator_token = self._get_token("operator@guestlookup.localhost", "oppass123")

        # Cancha activa + schedule block para lunes
        self.court = Court.objects.create(
            name="Cancha GuestLookup",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,   # lunes
            open_time="08:00",
            close_time="22:00",
        )

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        return resp.json()["access"]

    def _create_guest_booking(self, start_dt, phone="1155551234", status=None):
        """
        Crea un booking de invitado directamente en DB con el estado indicado.
        """
        start = start_dt
        end = start + timedelta(hours=1)
        booking = Booking.objects.create(
            court=self.court,
            guest_name="Juan Perez",
            guest_phone=phone,
            start_dt=start,
            end_dt=end,
            price=self.court.base_price,
            status=status or Booking.Status.PENDING_PAYMENT,
            is_active=True,
        )
        return booking

    # -----------------------------------------------------------------------
    # Caso 1: devuelve PENDING_PAYMENT y CONFIRMED, no CANCELLED
    # -----------------------------------------------------------------------

    def test_guest_lookup_returns_active_bookings(self):
        """
        GET ?phone=XXXX retorna reservas en PENDING_PAYMENT y CONFIRMED.
        Las CANCELLED no aparecen.
        """
        phone = "1155551234"
        pending = self._create_guest_booking(_make_future_start(0, 10), phone=phone)
        confirmed = self._create_guest_booking(_make_future_start(0, 12), phone=phone)
        confirmed.status = Booking.Status.CONFIRMED
        confirmed.save()
        cancelled = self._create_guest_booking(_make_future_start(0, 14), phone=phone)
        cancelled.status = Booking.Status.CANCELLED
        cancelled.save()

        resp = self.client.get(f"/api/bookings/guest-lookup/?phone={phone}")
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        # Manejo paginado o sin paginación
        results = data.get("results", data) if isinstance(data, dict) else data
        ids = [b["id"] for b in results]

        self.assertIn(pending.pk, ids, "PENDING_PAYMENT debe aparecer")
        self.assertIn(confirmed.pk, ids, "CONFIRMED debe aparecer")
        self.assertNotIn(cancelled.pk, ids, "CANCELLED no debe aparecer")

    # -----------------------------------------------------------------------
    # Caso 2: lista vacía si no hay reservas
    # -----------------------------------------------------------------------

    def test_guest_lookup_empty_if_no_results(self):
        """GET con phone sin reservas → lista vacía []."""
        resp = self.client.get("/api/bookings/guest-lookup/?phone=9900001111")
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        self.assertEqual(results, [], f"Esperaba lista vacía, recibí: {results}")

    # -----------------------------------------------------------------------
    # Caso 3: sin ?phone= → 400
    # -----------------------------------------------------------------------

    def test_guest_lookup_requires_phone(self):
        """GET sin parámetro phone → 400 VALIDATION_ERROR."""
        resp = self.client.get("/api/bookings/guest-lookup/")
        self.assertEqual(resp.status_code, 400, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 4: phone < 6 chars → 400
    # -----------------------------------------------------------------------

    def test_guest_lookup_phone_too_short(self):
        """GET con phone de menos de 6 caracteres → 400 VALIDATION_ERROR."""
        resp = self.client.get("/api/bookings/guest-lookup/?phone=123")
        self.assertEqual(resp.status_code, 400, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 5: un booking activo no aparece cuando pertenece a otro teléfono
    # -----------------------------------------------------------------------

    def test_guest_lookup_isolates_by_phone(self):
        """Reservas de otros teléfonos no aparecen en la búsqueda."""
        self._create_guest_booking(_make_future_start(0, 10), phone="1155551111")
        self._create_guest_booking(_make_future_start(0, 12), phone="1155552222")

        resp = self.client.get("/api/bookings/guest-lookup/?phone=1155551111")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        for booking in results:
            # Solo debe devolver bookings del teléfono buscado
            self.assertEqual(len(results), 1)


class TestCancelGuest(TenantTestCase):
    """Tests del endpoint POST /api/bookings/{id}/cancel-guest/"""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="operator@cancelguest.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.operator_token = self._get_token("operator@cancelguest.localhost", "oppass123")

        # Cancha + schedule block
        self.court = Court.objects.create(
            name="Cancha CancelGuest",
            court_type="padel",
            surface="cemento",
            base_price="3000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,
            open_time="08:00",
            close_time="22:00",
        )
        self.phone = "1155559999"

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        return resp.json()["access"]

    def _create_guest_booking(self, status=None, phone=None):
        phone = phone or self.phone
        start = _make_future_start(0, 10)
        end = start + timedelta(hours=1)
        return Booking.objects.create(
            court=self.court,
            guest_name="Ana García",
            guest_phone=phone,
            start_dt=start,
            end_dt=end,
            price=self.court.base_price,
            status=status or Booking.Status.PENDING_PAYMENT,
            is_active=True,
        )

    def _cancel_guest(self, pk, phone):
        return self.client.post(
            f"/api/bookings/{pk}/cancel-guest/",
            {"guest_phone": phone},
            content_type="application/json",
        )

    # -----------------------------------------------------------------------
    # Caso 5: phone correcto cancela → 200
    # -----------------------------------------------------------------------

    def test_cancel_guest_ok(self):
        """El invitado puede cancelar su propia reserva con el teléfono correcto → 200."""
        booking = self._create_guest_booking()
        resp = self._cancel_guest(booking.pk, self.phone)
        self.assertEqual(resp.status_code, 200, resp.content)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_cancel_guest_confirmed_ok(self):
        """El invitado puede cancelar una reserva CONFIRMED con el teléfono correcto → 200."""
        booking = self._create_guest_booking(status=Booking.Status.CONFIRMED)
        resp = self._cancel_guest(booking.pk, self.phone)
        self.assertEqual(resp.status_code, 200, resp.content)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    # -----------------------------------------------------------------------
    # Caso 6: phone incorrecto → 403
    # -----------------------------------------------------------------------

    def test_cancel_guest_wrong_phone(self):
        """El teléfono no coincide → 403 FORBIDDEN."""
        booking = self._create_guest_booking()
        resp = self._cancel_guest(booking.pk, "9900001111")
        self.assertEqual(resp.status_code, 403, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    # -----------------------------------------------------------------------
    # Caso 7: ya cancelada → 409
    # -----------------------------------------------------------------------

    def test_cancel_guest_already_cancelled(self):
        """Reserva ya CANCELLED → 409 INVALID_TRANSITION."""
        booking = self._create_guest_booking(status=Booking.Status.CANCELLED)
        resp = self._cancel_guest(booking.pk, self.phone)
        self.assertEqual(resp.status_code, 409, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_TRANSITION")

    # -----------------------------------------------------------------------
    # Caso 8: ya completada → 409
    # -----------------------------------------------------------------------

    def test_cancel_guest_already_completed(self):
        """Reserva ya COMPLETED → 409 INVALID_TRANSITION."""
        # Crear booking con start/end en el pasado para completar
        past_start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=tz.utc)
        past_end = past_start + timedelta(hours=1)
        booking = Booking.objects.create(
            court=self.court,
            guest_name="Ana García",
            guest_phone=self.phone,
            start_dt=past_start,
            end_dt=past_end,
            price=self.court.base_price,
            status=Booking.Status.COMPLETED,
            is_active=True,
        )
        resp = self._cancel_guest(booking.pk, self.phone)
        self.assertEqual(resp.status_code, 409, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_TRANSITION")

    # -----------------------------------------------------------------------
    # Caso 9: body sin guest_phone → 400
    # -----------------------------------------------------------------------

    def test_cancel_guest_missing_phone(self):
        """Body sin guest_phone → 400 VALIDATION_ERROR."""
        booking = self._create_guest_booking()
        resp = self.client.post(
            f"/api/bookings/{booking.pk}/cancel-guest/",
            {},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 10: booking inexistente → 404
    # -----------------------------------------------------------------------

    def test_cancel_guest_booking_not_found(self):
        """Booking inexistente → 404."""
        resp = self._cancel_guest(99999, self.phone)
        self.assertEqual(resp.status_code, 404, resp.content)
