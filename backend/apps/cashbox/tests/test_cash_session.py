"""
Tests de apertura/cierre de sesión de caja — CashSession

Cobertura:
  1. test_open_cash_session_success       — apertura exitosa, verifica status=OPEN
  2. test_open_cash_session_duplicate     — segunda apertura el mismo día → 400 SESSION_ALREADY_OPEN
  3. test_close_cash_session_success      — cierre exitoso, verifica expected_amount, difference, status=CLOSED
  4. test_close_cash_session_not_open     — cerrar sin haber abierto → 400 SESSION_NOT_OPEN
  5. test_close_cash_session_already_closed — cerrar sesión ya cerrada → 400 SESSION_ALREADY_CLOSED
  6. test_player_cannot_open              — player recibe 403
  7. test_today_endpoint                  — devuelve sesión activa; 404 si no existe
  8. test_tenant_isolation                — sesión de tenant A no visible desde tenant B

Patrón: TenantTestCase + TenantClient (mismo patrón que el resto de tests de Sprint 2/3).
"""

from datetime import date, datetime, timezone as tz
from decimal import Decimal

from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from apps.bookings.models import Booking, CashMovement
from apps.cashbox.models import CashSession
from apps.courts.models import Court
from apps.tenants.models import Domain, Tenant
from apps.users.models import User


