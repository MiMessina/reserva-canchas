"""
Tests de SlotBlock — app courts

Cobertura:
  1. test_create_slot_block_operator_ok     — operator puede crear bloqueo → 201
  2. test_create_slot_block_admin_ok        — admin puede crear bloqueo → 201
  3. test_create_slot_block_player_forbidden — player → 403
  4. test_create_slot_block_invalid_dates   — start >= end → 400
  5. test_delete_slot_block_soft_delete     — DELETE → is_active=False, no borra físicamente
  6. test_slot_block_appears_in_grid        — SlotBlock activo → daily-grid devuelve status BLOCKED

Patrón: TenantTestCase + TenantClient.
"""

from datetime import datetime, timezone as tz

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.courts.models import Court, ScheduleBlock, SlotBlock
from apps.users.models import User


class TestSlotBlocksCRUD(TenantTestCase):
    """Tests de permisos y CRUD de SlotBlock."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@slotblock.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@slotblock.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@slotblock.localhost",
            password="playerpass123",
            role=User.Role.PLAYER,
        )

        self.admin_token = self._get_token("admin@slotblock.localhost", "adminpass123")
        self.operator_token = self._get_token("operator@slotblock.localhost", "oppass123")
        self.player_token = self._get_token("player@slotblock.localhost", "playerpass123")

        # Cancha activa
        self.court = Court.objects.create(
            name="Cancha SlotBlock Test",
            court_type="futbol_5",
            surface="sintético",
            base_price="5000.00",
            slot_duration_minutes=60,
        )

        # start_dt y end_dt futuros en UTC para el bloqueo de prueba
        # 2027-03-01 14:00 UTC
        self.start_dt = "2027-03-01T14:00:00Z"
        self.end_dt = "2027-03-01T16:00:00Z"

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        return resp.json()["access"]

    def _create_block(self, token, start_dt=None, end_dt=None):
        return self.client.post(
            "/api/slot-blocks/",
            {
                "court": self.court.pk,
                "start_dt": start_dt or self.start_dt,
                "end_dt": end_dt or self.end_dt,
                "reason": "Torneo interno",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    # -----------------------------------------------------------------------
    # Caso 1: operator puede crear bloqueo → 201
    # -----------------------------------------------------------------------

    def test_create_slot_block_operator_ok(self):
        """El operador puede crear un bloqueo de slot."""
        response = self._create_block(self.operator_token)
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["court"], self.court.pk)
        self.assertEqual(data["reason"], "Torneo interno")
        self.assertTrue(data["is_active"])

    # -----------------------------------------------------------------------
    # Caso 2: admin puede crear bloqueo → 201
    # -----------------------------------------------------------------------

    def test_create_slot_block_admin_ok(self):
        """El admin puede crear un bloqueo de slot."""
        response = self._create_block(self.admin_token)
        self.assertEqual(response.status_code, 201, response.content)

    # -----------------------------------------------------------------------
    # Caso 3: player → 403
    # -----------------------------------------------------------------------

    def test_create_slot_block_player_forbidden(self):
        """El player no tiene permiso para crear bloqueos de slot → 403."""
        response = self._create_block(self.player_token)
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 4: start >= end → 400
    # -----------------------------------------------------------------------

    def test_create_slot_block_invalid_dates_start_equals_end(self):
        """start_dt == end_dt → 400."""
        response = self._create_block(
            self.operator_token,
            start_dt="2027-03-01T14:00:00Z",
            end_dt="2027-03-01T14:00:00Z",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        # Verificar que hay código de error INVALID_SCHEDULE
        self.assertTrue(
            self._find_code(data, "INVALID_SCHEDULE"),
            f"Código INVALID_SCHEDULE no encontrado en: {data}",
        )

    def test_create_slot_block_invalid_dates_start_after_end(self):
        """start_dt > end_dt → 400."""
        response = self._create_block(
            self.operator_token,
            start_dt="2027-03-01T16:00:00Z",
            end_dt="2027-03-01T14:00:00Z",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertTrue(
            self._find_code(data, "INVALID_SCHEDULE"),
            f"Código INVALID_SCHEDULE no encontrado en: {data}",
        )

    # -----------------------------------------------------------------------
    # Caso 5: DELETE → is_active=False, no borra físicamente
    # -----------------------------------------------------------------------

    def test_delete_slot_block_soft_delete(self):
        """DELETE → is_active=False; el registro sigue en DB."""
        create_resp = self._create_block(self.operator_token)
        self.assertEqual(create_resp.status_code, 201, create_resp.content)
        block_id = create_resp.json()["id"]

        delete_resp = self.client.delete(
            f"/api/slot-blocks/{block_id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.operator_token}",
        )
        self.assertEqual(delete_resp.status_code, 204, delete_resp.content)

        # El registro sigue en DB con is_active=False
        block = SlotBlock.objects.get(pk=block_id)
        self.assertFalse(block.is_active, "El bloqueo debe tener is_active=False (soft-delete)")

        # Ya no aparece en el listado (filtra por is_active=True)
        list_resp = self.client.get(
            "/api/slot-blocks/",
            HTTP_AUTHORIZATION=f"Bearer {self.operator_token}",
        )
        ids_in_list = [item["id"] for item in list_resp.json().get("results", list_resp.json())]
        self.assertNotIn(block_id, ids_in_list)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _find_code(self, obj, code):
        """Busca recursivamente un dict con key 'code' == code."""
        if isinstance(obj, dict):
            if obj.get("code") == code:
                return True
            return any(self._find_code(v, code) for v in obj.values())
        if isinstance(obj, list):
            return any(self._find_code(item, code) for item in obj)
        return False


class TestSlotBlockInGrid(TenantTestCase):
    """Tests de integración de SlotBlock con la grilla diaria."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="operator@gridblock.localhost",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.operator_token = self._get_token("operator@gridblock.localhost", "oppass123")

        # Cancha activa con slot de 60 min
        self.court = Court.objects.create(
            name="Cancha Grid Block",
            court_type="padel",
            surface="cemento",
            base_price="3000.00",
            slot_duration_minutes=60,
        )

        # ScheduleBlock: lunes (0) 10:00-18:00
        ScheduleBlock.objects.create(
            court=self.court,
            weekday=0,
            open_time="10:00",
            close_time="18:00",
        )

        # 2027-01-04 es lunes (weekday=0)
        # Slot bloqueado: 11:00-12:00 BA = 14:00-15:00 UTC (UTC-3)
        self.block = SlotBlock.objects.create(
            court=self.court,
            start_dt=datetime(2027, 1, 4, 14, 0, 0, tzinfo=tz.utc),  # 11:00 BA
            end_dt=datetime(2027, 1, 4, 15, 0, 0, tzinfo=tz.utc),    # 12:00 BA
            reason="Mantenimiento",
            is_active=True,
        )

    def _get_token(self, email, password):
        resp = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        return resp.json()["access"]

    # -----------------------------------------------------------------------
    # Caso 6: SlotBlock activo aparece con status BLOCKED en la grilla
    # -----------------------------------------------------------------------

    def test_slot_block_appears_in_grid(self):
        """
        Un SlotBlock activo hace que el slot aparezca como BLOCKED en la grilla diaria.
        """
        resp = self.client.get(
            "/api/bookings/daily-grid/?date=2027-01-04",
            HTTP_AUTHORIZATION=f"Bearer {self.operator_token}",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        # Encontrar la cancha en el resultado
        court_data = next(
            (c for c in data["courts"] if c["id"] == self.court.pk),
            None,
        )
        self.assertIsNotNone(court_data, "La cancha no aparece en la grilla")

        # Buscar el slot bloqueado: start_dt == 2027-01-04T14:00:00+00:00
        blocked_slot = next(
            (
                s for s in court_data["slots"]
                if "2027-01-04T14:00:00" in s["start_dt"]
            ),
            None,
        )
        self.assertIsNotNone(blocked_slot, "El slot bloqueado no aparece en la grilla")
        self.assertEqual(blocked_slot["status"], "BLOCKED", f"Slot inesperado: {blocked_slot}")
        self.assertEqual(blocked_slot["block_id"], self.block.pk)
        self.assertEqual(blocked_slot["block_reason"], "Mantenimiento")
        self.assertIsNone(blocked_slot["booking_id"])

    def test_slot_block_deleted_does_not_appear_blocked(self):
        """Un SlotBlock dado de baja no bloquea el slot → aparece AVAILABLE."""
        # Dar de baja el bloqueo
        self.block.is_active = False
        self.block.save()

        resp = self.client.get(
            "/api/bookings/daily-grid/?date=2027-01-04",
            HTTP_AUTHORIZATION=f"Bearer {self.operator_token}",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        court_data = next(c for c in data["courts"] if c["id"] == self.court.pk)

        # El slot que antes estaba bloqueado ahora debe ser AVAILABLE
        slot = next(
            (s for s in court_data["slots"] if "2027-01-04T14:00:00" in s["start_dt"]),
            None,
        )
        self.assertIsNotNone(slot)
        self.assertEqual(slot["status"], "AVAILABLE", f"Esperaba AVAILABLE, recibí: {slot}")
