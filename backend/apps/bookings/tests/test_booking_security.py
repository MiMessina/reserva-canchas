"""
Tests de seguridad y edge cases — motor de reservas — Sprint 2

Cubre los hallazgos del security review aplicados en este sprint:
  1. Ownership defensivo en cancel: player no puede cancelar reserva de invitado
     ni reserva de otro player.
  2. Serializer diferenciado: create no expone guest_phone/guest_name/user al público.
  3. Staff list incluye campos de contacto (guest_name, guest_phone).
  4. Fecha inválida en GET /api/cash-movements/?date= retorna 400.
  5. Fecha mayor a 90 días en GET /api/courts/{id}/availability/ retorna 400.
  6. Fecha dentro de 90 días en availability no retorna 400.

Patrón: TenantTestCase + TenantClient (igual que el resto de tests de bookings).
"""

from datetime import datetime, timedelta, timezone as tz

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestBookingCancelOwnership(TenantTestCase):
    """
    Hallazgo de seguridad: ownership en cancel debe ser defensivo para cualquier rol.

    Casos cubiertos:
      - Player no puede cancelar la reserva de otro player.
      - Player no puede cancelar una reserva de invitado (booking.user is None).
      - Player puede cancelar su propia reserva.
      - Admin puede cancelar una reserva de invitado.
    """

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@sec.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.player1 = User.objects.create_user(
            email="p1@sec.localhost",
            password="pass1",
            role=User.Role.PLAYER,
        )
        self.player2 = User.objects.create_user(
            email="p2@sec.localhost",
            password="pass2",
            role=User.Role.PLAYER,
        )

        self.admin_token = self._get_token("admin@sec.localhost", "adminpass")
        self.player1_token = self._get_token("p1@sec.localhost", "pass1")
        self.player2_token = self._get_token("p2@sec.localhost", "pass2")

        # Cancha con bloque para lunes
        self.court = Court.objects.create(
            name="Cancha Sec",
            court_type="futbol_5",
            surface="",
            base_price="1000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
            open_time="08:00",
            close_time="22:00",
        )

        # Slots futuros: lunes 2027-01-04 en distintos horarios (UTC)
        # 2027-01-04 es lunes. 11:00 UTC = 08:00 Buenos Aires (dentro del bloque)
        self.slot_player1 = datetime(2027, 1, 4, 11, 0, tzinfo=tz.utc)
        self.slot_guest = datetime(2027, 1, 4, 12, 0, tzinfo=tz.utc)

        # Reserva de player1
        self.booking_player1 = Booking.objects.create(
            court=self.court,
            user=self.player1,
            start_dt=self.slot_player1,
            end_dt=self.slot_player1 + timedelta(hours=1),
            price=1000,
            status=Booking.Status.PENDING_PAYMENT,
        )
        # Reserva de invitado (sin usuario registrado)
        self.booking_guest = Booking.objects.create(
            court=self.court,
            user=None,
            guest_name="Invitado Sec",
            guest_phone="11999",
            start_dt=self.slot_guest,
            end_dt=self.slot_guest + timedelta(hours=1),
            price=1000,
            status=Booking.Status.PENDING_PAYMENT,
        )

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, f"Login falló para {email}: {resp.content}")
        return resp.json()["access"]

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_player_cannot_cancel_other_player_booking(self):
        """Player2 intenta cancelar la reserva de player1 → 403."""
        resp = self.client.post(
            f"/api/bookings/{self.booking_player1.pk}/cancel/",
            content_type="application/json",
            **self._auth(self.player2_token),
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "TENANT_FORBIDDEN")

    def test_player_cannot_cancel_guest_booking(self):
        """Player1 intenta cancelar una reserva de invitado → 403.

        booking.user is None, player1 != None, luego booking.user != user → 403.
        """
        resp = self.client.post(
            f"/api/bookings/{self.booking_guest.pk}/cancel/",
            content_type="application/json",
            **self._auth(self.player1_token),
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "TENANT_FORBIDDEN")

    def test_player_can_cancel_own_booking(self):
        """Player1 cancela su propia reserva → 200 CANCELLED."""
        resp = self.client.post(
            f"/api/bookings/{self.booking_player1.pk}/cancel/",
            {"reason": "No puedo ir"},
            content_type="application/json",
            **self._auth(self.player1_token),
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "CANCELLED")

    def test_admin_can_cancel_guest_booking(self):
        """Admin puede cancelar una reserva de invitado → 200 CANCELLED."""
        resp = self.client.post(
            f"/api/bookings/{self.booking_guest.pk}/cancel/",
            {"reason": "Admin cancela"},
            content_type="application/json",
            **self._auth(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "CANCELLED")


class TestCashMovementDateValidation(TenantTestCase):
    """
    Hallazgo de seguridad: fecha inválida en ?date debe retornar 400.

    Antes del fix, una fecha inválida silenciaba el error y devolvía todos los registros.
    """

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        self.admin = User.objects.create_user(
            email="admin@cashsec.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.admin_token = self._get_token("admin@cashsec.localhost", "adminpass")

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, f"Login falló: {resp.content}")
        return resp.json()["access"]

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_invalid_date_returns_400(self):
        """GET /api/cash-movements/?date=invalid → 400 VALIDATION_ERROR."""
        resp = self.client.get(
            "/api/cash-movements/?date=invalid",
            **self._auth(self.admin_token),
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_ERROR")

    def test_invalid_date_format_like_slash_returns_400(self):
        """GET /api/cash-movements/?date=01/06/2026 → 400 (formato incorrecto)."""
        resp = self.client.get(
            "/api/cash-movements/?date=01/06/2026",
            **self._auth(self.admin_token),
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_ERROR")

    def test_valid_date_returns_200(self):
        """GET /api/cash-movements/?date=2026-06-01 → 200 (lista vacía es OK)."""
        resp = self.client.get(
            "/api/cash-movements/?date=2026-06-01",
            **self._auth(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200, resp.content)


class TestAvailabilityDateLimit(TenantTestCase):
    """
    Hallazgo de seguridad: fecha mayor a 90 días en availability debe retornar 400.

    Antes del fix, se podía consultar disponibilidad para fechas arbitrariamente lejanas
    (ej: año 2099), saturando la DB con queries innecesarias.
    """

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        self.court = Court.objects.create(
            name="Cancha Avail",
            court_type="futbol_5",
            surface="",
            base_price="1000.00",
            slot_duration_minutes=60,
        )

    def test_date_beyond_90_days_returns_400(self):
        """Fecha > 90 días desde hoy → 400 VALIDATION_ERROR."""
        from datetime import date, timedelta
        far_date = (date.today() + timedelta(days=100)).isoformat()
        resp = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date={far_date}",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_ERROR")

    def test_date_within_90_days_does_not_return_400(self):
        """Fecha <= 90 días desde hoy → no es 400 (puede ser 200 con slots vacíos)."""
        from datetime import date, timedelta
        near_date = (date.today() + timedelta(days=5)).isoformat()
        resp = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date={near_date}",
        )
        self.assertNotEqual(resp.status_code, 400, resp.content)

    def test_invalid_date_format_in_availability_returns_400(self):
        """Fecha con formato inválido → 400 VALIDATION_ERROR."""
        resp = self.client.get(
            f"/api/courts/{self.court.pk}/availability/?date=no-es-fecha",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_ERROR")


class TestBookingSerializerByRole(TenantTestCase):
    """
    Hallazgo de seguridad: serializer diferenciado por rol.

    - El response de create (público) no debe exponer guest_phone, guest_name ni user.
    - El response de list para staff debe incluir guest_name y guest_phone.
    """

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@serial.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.admin_token = self._get_token("admin@serial.localhost", "adminpass")

        self.court = Court.objects.create(
            name="Cancha Serial",
            court_type="futbol_5",
            surface="",
            base_price="1000.00",
            slot_duration_minutes=60,
        )
        # Bloque para lunes: 2027-01-04 es lunes
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,
            open_time="08:00",
            close_time="22:00",
        )
        # 2027-01-04 11:00 UTC = 08:00 Buenos Aires (dentro del bloque)
        self.start = datetime(2027, 1, 4, 11, 0, tzinfo=tz.utc)

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, f"Login falló: {resp.content}")
        return resp.json()["access"]

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_create_response_does_not_expose_guest_phone_to_public(self):
        """POST sin JWT (invitado) → 201 y la respuesta NO incluye guest_phone, guest_name ni user."""
        resp = self.client.post(
            "/api/bookings/",
            {
                "court": self.court.pk,
                "start_dt": self.start.isoformat(),
                "guest_name": "Juan Public",
                "guest_phone": "1199999999",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertNotIn("guest_phone", data)
        self.assertNotIn("guest_name", data)
        self.assertNotIn("user", data)

    def test_create_response_includes_expected_public_fields(self):
        """POST invitado → respuesta incluye los campos públicos esperados."""
        resp = self.client.post(
            "/api/bookings/",
            {
                "court": self.court.pk,
                "start_dt": self.start.isoformat(),
                "guest_name": "Juan Public",
                "guest_phone": "1199999999",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        for field in ("id", "court", "start_dt", "end_dt", "status", "price"):
            self.assertIn(field, data, f"Campo '{field}' debería estar en la respuesta pública")

    def test_staff_list_includes_contact_fields(self):
        """GET /api/bookings/ como admin → la respuesta incluye guest_name y guest_phone."""
        # Crear una reserva de invitado
        Booking.objects.create(
            court=self.court,
            user=None,
            guest_name="Juan Staff",
            guest_phone="1188888888",
            start_dt=self.start,
            end_dt=self.start + timedelta(hours=1),
            price=1000,
            status=Booking.Status.PENDING_PAYMENT,
        )
        resp = self.client.get(
            "/api/bookings/",
            **self._auth(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        # Puede estar paginado o no
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, list) and results:
            booking_data = results[0]
            self.assertIn("guest_name", booking_data)
            self.assertIn("guest_phone", booking_data)
