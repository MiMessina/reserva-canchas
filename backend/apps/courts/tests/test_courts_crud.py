"""
Tests CRUD de canchas — Sprint 1

Cobertura:
  1. Crear una cancha vía POST /api/courts/ retorna 201 y datos correctos.
  2. Listar canchas vía GET /api/courts/ retorna la cancha creada.
  3. Editar cancha vía PATCH /api/courts/{id}/ actualiza el campo y retorna 200.
  4. Baja lógica vía DELETE /api/courts/{id}/ retorna 204, is_active=False y el
     registro SIGUE en la base de datos (no se elimina físicamente).
  5. GET /api/courts/{id}/ retorna 200 con los datos correctos.
  6. Filtro por court_type retorna solo las canchas del tipo indicado.
  7. Filtro por is_active retorna solo las canchas activas/inactivas.
  8. Crear ScheduleBlock válido y verificar creación.
  9. Listar ScheduleBlocks filtrando por court.
 10. PATCH ScheduleBlock actualiza campos.
 11. DELETE ScheduleBlock hace soft-delete (is_active=False, registro en DB).

Patrón: TenantTestCase + TenantClient (igual que Sprint 0).
El tenant_admin se crea en setUp y se autentica para las mutaciones.
"""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestCourtsCRUD(TenantTestCase):
    """Tests de operaciones CRUD sobre el modelo Court."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # tenant_admin para mutaciones
        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        # Obtener token JWT
        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@test.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, f"Login falló: {response.content}")
        self.token = response.json()["access"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def _create_court(self, name="Cancha 1", court_type="futbol_5"):
        """Helper: crea una cancha vía API y retorna la response."""
        return self.client.post(
            "/api/courts/",
            {
                "name": name,
                "court_type": court_type,
                "surface": "césped sintético",
                "base_price": "5000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self.auth_headers,
        )

    # -----------------------------------------------------------------------
    # Caso 1: crear cancha
    # -----------------------------------------------------------------------

    def test_create_court_returns_201(self):
        """POST /api/courts/ con datos válidos retorna 201 y la cancha creada."""
        response = self._create_court(name="Cancha A")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["name"], "Cancha A")
        self.assertEqual(data["court_type"], "futbol_5")
        self.assertTrue(data["is_active"])
        self.assertIn("id", data)

    # -----------------------------------------------------------------------
    # Caso 2: listar canchas
    # -----------------------------------------------------------------------

    def test_list_courts_returns_created_court(self):
        """GET /api/courts/ lista la cancha creada."""
        self._create_court(name="Cancha Lista")
        response = self.client.get("/api/courts/", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Puede venir paginado
        results = data.get("results", data)
        names = [c["name"] for c in results]
        self.assertIn("Cancha Lista", names)

    # -----------------------------------------------------------------------
    # Caso 3: editar cancha (PATCH)
    # -----------------------------------------------------------------------

    def test_patch_court_updates_field(self):
        """PATCH /api/courts/{id}/ actualiza el campo y retorna 200."""
        create_response = self._create_court(name="Cancha Editar")
        court_id = create_response.json()["id"]

        patch_response = self.client.patch(
            f"/api/courts/{court_id}/",
            {"base_price": "7500.00"},
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(patch_response.status_code, 200, patch_response.content)
        self.assertEqual(patch_response.json()["base_price"], "7500.00")

    # -----------------------------------------------------------------------
    # Caso 4: baja lógica (DELETE → is_active=False, registro permanece en DB)
    # -----------------------------------------------------------------------

    def test_delete_court_sets_is_active_false(self):
        """DELETE /api/courts/{id}/ retorna 204 y deja is_active=False en DB."""
        create_response = self._create_court(name="Cancha Borrar")
        court_id = create_response.json()["id"]

        delete_response = self.client.delete(
            f"/api/courts/{court_id}/",
            **self.auth_headers,
        )
        self.assertEqual(delete_response.status_code, 204)

        # El registro DEBE seguir en la DB (soft-delete)
        court = Court.objects.get(pk=court_id)
        self.assertFalse(court.is_active, "FALLA: is_active sigue True tras DELETE.")

    def test_delete_court_record_remains_in_db(self):
        """Después del DELETE el registro sigue en DB (prohibido DELETE físico)."""
        create_response = self._create_court(name="Cancha Física")
        court_id = create_response.json()["id"]

        self.client.delete(f"/api/courts/{court_id}/", **self.auth_headers)

        self.assertTrue(
            Court.objects.filter(pk=court_id).exists(),
            "FALLA: el registro fue borrado físicamente.",
        )

    # -----------------------------------------------------------------------
    # Caso 5: detalle de cancha
    # -----------------------------------------------------------------------

    def test_retrieve_court_returns_200(self):
        """GET /api/courts/{id}/ retorna 200 con datos correctos."""
        create_response = self._create_court(name="Cancha Detalle", court_type="padel")
        court_id = create_response.json()["id"]

        response = self.client.get(f"/api/courts/{court_id}/", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Cancha Detalle")
        self.assertEqual(data["court_type"], "padel")

    # -----------------------------------------------------------------------
    # Caso 6: filtro por court_type
    # -----------------------------------------------------------------------

    def test_filter_by_court_type(self):
        """Filtro ?court_type=padel retorna solo canchas de ese tipo."""
        self._create_court(name="Cancha Fútbol", court_type="futbol_5")
        self._create_court(name="Cancha Pádel", court_type="padel")

        response = self.client.get(
            "/api/courts/?court_type=padel", **self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", response.json())
        types = [c["court_type"] for c in results]
        self.assertTrue(all(t == "padel" for t in types), f"Tipos encontrados: {types}")
        self.assertTrue(any(c["name"] == "Cancha Pádel" for c in results))

    # -----------------------------------------------------------------------
    # Caso 7: filtro por is_active
    # -----------------------------------------------------------------------

    def test_filter_by_is_active_false(self):
        """Filtro ?is_active=false retorna solo canchas inactivas."""
        create_response = self._create_court(name="Cancha Inactiva")
        court_id = create_response.json()["id"]
        # Dar de baja
        self.client.delete(f"/api/courts/{court_id}/", **self.auth_headers)

        response = self.client.get("/api/courts/?is_active=false", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", response.json())
        self.assertTrue(len(results) >= 1)
        self.assertTrue(all(not c["is_active"] for c in results))


class TestScheduleBlocksCRUD(TenantTestCase):
    """Tests de operaciones CRUD sobre el modelo ScheduleBlock."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@test.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@test.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token = response.json()["access"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Crear cancha base para los tests de bloques
        court_response = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Base",
                "court_type": "futbol_5",
                "surface": "",
                "base_price": "3000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self.auth_headers,
        )
        self.court_id = court_response.json()["id"]

    def _create_block(self, weekday=0, open_time="08:00", close_time="12:00"):
        """Helper: crea un ScheduleBlock vía API."""
        return self.client.post(
            "/api/schedule-blocks/",
            {
                "court": self.court_id,
                "weekday": weekday,
                "open_time": open_time,
                "close_time": close_time,
            },
            content_type="application/json",
            **self.auth_headers,
        )

    # -----------------------------------------------------------------------
    # Caso 8: crear ScheduleBlock válido
    # -----------------------------------------------------------------------

    def test_create_schedule_block_returns_201(self):
        """POST /api/schedule-blocks/ con datos válidos retorna 201."""
        response = self._create_block(weekday=0, open_time="08:00", close_time="12:00")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["court"], self.court_id)
        self.assertEqual(data["weekday"], 0)
        self.assertEqual(data["open_time"], "08:00:00")
        self.assertEqual(data["close_time"], "12:00:00")
        self.assertTrue(data["is_active"])

    # -----------------------------------------------------------------------
    # Caso 9: listar ScheduleBlocks filtrando por court
    # -----------------------------------------------------------------------

    def test_list_schedule_blocks_filter_by_court(self):
        """GET /api/schedule-blocks/?court={id} retorna bloques de esa cancha."""
        self._create_block(weekday=1)
        response = self.client.get(
            f"/api/schedule-blocks/?court={self.court_id}",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", response.json())
        self.assertTrue(len(results) >= 1)
        self.assertTrue(all(b["court"] == self.court_id for b in results))

    # -----------------------------------------------------------------------
    # Caso 10: PATCH ScheduleBlock
    # -----------------------------------------------------------------------

    def test_patch_schedule_block_updates_close_time(self):
        """PATCH /api/schedule-blocks/{id}/ actualiza close_time."""
        create_response = self._create_block(weekday=2, open_time="09:00", close_time="13:00")
        block_id = create_response.json()["id"]

        patch_response = self.client.patch(
            f"/api/schedule-blocks/{block_id}/",
            {"close_time": "14:00:00"},
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(patch_response.status_code, 200, patch_response.content)
        self.assertEqual(patch_response.json()["close_time"], "14:00:00")

    # -----------------------------------------------------------------------
    # Caso 11: DELETE ScheduleBlock → soft-delete
    # -----------------------------------------------------------------------

    def test_delete_schedule_block_sets_is_active_false(self):
        """DELETE /api/schedule-blocks/{id}/ retorna 204 y deja is_active=False en DB."""
        create_response = self._create_block(weekday=3, open_time="10:00", close_time="14:00")
        block_id = create_response.json()["id"]

        delete_response = self.client.delete(
            f"/api/schedule-blocks/{block_id}/",
            **self.auth_headers,
        )
        self.assertEqual(delete_response.status_code, 204)

        block = ScheduleBlock.objects.get(pk=block_id)
        self.assertFalse(block.is_active, "FALLA: is_active sigue True tras DELETE.")
        # El registro DEBE seguir en DB
        self.assertTrue(
            ScheduleBlock.objects.filter(pk=block_id).exists(),
            "FALLA: el registro fue borrado físicamente.",
        )
