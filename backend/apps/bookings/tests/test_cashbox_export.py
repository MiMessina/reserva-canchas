"""
Tests de exportación CSV de caja — Feature 1

Cobertura:
  1. test_export_requires_auth          — sin JWT → 401
  2. test_export_requires_operator_role — player → 403
  3. test_export_returns_csv            — operator → 200 con Content-Type text/csv
  4. test_export_csv_columns            — CSV contiene las columnas esperadas
  5. test_export_csv_row_data           — los datos del movimiento están en el CSV
  6. test_export_filter_by_date         — ?date= filtra correctamente
  7. test_export_invalid_date           — ?date=bad → 400
  8. test_export_negative_amount_is_devolucion — amount < 0 → tipo "Devolucion"
  9. test_export_guest_name_used_when_present — guest_name aparece en columna Jugador
  10. test_export_user_email_fallback    — sin guest_name usa email del user
"""

import csv
import io
from datetime import datetime, timezone as tz

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock
from apps.users.models import User


class TestCashboxExport(TenantTestCase):
    """Tests de exportación CSV del endpoint GET /api/cash-movements/export/."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="operator@export.test",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@export.test",
            password="playerpass",
            role=User.Role.PLAYER,
        )

        self.operator_token = self._get_token("operator@export.test", "oppass123")

        self.court = Court.objects.create(
            name="Cancha Export",
            court_type="futbol_5",
            surface="sintetico",
            base_price="4000.00",
            slot_duration_minutes=60,
        )

        # Reserva con invitado (guest_name)
        self.booking_guest = Booking.objects.create(
            court=self.court,
            guest_name="Carlos Invitado",
            guest_phone="1234567890",
            start_dt=datetime(2026, 6, 8, 14, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 15, 0, tzinfo=tz.utc),
            status=Booking.Status.CONFIRMED,
            price="4000.00",
        )

        # Movimiento de caja asociado
        self.movement = CashMovement.objects.create(
            booking=self.booking_guest,
            operator=self.operator,
            amount="4000.00",
            notes="Seña por transferencia",
        )

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

    def _parse_csv(self, response_content):
        """Parsea el contenido de la respuesta CSV (skipea el BOM si existe)."""
        content = response_content
        # Decodificar si es bytes
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        return list(csv.reader(io.StringIO(content)))

    # -----------------------------------------------------------------------
    # Caso 1: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_export_requires_auth(self):
        response = self.client.get("/api/cash-movements/export/")
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 2: player → 403
    # -----------------------------------------------------------------------

    def test_export_requires_operator_role(self):
        player_token = self._get_token("player@export.test", "playerpass")
        response = self.client.get(
            "/api/cash-movements/export/",
            **self._headers(player_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 3: operator → 200, Content-Type text/csv
    # -----------------------------------------------------------------------

    def test_export_returns_csv(self):
        response = self.client.get(
            "/api/cash-movements/export/",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])

    # -----------------------------------------------------------------------
    # Caso 4: CSV contiene columnas esperadas
    # -----------------------------------------------------------------------

    def test_export_csv_columns(self):
        response = self.client.get(
            "/api/cash-movements/export/",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        self.assertGreater(len(rows), 0, "El CSV no tiene contenido")
        header = rows[0]
        self.assertEqual(header, ["Fecha", "Cancha", "Jugador", "Monto", "Tipo", "Notas"])

    # -----------------------------------------------------------------------
    # Caso 5: los datos del movimiento están en el CSV
    # -----------------------------------------------------------------------

    def test_export_csv_row_data(self):
        # Filtrar por la fecha del movimiento para garantizar que aparece
        response = self.client.get(
            "/api/cash-movements/export/?date=2026-06-08",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        # rows[0] es el header; rows[1] es el primer movimiento
        self.assertGreater(len(rows), 1, "Se esperaba al menos un movimiento en el CSV")
        data_row = rows[1]

        cancha = data_row[1]
        jugador = data_row[2]
        tipo = data_row[4]
        notas = data_row[5]

        self.assertEqual(cancha, "Cancha Export")
        self.assertEqual(jugador, "Carlos Invitado")
        self.assertEqual(tipo, "Ingreso")
        self.assertEqual(notas, "Seña por transferencia")
        # El monto debe tener formato $X,XX
        self.assertTrue(data_row[3].startswith("$"), f"Monto sin formato: {data_row[3]}")

    # -----------------------------------------------------------------------
    # Caso 6: ?date filtra correctamente
    # -----------------------------------------------------------------------

    def test_export_filter_by_date(self):
        # Consultar una fecha sin movimientos
        response = self.client.get(
            "/api/cash-movements/export/?date=2025-01-01",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        # Solo el header, sin filas de datos
        self.assertEqual(len(rows), 1, "No debería haber movimientos para 2025-01-01")

    # -----------------------------------------------------------------------
    # Caso 7: date inválida → 400
    # -----------------------------------------------------------------------

    def test_export_invalid_date(self):
        response = self.client.get(
            "/api/cash-movements/export/?date=not-a-date",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    # -----------------------------------------------------------------------
    # Caso 8: amount negativo → tipo "Devolucion"
    # -----------------------------------------------------------------------

    def test_export_negative_amount_is_devolucion(self):
        # Crear un movimiento negativo (devolución)
        booking_dev = Booking.objects.create(
            court=self.court,
            guest_name="Devuelto",
            guest_phone="9999",
            start_dt=datetime(2026, 6, 8, 16, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 17, 0, tzinfo=tz.utc),
            status=Booking.Status.CANCELLED,
            price="4000.00",
        )
        CashMovement.objects.create(
            booking=booking_dev,
            operator=self.operator,
            amount="-4000.00",
            notes="Devolucion por cancelacion",
        )

        response = self.client.get(
            "/api/cash-movements/export/?date=2026-06-08",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        # Buscar la fila de la devolución
        devolucion_rows = [r for r in rows[1:] if r[4] == "Devolucion"]
        self.assertGreater(len(devolucion_rows), 0, "No se encontro fila de Devolucion")

    # -----------------------------------------------------------------------
    # Caso 9: guest_name aparece como Jugador cuando está presente
    # -----------------------------------------------------------------------

    def test_export_guest_name_used_when_present(self):
        response = self.client.get(
            "/api/cash-movements/export/?date=2026-06-08",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        jugador_col = [r[2] for r in rows[1:]]
        self.assertIn("Carlos Invitado", jugador_col)

    # -----------------------------------------------------------------------
    # Caso 10: sin guest_name usa email del user
    # -----------------------------------------------------------------------

    def test_export_user_email_fallback(self):
        # Crear reserva vinculada a un usuario registrado (sin guest_name)
        booking_user = Booking.objects.create(
            court=self.court,
            user=self.player,
            guest_name="",
            guest_phone="",
            start_dt=datetime(2026, 6, 8, 12, 0, tzinfo=tz.utc),
            end_dt=datetime(2026, 6, 8, 13, 0, tzinfo=tz.utc),
            status=Booking.Status.CONFIRMED,
            price="4000.00",
        )
        CashMovement.objects.create(
            booking=booking_user,
            operator=self.operator,
            amount="4000.00",
            notes="",
        )

        response = self.client.get(
            "/api/cash-movements/export/?date=2026-06-08",
            **self._headers(self.operator_token),
        )
        rows = self._parse_csv(response.content)
        jugador_col = [r[2] for r in rows[1:]]
        self.assertIn("player@export.test", jugador_col)
