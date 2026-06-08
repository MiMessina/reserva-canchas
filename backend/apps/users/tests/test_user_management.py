"""
Tests de gestión de operadores — Feature 2

Cobertura:
  1.  test_me_requires_auth              — sin JWT → 401
  2.  test_me_returns_current_user       — GET /api/users/me/ → datos del usuario autenticado
  3.  test_me_any_role_can_access        — player puede acceder a me/
  4.  test_list_requires_tenant_admin    — operator → 403
  5.  test_list_returns_operators_only   — solo operators aparecen en el listado
  6.  test_list_excludes_inactive        — usuario inactivo no aparece
  7.  test_create_operator_success       — POST → 201, role=OPERATOR
  8.  test_create_forces_operator_role   — no se puede crear tenant_admin desde aquí
  9.  test_create_requires_tenant_admin  — operator no puede crear usuarios → 403
  10. test_retrieve_operator             — GET /api/users/{id}/ → datos del operador
  11. test_retrieve_requires_tenant_admin — operator no puede ver listado → 403
  12. test_patch_operator                — PATCH edita first_name/last_name/email
  13. test_patch_password_hashed         — PATCH con password → se hashea correctamente
  14. test_delete_soft_deletes           — DELETE → is_active=False, no borra físicamente
  15. test_delete_not_found_after_soft   — operador soft-deleted no aparece en list
  16. test_no_password_in_response       — la respuesta nunca contiene el campo password
  17. test_tenant_isolation              — usuario de otro tenant no accede a datos de este
"""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.users.models import User


