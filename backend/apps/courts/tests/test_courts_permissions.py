"""
Tests de permisos — app courts — Sprint 1

Cobertura (RBAC.md §4, §7):
  1. Usuario sin autenticación → 401 en GET y POST.
  2. player no puede crear cancha (POST → 403).
  3. player no puede editar cancha (PATCH → 403).
  4. player no puede dar de baja cancha (DELETE → 403).
  5. player SÍ puede listar canchas (GET list → 200).
  6. player SÍ puede ver detalle de cancha (GET retrieve → 200).
  7. operator no puede crear cancha (POST → 403).
  8. operator no puede editar cancha (PATCH → 403).
  9. operator SÍ puede listar canchas (GET → 200).
 10. tenant_admin puede hacer CRUD completo.
 11. Mismos permisos para /api/schedule-blocks/.

Patrón: TenantTestCase + TenantClient (igual que Sprint 0).
"""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.users.models import User


class TestCourtsPermissions(TenantTestCase):
    """Tests de permisos en endpoints de canchas."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Crear usuarios con distintos roles
        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@test.localhost",
            password="oppass",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@test.localhost",
            password="playerpass",
            role=User.Role.PLAYER,
        )

        # Obtener tokens
        self.admin_token = self._get_token("admin@test.localhost", "adminpass")
        self.operator_token = self._get_token("operator@test.localhost", "oppass")
        self.player_token = self._get_token("player@test.localhost", "playerpass")

        # Crear una cancha como admin para las pruebas de detalle/edición/borrado
        admin_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        court_response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Permiso",
                "court_type": "padel",
                "surface": "",
                "base_price": "4000.00",
                "slot_duration_minutes": 90,
            },
            content_type="application/json",
            **admin_headers,
        )
        self.assertEqual(court_response.status_code, 201, court_response.content)
        self.court_id = court_response.json()["id"]

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

    # -----------------------------------------------------------------------
    # Sin autenticación
    # -----------------------------------------------------------------------

    def test_unauthenticated_get_courts_returns_401(self):
        """GET /api/courts/ sin token → 401."""
        response = self.client.get("/api/courts/")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_post_courts_returns_401(self):
        """POST /api/courts/ sin token → 401."""
        response = self.client.post(
            "/api/courts/",
            {"name": "X", "court_type": "padel", "base_price": "0", "slot_duration_minutes": 60},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    # -----------------------------------------------------------------------
    # player: solo lectura
    # -----------------------------------------------------------------------

    def test_player_can_list_courts(self):
        """player GET /api/courts/ → 200."""
        response = self.client.get("/api/courts/", **self._headers(self.player_token))
        self.assertEqual(response.status_code, 200)

    def test_player_can_retrieve_court(self):
        """player GET /api/courts/{id}/ → 200."""
        response = self.client.get(f"/api/courts/{self.court_id}/", **self._headers(self.player_token))
        self.assertEqual(response.status_code, 200)

    def test_player_cannot_create_court(self):
        """player POST /api/courts/ → 403."""
        response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Player",
                "court_type": "padel",
                "surface": "",
                "base_price": "1000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_player_cannot_patch_court(self):
        """player PATCH /api/courts/{id}/ → 403."""
        response = self.client.patch(
            f"/api/courts/{self.court_id}/",
            {"base_price": "9999.00"},
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_player_cannot_delete_court(self):
        """player DELETE /api/courts/{id}/ → 403."""
        response = self.client.delete(
            f"/api/courts/{self.court_id}/",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403)

    # -----------------------------------------------------------------------
    # operator: solo lectura
    # -----------------------------------------------------------------------

    def test_operator_can_list_courts(self):
        """operator GET /api/courts/ → 200."""
        response = self.client.get("/api/courts/", **self._headers(self.operator_token))
        self.assertEqual(response.status_code, 200)

    def test_operator_cannot_create_court(self):
        """operator POST /api/courts/ → 403."""
        response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Operator",
                "court_type": "futbol_7",
                "surface": "",
                "base_price": "2000.00",
                "slot_duration_minutes": 90,
            },
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_patch_court(self):
        """operator PATCH /api/courts/{id}/ → 403."""
        response = self.client.patch(
            f"/api/courts/{self.court_id}/",
            {"base_price": "1.00"},
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_delete_court(self):
        """operator DELETE /api/courts/{id}/ → 403."""
        response = self.client.delete(
            f"/api/courts/{self.court_id}/",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403)

    # -----------------------------------------------------------------------
    # tenant_admin: CRUD completo
    # -----------------------------------------------------------------------

    def test_admin_can_create_court(self):
        """tenant_admin POST /api/courts/ → 201."""
        response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Admin",
                "court_type": "futbol_5",
                "surface": "sintético",
                "base_price": "6000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 201)

    def test_admin_can_patch_court(self):
        """tenant_admin PATCH /api/courts/{id}/ → 200."""
        response = self.client.patch(
            f"/api/courts/{self.court_id}/",
            {"slot_duration_minutes": 90},
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_court(self):
        """tenant_admin DELETE /api/courts/{id}/ → 204."""
        # Crear una cancha extra para borrar sin afectar otros tests
        court_resp = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Para Borrar",
                "court_type": "futbol_5",
                "surface": "",
                "base_price": "1000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        court_id = court_resp.json()["id"]

        response = self.client.delete(
            f"/api/courts/{court_id}/",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 204)


class TestScheduleBlockPermissions(TenantTestCase):
    """Tests de permisos en endpoints de bloques horarios."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@sb.localhost",
            password="adminpass",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@sb.localhost",
            password="oppass",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@sb.localhost",
            password="playerpass",
            role=User.Role.PLAYER,
        )

        self.admin_token = self._get_token("admin@sb.localhost", "adminpass")
        self.operator_token = self._get_token("operator@sb.localhost", "oppass")
        self.player_token = self._get_token("player@sb.localhost", "playerpass")

        # Crear cancha como admin
        admin_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        court_response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha SB",
                "court_type": "padel",
                "surface": "",
                "base_price": "3000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **admin_headers,
        )
        self.court_id = court_response.json()["id"]

        # Crear bloque como admin
        block_response = self.client.post(
            "/api/schedule-blocks/",
            {
                "court": self.court_id,
                "weekday": 0,
                "open_time": "08:00",
                "close_time": "12:00",
            },
            content_type="application/json",
            **admin_headers,
        )
        self.block_id = block_response.json()["id"]

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        return response.json()["access"]

    def _headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_unauthenticated_get_schedule_blocks_returns_401(self):
        """GET /api/schedule-blocks/ sin token → 401."""
        response = self.client.get("/api/schedule-blocks/")
        self.assertEqual(response.status_code, 401)

    def test_player_can_list_schedule_blocks(self):
        """player GET /api/schedule-blocks/ → 200."""
        response = self.client.get("/api/schedule-blocks/", **self._headers(self.player_token))
        self.assertEqual(response.status_code, 200)

    def test_player_cannot_create_schedule_block(self):
        """player POST /api/schedule-blocks/ → 403."""
        response = self.client.post(
            "/api/schedule-blocks/",
            {
                "court": self.court_id,
                "weekday": 1,
                "open_time": "10:00",
                "close_time": "14:00",
            },
            content_type="application/json",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_player_cannot_delete_schedule_block(self):
        """player DELETE /api/schedule-blocks/{id}/ → 403."""
        response = self.client.delete(
            f"/api/schedule-blocks/{self.block_id}/",
            **self._headers(self.player_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_delete_schedule_block(self):
        """operator DELETE /api/schedule-blocks/{id}/ → 403."""
        response = self.client.delete(
            f"/api/schedule-blocks/{self.block_id}/",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_schedule_block(self):
        """tenant_admin POST /api/schedule-blocks/ → 201."""
        response = self.client.post(
            "/api/schedule-blocks/",
            {
                "court": self.court_id,
                "weekday": 2,
                "open_time": "08:00",
                "close_time": "12:00",
            },
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 201)
