"""
Tests de lógica de negocio de ScheduleBlock — Sprint 1

Cobertura (services.py):
  1. Crear bloque válido → 201, bloque en DB.
  2. open_time >= close_time rechazado → 400 con código INVALID_SCHEDULE.
  3. open_time == close_time rechazado → 400 con código INVALID_SCHEDULE.
  4. Solapamiento total con bloque activo → 400 con código SCHEDULE_OVERLAP.
  5. Solapamiento parcial izquierdo → 400 SCHEDULE_OVERLAP.
  6. Solapamiento parcial derecho → 400 SCHEDULE_OVERLAP.
  7. Turno partido (dos bloques no solapados en el mismo día) → ambos 201.
  8. Bloque adyacente (close_a == open_b) → NO solapamiento → 201.
  9. Editar bloque excluyendo su propio id → no se auto-rechaza → 200.
 10. Editar bloque generando solapamiento con OTRO bloque → 400 SCHEDULE_OVERLAP.
 11. Bloque inactivo no interfiere en la validación de solapamiento.

Patrón: TenantTestCase + TenantClient.
"""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.users.models import User


class TestScheduleBlockValidation(TenantTestCase):
    """Tests de validaciones de negocio de ScheduleBlock."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@sb-val.localhost",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@sb-val.localhost", "password": "adminpass123"},
            content_type="application/json",
        )
        self.token = response.json()["access"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Crear cancha base
        court_resp = self.client.post(
            "/api/courts/",
            {
                "name": "Cancha Validacion",
                "court_type": "futbol_5",
                "surface": "",
                "base_price": "3000.00",
                "slot_duration_minutes": 60,
            },
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(court_resp.status_code, 201, court_resp.content)
        self.court_id = court_resp.json()["id"]

    def _create_block(self, open_time, close_time, weekday=0):
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
    # Caso 1: bloque válido
    # -----------------------------------------------------------------------

    def test_valid_block_creates_successfully(self):
        """Bloque con open < close se crea correctamente."""
        response = self._create_block("08:00", "12:00")
        self.assertEqual(response.status_code, 201, response.content)

    # -----------------------------------------------------------------------
    # Caso 2: open_time > close_time → INVALID_SCHEDULE
    # -----------------------------------------------------------------------

    def test_open_greater_than_close_returns_invalid_schedule(self):
        """open_time > close_time → 400 con INVALID_SCHEDULE."""
        response = self._create_block("14:00", "08:00")
        self.assertEqual(response.status_code, 400, response.content)
        self._assert_error_code(response, "INVALID_SCHEDULE")

    # -----------------------------------------------------------------------
    # Caso 3: open_time == close_time → INVALID_SCHEDULE
    # -----------------------------------------------------------------------

    def test_open_equals_close_returns_invalid_schedule(self):
        """open_time == close_time → 400 con INVALID_SCHEDULE."""
        response = self._create_block("10:00", "10:00")
        self.assertEqual(response.status_code, 400, response.content)
        self._assert_error_code(response, "INVALID_SCHEDULE")

    # -----------------------------------------------------------------------
    # Caso 4: solapamiento total → SCHEDULE_OVERLAP
    # -----------------------------------------------------------------------

    def test_total_overlap_returns_schedule_overlap(self):
        """Bloque idéntico al existente → 400 SCHEDULE_OVERLAP."""
        self._create_block("08:00", "12:00")
        response = self._create_block("08:00", "12:00")
        self.assertEqual(response.status_code, 400, response.content)
        self._assert_error_code(response, "SCHEDULE_OVERLAP")

    # -----------------------------------------------------------------------
    # Caso 5: solapamiento parcial izquierdo → SCHEDULE_OVERLAP
    # -----------------------------------------------------------------------

    def test_left_partial_overlap_returns_schedule_overlap(self):
        """Nuevo bloque empieza antes y termina dentro del existente."""
        self._create_block("10:00", "14:00")
        # Nuevo: 08:00-11:00 solapa con 10:00-14:00
        response = self._create_block("08:00", "11:00")
        self.assertEqual(response.status_code, 400, response.content)
        self._assert_error_code(response, "SCHEDULE_OVERLAP")

    # -----------------------------------------------------------------------
    # Caso 6: solapamiento parcial derecho → SCHEDULE_OVERLAP
    # -----------------------------------------------------------------------

    def test_right_partial_overlap_returns_schedule_overlap(self):
        """Nuevo bloque empieza dentro del existente y termina después."""
        self._create_block("08:00", "12:00")
        # Nuevo: 11:00-15:00 solapa con 08:00-12:00
        response = self._create_block("11:00", "15:00")
        self.assertEqual(response.status_code, 400, response.content)
        self._assert_error_code(response, "SCHEDULE_OVERLAP")

    # -----------------------------------------------------------------------
    # Caso 7: turno partido (no solapado) → ambos 201
    # -----------------------------------------------------------------------

    def test_split_shift_no_overlap_both_accepted(self):
        """Dos bloques no solapados en el mismo día → ambos 201."""
        r1 = self._create_block("08:00", "12:00", weekday=1)
        r2 = self._create_block("16:00", "22:00", weekday=1)
        self.assertEqual(r1.status_code, 201, r1.content)
        self.assertEqual(r2.status_code, 201, r2.content)

    # -----------------------------------------------------------------------
    # Caso 8: bloques adyacentes (close_a == open_b) → NO solapamiento → 201
    # -----------------------------------------------------------------------

    def test_adjacent_blocks_not_overlap(self):
        """close_a == open_b es adyacente, NO solapamiento: el segundo se acepta."""
        # Bloque A: 08:00-12:00. Bloque B: 12:00-16:00. No se solapan.
        r1 = self._create_block("08:00", "12:00", weekday=2)
        r2 = self._create_block("12:00", "16:00", weekday=2)
        self.assertEqual(r1.status_code, 201, r1.content)
        self.assertEqual(r2.status_code, 201, r2.content)

    # -----------------------------------------------------------------------
    # Caso 9: editar bloque excluyendo su propio id (no se auto-rechaza)
    # -----------------------------------------------------------------------

    def test_edit_block_does_not_reject_itself(self):
        """PATCH sobre el mismo bloque con los mismos tiempos → 200 (no SCHEDULE_OVERLAP)."""
        create_resp = self._create_block("09:00", "13:00", weekday=3)
        block_id = create_resp.json()["id"]

        # Editar solo close_time sin crear solapamiento
        patch_resp = self.client.patch(
            f"/api/schedule-blocks/{block_id}/",
            {"close_time": "14:00:00"},
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(patch_resp.status_code, 200, patch_resp.content)

    # -----------------------------------------------------------------------
    # Caso 10: editar bloque generando solapamiento con OTRO bloque → 400
    # -----------------------------------------------------------------------

    def test_edit_block_overlapping_another_returns_400(self):
        """PATCH que genera solapamiento con otro bloque activo → 400 SCHEDULE_OVERLAP."""
        # Bloque A: 08:00-12:00
        self._create_block("08:00", "12:00", weekday=4)
        # Bloque B: 14:00-18:00
        create_b = self._create_block("14:00", "18:00", weekday=4)
        block_b_id = create_b.json()["id"]

        # Intentar mover el inicio de B a 11:00 (solaparía con A hasta las 12:00)
        patch_resp = self.client.patch(
            f"/api/schedule-blocks/{block_b_id}/",
            {"open_time": "11:00:00"},
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(patch_resp.status_code, 400, patch_resp.content)
        self._assert_error_code(patch_resp, "SCHEDULE_OVERLAP")

    # -----------------------------------------------------------------------
    # Caso 11: bloque inactivo no bloquea la creación de uno nuevo
    # -----------------------------------------------------------------------

    def test_inactive_block_does_not_block_new_block(self):
        """Un bloque dado de baja no interfiere en la validación de solapamiento."""
        create_resp = self._create_block("08:00", "12:00", weekday=5)
        block_id = create_resp.json()["id"]

        # Dar de baja el bloque
        delete_resp = self.client.delete(
            f"/api/schedule-blocks/{block_id}/",
            **self.auth_headers,
        )
        self.assertEqual(delete_resp.status_code, 204)

        # Crear otro bloque idéntico → debe aceptarse porque el anterior está inactivo
        response = self._create_block("08:00", "12:00", weekday=5)
        self.assertEqual(response.status_code, 201, response.content)

    # -----------------------------------------------------------------------
    # Helper
    # -----------------------------------------------------------------------

    def _assert_error_code(self, response, expected_code):
        """Verifica que la respuesta contiene el código de negocio esperado."""
        data = response.json()
        # El error puede venir en non_field_errors (list de dicts con 'code')
        # o en el campo directamente
        found = False
        # Buscar recursivamente el código en la respuesta
        found = self._find_code(data, expected_code)
        self.assertTrue(
            found,
            f"Código '{expected_code}' no encontrado en la respuesta: {data}",
        )

    def _find_code(self, obj, code):
        """Busca recursivamente un dict con key 'code' == code."""
        if isinstance(obj, dict):
            if obj.get("code") == code:
                return True
            return any(self._find_code(v, code) for v in obj.values())
        if isinstance(obj, list):
            return any(self._find_code(item, code) for item in obj)
        return False
