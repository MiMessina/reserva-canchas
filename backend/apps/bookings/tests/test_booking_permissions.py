"""
Tests de permisos — motor de reservas — Sprint 2

Cobertura (RBAC.md §4, §7):
  1.  test_unauthenticated_guest_can_create_booking  — sin JWT, guest → 201
  2.  test_player_cannot_list_all_bookings           — player GET /api/bookings/ → 403
  3.  test_operator_can_list_bookings                — operator GET /api/bookings/ → 200
  4.  test_admin_can_list_bookings                   — admin GET /api/bookings/ → 200
  5.  test_player_cannot_confirm                     — player POST .../confirm/ → 403
  6.  test_operator_can_confirm                      — operator POST .../confirm/ → 200
  7.  test_player_can_cancel_own_booking             — player cancela la suya → 200
  8.  test_player_cannot_cancel_others_booking       — player cancela ajena → 403
  9.  test_player_cannot_access_cash_movements       — player GET /api/cash-movements/ → 403
  10. test_operator_can_access_cash_movements        — operator GET /api/cash-movements/ → 200
  11. test_unauthenticated_cannot_confirm            — sin JWT POST .../confirm/ → 401
  12. test_admin_can_confirm                         — admin POST .../confirm/ → 200

Patrón: TenantTestCase + TenantClient (mismo que Sprint 1).
"""