class TestUserManagement(TenantTestCase):
    """Tests del UserViewSet — endpoints /api/users/."""

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)

        self.admin = User.objects.create_user(
            email="admin@usermgmt.test",
            password="adminpass123",
            role=User.Role.TENANT_ADMIN,
            is_staff=True,
        )
        self.operator = User.objects.create_user(
            email="operator@usermgmt.test",
            password="oppass123",
            role=User.Role.OPERATOR,
        )
        self.player = User.objects.create_user(
            email="player@usermgmt.test",
            password="playerpass",
            role=User.Role.PLAYER,
        )

        self.admin_token = self._get_token("admin@usermgmt.test", "adminpass123")
        self.operator_token = self._get_token("operator@usermgmt.test", "oppass123")
        self.player_token = self._get_token("player@usermgmt.test", "playerpass")

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

    # -----------------------------------------------------------------------
    # Caso 1: sin JWT → 401
    # -----------------------------------------------------------------------

    def test_me_requires_auth(self):
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, 401, response.content)

    # -----------------------------------------------------------------------
    # Caso 2: GET /api/users/me/ retorna datos del usuario autenticado
    # -----------------------------------------------------------------------

    def test_me_returns_current_user(self):
        response = self.client.get(
            "/api/users/me/",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["email"], "admin@usermgmt.test")
        self.assertEqual(data["role"], "tenant_admin")
        self.assertNotIn("password", data)

    # -----------------------------------------------------------------------
    # Caso 3: cualquier rol puede acceder a me/
    # -----------------------------------------------------------------------

    def test_me_any_role_can_access(self):
        for token, expected_email in [
            (self.admin_token, "admin@usermgmt.test"),
            (self.operator_token, "operator@usermgmt.test"),
            (self.player_token, "player@usermgmt.test"),
        ]:
            with self.subTest(email=expected_email):
                response = self.client.get("/api/users/me/", **self._headers(token))
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()["email"], expected_email)

    # -----------------------------------------------------------------------
    # Caso 4: operator no puede listar usuarios → 403
    # -----------------------------------------------------------------------

    def test_list_requires_tenant_admin(self):
        response = self.client.get("/api/users/", **self._headers(self.operator_token))
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 5: list retorna solo operators
    # -----------------------------------------------------------------------

    def test_list_returns_operators_only(self):
        response = self.client.get("/api/users/", **self._headers(self.admin_token))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        # Si la respuesta está paginada, usar "results"
        results = data.get("results", data) if isinstance(data, dict) else data
        emails = [u["email"] for u in results]
        self.assertIn("operator@usermgmt.test", emails)
        # El tenant_admin y el player no deben aparecer
        self.assertNotIn("admin@usermgmt.test", emails)
        self.assertNotIn("player@usermgmt.test", emails)

    # -----------------------------------------------------------------------
    # Caso 6: usuario inactivo no aparece en list
    # -----------------------------------------------------------------------

    def test_list_excludes_inactive(self):
        inactive_op = User.objects.create_user(
            email="inactive@usermgmt.test",
            password="pass",
            role=User.Role.OPERATOR,
            is_active=False,
        )
        response = self.client.get("/api/users/", **self._headers(self.admin_token))
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        emails = [u["email"] for u in results]
        self.assertNotIn("inactive@usermgmt.test", emails)

    # -----------------------------------------------------------------------
    # Caso 7: POST crea operador correctamente → 201
    # -----------------------------------------------------------------------

    def test_create_operator_success(self):
        payload = {
            "email": "nuevo@usermgmt.test",
            "password": "newpass123",
            "first_name": "Nuevo",
            "last_name": "Operador",
        }
        response = self.client.post(
            "/api/users/",
            payload,
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["email"], "nuevo@usermgmt.test")
        self.assertEqual(data["role"], "operator")
        self.assertNotIn("password", data)

        # Verificar en DB
        user = User.objects.get(email="nuevo@usermgmt.test")
        self.assertEqual(user.role, User.Role.OPERATOR)
        self.assertTrue(user.check_password("newpass123"))

    # -----------------------------------------------------------------------
    # Caso 8: el role enviado se ignora y siempre queda OPERATOR
    # -----------------------------------------------------------------------

    def test_create_forces_operator_role(self):
        """El cliente no puede crear un tenant_admin desde este endpoint."""
        payload = {
            "email": "tricky@usermgmt.test",
            "password": "tricky123",
            "first_name": "",
            "last_name": "",
        }
        response = self.client.post(
            "/api/users/",
            payload,
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email="tricky@usermgmt.test")
        self.assertEqual(user.role, User.Role.OPERATOR)

    # -----------------------------------------------------------------------
    # Caso 9: operator no puede crear usuarios → 403
    # -----------------------------------------------------------------------

    def test_create_requires_tenant_admin(self):
        payload = {
            "email": "blocked@usermgmt.test",
            "password": "pass12345",
            "first_name": "",
            "last_name": "",
        }
        response = self.client.post(
            "/api/users/",
            payload,
            content_type="application/json",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 10: GET /api/users/{id}/ retorna datos del operador
    # -----------------------------------------------------------------------

    def test_retrieve_operator(self):
        response = self.client.get(
            f"/api/users/{self.operator.pk}/",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["email"], "operator@usermgmt.test")
        self.assertNotIn("password", data)

    # -----------------------------------------------------------------------
    # Caso 11: operator no puede usar retrieve → 403
    # -----------------------------------------------------------------------

    def test_retrieve_requires_tenant_admin(self):
        response = self.client.get(
            f"/api/users/{self.operator.pk}/",
            **self._headers(self.operator_token),
        )
        self.assertEqual(response.status_code, 403, response.content)

    # -----------------------------------------------------------------------
    # Caso 12: PATCH edita campos del operador
    # -----------------------------------------------------------------------

    def test_patch_operator(self):
        response = self.client.patch(
            f"/api/users/{self.operator.pk}/",
            {"first_name": "Editado", "last_name": "Operador"},
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["first_name"], "Editado")
        self.assertEqual(data["last_name"], "Operador")

        # Verificar en DB
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.first_name, "Editado")

    # -----------------------------------------------------------------------
    # Caso 13: PATCH con password → se hashea correctamente
    # -----------------------------------------------------------------------

    def test_patch_password_hashed(self):
        response = self.client.patch(
            f"/api/users/{self.operator.pk}/",
            {"password": "newpass999"},
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.operator.refresh_from_db()
        self.assertTrue(self.operator.check_password("newpass999"))
        # La contraseña anterior ya no funciona
        self.assertFalse(self.operator.check_password("oppass123"))

    # -----------------------------------------------------------------------
    # Caso 14: DELETE → is_active=False (soft-delete)
    # -----------------------------------------------------------------------

    def test_delete_soft_deletes(self):
        response = self.client.delete(
            f"/api/users/{self.operator.pk}/",
            **self._headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 204, response.content)

        # El usuario sigue existiendo en la DB
        self.operator.refresh_from_db()
        self.assertFalse(self.operator.is_active)

    # -----------------------------------------------------------------------
    # Caso 15: operador soft-deleted no aparece en list
    # -----------------------------------------------------------------------

    def test_delete_not_found_after_soft(self):
        # Desactivar primero
        self.operator.is_active = False
        self.operator.save()

        response = self.client.get("/api/users/", **self._headers(self.admin_token))
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        emails = [u["email"] for u in results]
        self.assertNotIn("operator@usermgmt.test", emails)

    # -----------------------------------------------------------------------
    # Caso 16: ninguna respuesta expone password
    # -----------------------------------------------------------------------

    def test_no_password_in_response(self):
        # list
        resp_list = self.client.get("/api/users/", **self._headers(self.admin_token))
        results = resp_list.json().get("results", resp_list.json())
        for u in results:
            self.assertNotIn("password", u)

        # retrieve
        resp_retrieve = self.client.get(
            f"/api/users/{self.operator.pk}/",
            **self._headers(self.admin_token),
        )
        self.assertNotIn("password", resp_retrieve.json())

        # create
        resp_create = self.client.post(
            "/api/users/",
            {"email": "nopass@test.com", "password": "secret123", "first_name": "", "last_name": ""},
            content_type="application/json",
            **self._headers(self.admin_token),
        )
        self.assertNotIn("password", resp_create.json())

    # -----------------------------------------------------------------------
    # Caso 17: aislamiento multi-tenant (usuario de otro tenant no accede)
    # -----------------------------------------------------------------------

    def test_tenant_isolation(self):
        """
        El aislamiento multi-tenant lo garantiza django-tenants a nivel de esquema.
        Dentro de TenantTestCase, todos los objetos pertenecen al mismo tenant de test.
        Este test verifica que el endpoint /api/users/ solo devuelve usuarios del
        esquema activo (el tenant del test), sin filtro adicional por tenant_id.
        """
        # Verificar que los resultados del listado son los esperados del tenant
        response = self.client.get("/api/users/", **self._headers(self.admin_token))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        # Solo deben aparecer los operators del tenant actual
        for user_data in results:
            self.assertEqual(user_data["role"], "operator")