class TestCashSessionOpenClose(TenantTestCase):
    """Tests de apertura y cierre de sesión de caja (casos 1-6)."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        # Usuarios
        self.admin = User.objects.create_user(
            email="admin@cashsession.test",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@cashsession.test",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@cashsession.test",
            password="playerpass123",
            role=User.Role.PLAYER,
        )

        # Tokens JWT
        self.admin_token = self._get_token("admin@cashsession.test", "adminpass123")
        self.operator_token = self._get_token("operator@cashsession.test", "oppass123")
        self.player_token = self._get_token("player@cashsession.test", "playerpass123")

        # Fecha de test: usar una fecha futura fija para aislar tests
        # (evita conflictos con "hoy" en BA si se corre el test en producción)
        self.test_date = date(2030, 6, 10)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _get_token(self, email, password):
        response = self.client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(
            response.status_code, 200,
            f"Login falló para {email}: {response.content}",
        )
        return response.json()["access"]

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _open_session(self, token, opening_amount="500.00", session_date=None):
        payload = {"opening_amount": opening_amount}
        if session_date:
            payload["session_date"] = str(session_date)
        return self.client.post(
            "/api/cash-sessions/open/",
            payload,
            content_type="application/json",
            **self._auth(token),
        )

    def _close_session(self, token, closing_amount="500.00", notes="", session_date=None):
        payload = {"closing_amount": closing_amount, "notes": notes}
        if session_date:
            payload["session_date"] = str(session_date)
        return self.client.post(
            "/api/cash-sessions/close/",
            payload,
            content_type="application/json",
            **self._auth(token),
        )

    def _make_cash_movement(self, session_date: date, amount: Decimal):
        """
        Crea un CashMovement en el día indicado para que se incluya
        en el cálculo de expected_amount al cerrar la sesión.
        """
        from datetime import time, timedelta

        # Construir un timestamp dentro del día de session_date a las 12:00 BA
        from zoneinfo import ZoneInfo
        BA = ZoneInfo("America/Argentina/Buenos_Aires")
        dt_ba = datetime.combine(session_date, time(12, 0), tzinfo=BA)
        dt_utc = dt_ba.astimezone(tz.utc)

        # Crear booking ficticio para el CashMovement
        court = Court.objects.create(
            name="Cancha CashSession Test",
            court_type="futbol_5",
            surface="sintético",
            base_price=str(amount),
            slot_duration_minutes=60,
        )
        booking = Booking.objects.create(
            court=court,
            guest_name="Jugador Test Session",
            guest_phone="1122334455",
            start_dt=dt_utc,
            end_dt=dt_utc.replace(hour=dt_utc.hour + 1),
            price=amount,
            status=Booking.Status.CONFIRMED,
        )
        movement = CashMovement(
            booking=booking,
            operator=self.operator,
            amount=amount,
            notes="Movimiento de test",
        )
        movement.save()
        # Forzar created_at dentro del día de session_date
        CashMovement.objects.filter(pk=movement.pk).update(created_at=dt_utc)
        return CashMovement.objects.get(pk=movement.pk)

    # -----------------------------------------------------------------------
    # Caso 1: apertura exitosa
    # -----------------------------------------------------------------------

    def test_open_cash_session_success(self):
        """Apertura exitosa: retorna 201 con status=OPEN y los campos correctos."""
        response = self._open_session(
            self.operator_token,
            opening_amount="1500.00",
            session_date=self.test_date,
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()

        self.assertEqual(data["status"], CashSession.STATUS_OPEN)
        self.assertEqual(Decimal(data["opening_amount"]), Decimal("1500.00"))
        self.assertEqual(data["session_date"], str(self.test_date))
        self.assertIsNotNone(data["opened_at"])
        self.assertIsNone(data["closed_at"])
        self.assertIsNone(data["closing_amount"])
        self.assertIsNone(data["expected_amount"])
        self.assertIsNone(data["difference"])

        # Verificar en DB
        session = CashSession.objects.get(session_date=self.test_date)
        self.assertEqual(session.status, CashSession.STATUS_OPEN)
        self.assertEqual(session.opening_amount, Decimal("1500.00"))
        self.assertTrue(session.is_active)

    # -----------------------------------------------------------------------
    # Caso 2: apertura duplicada el mismo día
    # -----------------------------------------------------------------------

    def test_open_cash_session_duplicate(self):
        """Segunda apertura el mismo día → 400 con código SESSION_ALREADY_OPEN."""
        # Primera apertura: debe tener éxito
        r1 = self._open_session(
            self.operator_token,
            opening_amount="1000.00",
            session_date=self.test_date,
        )
        self.assertEqual(r1.status_code, 201, r1.content)

        # Segunda apertura: debe fallar
        r2 = self._open_session(
            self.operator_token,
            opening_amount="500.00",
            session_date=self.test_date,
        )
        self.assertEqual(r2.status_code, 400, r2.content)
        data = r2.json()
        self.assertEqual(data["error"]["code"], "SESSION_ALREADY_OPEN")

    # -----------------------------------------------------------------------
    # Caso 3: cierre exitoso con cálculo de expected_amount y difference
    # -----------------------------------------------------------------------

    def test_close_cash_session_success(self):
        """
        Cierre exitoso: verifica expected_amount, difference y status=CLOSED.

        Escenario:
          opening_amount = 1000.00
          CashMovement del día = 2500.00
          expected_amount = 1000.00 + 2500.00 = 3500.00
          closing_amount = 3200.00 (cajero contó menos)
          difference = 3200.00 - 3500.00 = -300.00 (faltante)
        """
        opening = Decimal("1000.00")
        movement_amount = Decimal("2500.00")
        closing = Decimal("3200.00")

        # Abrir sesión
        r_open = self._open_session(
            self.operator_token,
            opening_amount=str(opening),
            session_date=self.test_date,
        )
        self.assertEqual(r_open.status_code, 201, r_open.content)

        # Crear un movimiento de caja en el día de test
        self._make_cash_movement(self.test_date, movement_amount)

        # Cerrar sesión
        r_close = self._close_session(
            self.operator_token,
            closing_amount=str(closing),
            notes="Diferencia por billete mal contado.",
            session_date=self.test_date,
        )
        self.assertEqual(r_close.status_code, 200, r_close.content)
        data = r_close.json()

        expected = opening + movement_amount
        difference = closing - expected

        self.assertEqual(data["status"], CashSession.STATUS_CLOSED)
        self.assertEqual(Decimal(data["closing_amount"]), closing)
        self.assertEqual(Decimal(data["expected_amount"]), expected)
        self.assertEqual(Decimal(data["difference"]), difference)
        self.assertEqual(data["notes"], "Diferencia por billete mal contado.")
        self.assertIsNotNone(data["closed_at"])

    # -----------------------------------------------------------------------
    # Caso 4: cerrar sin haber abierto
    # -----------------------------------------------------------------------

    def test_close_cash_session_not_open(self):
        """Cerrar sin haber abierto → 400 con código SESSION_NOT_OPEN."""
        # Fecha sin sesión existente
        no_session_date = date(2030, 12, 31)
        response = self._close_session(
            self.operator_token,
            closing_amount="500.00",
            session_date=no_session_date,
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "SESSION_NOT_OPEN")

    # -----------------------------------------------------------------------
    # Caso 5: cerrar sesión ya cerrada
    # -----------------------------------------------------------------------

    def test_close_cash_session_already_closed(self):
        """Cerrar una sesión ya CLOSED → 400 con código SESSION_ALREADY_CLOSED."""
        already_closed_date = date(2030, 7, 15)

        # Abrir y cerrar
        self._open_session(
            self.operator_token,
            opening_amount="500.00",
            session_date=already_closed_date,
        )
        r_close1 = self._close_session(
            self.operator_token,
            closing_amount="500.00",
            session_date=already_closed_date,
        )
        self.assertEqual(r_close1.status_code, 200, r_close1.content)

        # Intentar cerrar de nuevo
        r_close2 = self._close_session(
            self.operator_token,
            closing_amount="500.00",
            session_date=already_closed_date,
        )
        self.assertEqual(r_close2.status_code, 400, r_close2.content)
        data = r_close2.json()
        self.assertEqual(data["error"]["code"], "SESSION_ALREADY_CLOSED")

    # -----------------------------------------------------------------------
    # Caso 6: player no puede abrir caja
    # -----------------------------------------------------------------------

    def test_player_cannot_open(self):
        """Player recibe 403 al intentar abrir la sesión de caja."""
        response = self._open_session(
            self.player_token,
            opening_amount="500.00",
            session_date=self.test_date,
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_player_cannot_close(self):
        """Player recibe 403 al intentar cerrar la sesión de caja."""
        response = self._close_session(
            self.player_token,
            closing_amount="500.00",
            session_date=self.test_date,
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_player_cannot_list(self):
        """Player recibe 403 al intentar listar sesiones de caja."""
        response = self.client.get(
            "/api/cash-sessions/",
            **self._auth(self.player_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_unauthenticated_cannot_open(self):
        """Sin JWT → 401."""
        response = self.client.post(
            "/api/cash-sessions/open/",
            {"opening_amount": "500.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401, response.content)


class TestCashSessionTodayEndpoint(TenantTestCase):
    """Tests del endpoint GET /api/cash-sessions/today/ (caso 7)."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.operator = User.objects.create_user(
            email="op@today.test",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": "op@today.test", "password": "oppass123"},
            content_type="application/json",
        )
        self.token = login.json()["access"]

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_today_endpoint_returns_404_when_no_session(self):
        """
        GET /api/cash-sessions/today/ devuelve 404 cuando no hay sesión
        para el día actual en BA.
        """
        # Asegurarse de que no existe sesión para hoy
        from apps.cashbox.services import _today_ba
        today = _today_ba()
        CashSession.objects.filter(session_date=today, is_active=True).delete()

        response = self.client.get(
            "/api/cash-sessions/today/",
            **self._auth(self.token),
        )
        self.assertEqual(response.status_code, 404, response.content)
        data = response.json()
        self.assertEqual(data["error"]["code"], "SESSION_NOT_FOUND")

    def test_today_endpoint_returns_session_when_open(self):
        """
        GET /api/cash-sessions/today/ devuelve la sesión abierta del día actual.
        """
        from apps.cashbox.services import _today_ba, open_cash_session
        today = _today_ba()

        # Limpiar sesión previa si existe
        CashSession.objects.filter(session_date=today, is_active=True).delete()

        # Abrir sesión para hoy
        session = open_cash_session(
            operator=self.operator,
            opening_amount=Decimal("800.00"),
            session_date=today,
        )

        response = self.client.get(
            "/api/cash-sessions/today/",
            **self._auth(self.token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["id"], session.pk)
        self.assertEqual(data["status"], CashSession.STATUS_OPEN)
        self.assertEqual(data["session_date"], str(today))


class TestCashSessionTenantIsolation(TenantTestCase):
    """
    Test de aislamiento multi-tenant: sesión de tenant A no visible desde tenant B.
    (caso 8)
    """

    TENANT_B_SCHEMA = "test_cashsession_tenant_b"
    TENANT_B_DOMAIN = "cashsession-b.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from django.conf import settings as django_settings
        if cls.TENANT_B_DOMAIN not in django_settings.ALLOWED_HOSTS:
            django_settings.ALLOWED_HOSTS += [cls.TENANT_B_DOMAIN]

        connection.set_schema_to_public()
        cls.tenant_b = Tenant(
            schema_name=cls.TENANT_B_SCHEMA,
            name="Complejo B (CashSession test)",
        )
        cls.tenant_b.save()
        Domain.objects.create(
            domain=cls.TENANT_B_DOMAIN,
            tenant=cls.tenant_b,
            is_primary=True,
        )
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        try:
            Domain.objects.filter(tenant=cls.tenant_b).delete()
            cls.tenant_b.delete(force_drop=True)
        except Exception:
            pass
        from django.conf import settings as django_settings
        if cls.TENANT_B_DOMAIN in django_settings.ALLOWED_HOSTS:
            django_settings.ALLOWED_HOSTS.remove(cls.TENANT_B_DOMAIN)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.tenant)

        self.client_a = TenantClient(self.tenant)
        self.client_b = TenantClient(self.tenant_b)

        # Operador en tenant A
        self.op_a = User.objects.create_user(
            email="op@cs-a.test",
            password="pass123",
            role=User.Role.OPERATOR,
        )
        login_a = self.client_a.post(
            "/api/auth/login/",
            {"email": "op@cs-a.test", "password": "pass123"},
            content_type="application/json",
        )
        self.token_a = login_a.json()["access"]

        # Operador en tenant B
        with schema_context(self.TENANT_B_SCHEMA):
            self.op_b = User.objects.create_user(
                email="op@cs-b.test",
                password="pass123",
                role=User.Role.OPERATOR,
            )
        login_b = self.client_b.post(
            "/api/auth/login/",
            {"email": "op@cs-b.test", "password": "pass123"},
            content_type="application/json",
        )
        self.token_b = login_b.json()["access"]

        # Restaurar al esquema de tenant_a
        connection.set_tenant(self.tenant)

    def test_tenant_isolation_orm(self):
        """
        CashSession creada en tenant A no es visible desde tenant B vía ORM.
        """
        session_date = date(2030, 8, 20)

        # Crear sesión en tenant A
        CashSession.objects.create(
            operator=self.op_a,
            session_date=session_date,
            opened_at=datetime.now(tz=tz.utc),
            opening_amount=Decimal("1000.00"),
            status=CashSession.STATUS_OPEN,
        )

        # Verificar que existe en tenant A
        self.assertTrue(
            CashSession.objects.filter(session_date=session_date).exists(),
            "La sesión debe existir en tenant A.",
        )

        # Verificar que NO existe en tenant B
        with schema_context(self.TENANT_B_SCHEMA):
            exists_in_b = CashSession.objects.filter(session_date=session_date).exists()

        self.assertFalse(
            exists_in_b,
            "FALLA: CashSession de tenant A visible en tenant B.",
        )

    def test_tenant_isolation_api(self):
        """
        Tenant B no puede ver las sesiones de tenant A vía API.
        El listado de tenant B debe estar vacío cuando tenant A tiene sesiones.
        """
        session_date = date(2030, 9, 10)

        # Crear sesión en tenant A
        connection.set_tenant(self.tenant)
        r_open = self.client_a.post(
            "/api/cash-sessions/open/",
            {"opening_amount": "500.00", "session_date": str(session_date)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(r_open.status_code, 201, r_open.content)

        # Restaurar esquema de tenant_a
        connection.set_tenant(self.tenant)

        # Tenant B lista sus sesiones: no debe ver la de tenant A
        r_list = self.client_b.get(
            "/api/cash-sessions/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
        )
        self.assertEqual(r_list.status_code, 200, r_list.content)

        sessions_b = r_list.json()
        if isinstance(sessions_b, dict):
            # Paginado
            results = sessions_b.get("results", [])
        else:
            results = sessions_b

        # Ninguna sesión de tenant B debe tener session_date = session_date de tenant A
        dates_in_b = [s["session_date"] for s in results]
        self.assertNotIn(
            str(session_date),
            dates_in_b,
            "FALLA: sesión de tenant A visible desde tenant B vía API.",
        )