from datetime import datetime, timezone as tz

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestBookingPermissions(TenantTestCase):
    """Tests de permisos en endpoints de reservas y caja."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Usuarios
        self.admin = User.objects.create_user(
            email="admin@perm.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@perm.localhost",
            password="oppass",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@perm.localhost",
            password="playerpass",
            role=User.Role.PLAYER,
        )
        self.player2 = User.objects.create_user(
            email="player2@perm.localhost",
            password="playerpass2",
            role=User.Role.PLAYER,
        )

        # Tokens
        self.admin_token = self._get_token("admin@perm.localhost", "adminpass")
        self.operator_token = self._get_token("operator@perm.localhost", "oppass")
        self.player_token = self._get_token("player@perm.localhost", "playerpass")
        self.player2_token = self._get_token("player2@perm.localhost", "playerpass2")

        # Cancha y bloque
        self.court = Court.objects.create(
            name="Cancha Permisos",
            court_type="futbol_5",
            surface="",
            base_price="4000.00",
            slot_duration_minutes=60,
        )
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,  # lunes
            open_time="08:00",
            close_time="22:00",
        )

        # Slot base futuro: lunes 2027-01-04 10:00 UTC = 07:00 BA (dentro del bloque)
        self.base_slot = datetime(2027, 1, 4, 11, 0, tzinfo=tz.utc)  # = 08:00 BA

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló para {email}: {response.content}")
        return response.json()["access"]

    def _headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _create_guest_booking(self, slot, name="Invitado", phone="000"):
        """Helper: crea una reserva de invitado sin JWT."""
        return self.client.post(
            "/api/bookings/",
            {
                "court": self.court.pk,
                "start_dt": slot.isoformat(),
                "guest_name": name,
                "guest_phone": phone,
            },
            content_type="application/json",
        )

    def _create_player_booking(self, slot, token):
        """Helper: crea una reserva con el token del player."""
        return self.client.post(
            "/api/bookings/",
            {
                "court": self.court.pk,
                "start_dt": slot.isoformat(),
            },
            content_type="application/json",
            **self._headers(token),
        )

    # -----------------------------------------------------------------------
    # 1. Invitado sin JWT puede crear reserva
    # -----------------------------------------------------------------------

    def test_unauthenticated_guest_can_create_booking(self):
        """Sin JWT con guest_name+phone → 201."""
        response = self._create_guest_booking(
            self.base_slot, name="Invitado Perm", phone="111"
        )
        self.assertEqual(response.status_code, 201, response.content)

    # -----------------------------------------------------------------------
    # 2. Player no puede ver listado completo
    # -----------------------------------------------------------------------

    def test_player_cannot_list_all_bookings(self):
        """Player GET /api/bookings/ → 403."""
        response = self.client.get("/api/bookings/", **self._headers(self.player_token))
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # 3. Operator puede listar reservas
    # -----------------------------------------------------------------------

    def test_operator_can_list_bookings(self):
        """Operator GET /api/bookings/ → 200."""
        response = self.client.get("/api/bookings/", **self._headers(self.operator_token))
        self.assertEqual(response.status_code, 200, response.content)

    # -----------------------------------------------------------------------
    # 4. Admin puede listar reservas
    # -----------------------------------------------------------------------

    def test_admin_can_list_bookings(self):
        """Admin GET /api/bookings/ → 200."""
        response = self.client.get("/api/bookings/", **self._headers(self.admin_token))
        self.assertEqual(response.status_code, 200, response.content)

    # -----------------------------------------------------------------------
    # 5. Player no puede confirmar una reserva
    # -----------------------------------------------------------------------

    def test_player_cannot_confirm(self):
        """Player POST .../confirm/ → 403."""
        slot = datetime(2027, 1, 4, 12, 0, tzinfo=tz.utc)
        create_resp = self._create_guest_booking(slot, "Para Confirmar", "222")
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # 6. Operator puede confirmar una reserva
    # -----------------------------------------------------------------------

    def test_operator_can_confirm(self):
        """Operator POST .../confirm/ → 200 CONFIRMED."""
        slot = datetime(2027, 1, 4, 13, 0, tzinfo=tz.utc)
        create_resp = self._create_guest_booking(slot, "Para Op Confirmar", "333")
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CONFIRMED")

    # -----------------------------------------------------------------------
    # 7. Player puede cancelar SU PROPIA reserva
    # -----------------------------------------------------------------------

    def test_player_can_cancel_own_booking(self):
        """Player POST .../cancel/ sobre su propia reserva → 200 CANCELLED."""
        slot = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)
        create_resp = self._create_player_booking(slot, self.player_token)
        self.assertEqual(create_resp.status_code, 201, create_resp.content)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/cancel/",
            {"reason": "No puedo ir"},
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CANCELLED")

    # -----------------------------------------------------------------------
    # 8. Player no puede cancelar la reserva de otro player
    # -----------------------------------------------------------------------

    def test_player_cannot_cancel_others_booking(self):
        """Player POST .../cancel/ sobre reserva ajena → 403."""
        # Reserva de player2 (slot distinto)
        slot = datetime(2027, 1, 4, 15, 0, tzinfo=tz.utc)
        create_resp = self._create_player_booking(slot, self.player2_token)
        self.assertEqual(create_resp.status_code, 201, create_resp.content)
        booking_id = create_resp.json()["id"]

        # Player1 intenta cancelar la reserva de player2
        response = self.client.post(
            f"/api/bookings/{booking_id}/cancel/",
            {"reason": "Quiero el slot"},
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # 9. Player no puede acceder a movimientos de caja
    # -----------------------------------------------------------------------

    def test_player_cannot_access_cash_movements(self):
        """Player GET /api/cash-movements/ → 403."""
        response = self.client.get(
            "/api/cash-movements/", **self._headers(self.player_token)
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # 10. Operator puede acceder a movimientos de caja
    # -----------------------------------------------------------------------

    def test_operator_can_access_cash_movements(self):
        """Operator GET /api/cash-movements/ → 200."""
        response = self.client.get(
            "/api/cash-movements/", **self._headers(self.operator_token)
        )
        self.assertEqual(response.status_code, 200, response.content)

    # -----------------------------------------------------------------------
    # 11. Sin autenticación no se puede confirmar
    # -----------------------------------------------------------------------

    def test_unauthenticated_cannot_confirm(self):
        """Sin JWT POST .../confirm/ → 401."""
        slot = datetime(2027, 1, 4, 16, 0, tzinfo=tz.utc)
        create_resp = self._create_guest_booking(slot, "SinAuth", "444")
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # 12. Admin puede confirmar una reserva
    # -----------------------------------------------------------------------

    def test_admin_can_confirm(self):
        """Admin POST .../confirm/ → 200 CONFIRMED."""
        slot = datetime(2027, 1, 4, 17, 0, tzinfo=tz.utc)
        create_resp = self._create_guest_booking(slot, "Para Admin Confirmar", "555")
        self.assertEqual(create_resp.status_code, 201)
        booking_id = create_resp.json()["id"]

        response = self.client.post(
            f"/api/bookings/{booking_id}/confirm/",
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CONFIRMED")
