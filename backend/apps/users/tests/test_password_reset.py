"""
Tests del flujo de password reset por email.

Endpoints cubiertos:
  POST /api/auth/password-reset/         — solicitar link de reset
  POST /api/auth/password-reset/confirm/ — confirmar con uid+token

Cobertura:
  - Email desconocido siempre retorna 200 (anti-enumeracion).
  - Email conocido retorna 200 y el email se encola en outbox.
  - Token invalido retorna 400 con codigo INVALID_RESET_LINK.
  - Flujo completo: request -> extraer uid+token -> confirm -> login con nueva contrasena.

Notas de implementacion:
  - TenantTestCase: corre dentro del esquema del tenant de prueba (django-tenants).
  - Se usa self.client (DjangoTestClient estandar) con SERVER_NAME=cls.domain.domain
    en lugar de TenantClient, que depende de get_primary_domain() con la conexion
    ya en el esquema del tenant (lo que oculta la tabla domains del public).
  - override_settings(EMAIL_BACKEND=locmem): captura mails sin enviarlos por SMTP.
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import Client, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_tenants.test.cases import TenantTestCase

from apps.users.models import User


RESET_REQUEST_URL = "/api/auth/password-reset/"
RESET_CONFIRM_URL = "/api/auth/password-reset/confirm/"
LOGIN_URL = "/api/auth/login/"


class PasswordResetTestBase(TenantTestCase):
    """
    Clase base para tests de password reset.

    Usa el DjangoTestClient estandar (no TenantClient) con SERVER_NAME
    explicitamente seteado al dominio del tenant creado por TenantTestCase.

    TenantTestCase crea el schema y el dominio en setUpClass(); la conexion
    queda apuntando al schema del tenant. El middleware de django-tenants
    resuelve el tenant por el header HTTP_HOST de la request, que proveemos
    a traves de SERVER_NAME del test client.

    El dominio de prueba de TenantTestCase es 'tenant.test.com' (valor por
    defecto de get_test_tenant_domain()). Este valor ya se agrega a
    ALLOWED_HOSTS via add_allowed_test_domain() en setUpClass.
    """

    def setUp(self):
        super().setUp()
        # Usamos el Django test client estandar con el dominio del tenant
        # como SERVER_NAME para que el middleware resuelva el tenant correcto.
        self.client = Client(SERVER_NAME=self.domain.domain)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetRequest(PasswordResetTestBase):
    """Tests de POST /api/auth/password-reset/."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="jugador@test.localhost",
            password="original123",
            role=User.Role.PLAYER,
        )

    def test_unknown_email_returns_200(self):
        """
        Un email no registrado retorna 200 igualmente.
        Evita que un atacante enumere usuarios por intentos de reset.
        """
        response = self.client.post(
            RESET_REQUEST_URL,
            {"email": "nadie@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("detail", data)

    def test_known_email_returns_200(self):
        """Un email registrado retorna 200 con el mensaje generico."""
        response = self.client.post(
            RESET_REQUEST_URL,
            {"email": "jugador@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("detail", data)

    def test_known_email_sends_one_email(self):
        """Al solicitar reset con email valido se envia exactamente un email."""
        mail.outbox = []
        self.client.post(
            RESET_REQUEST_URL,
            {"email": "jugador@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_known_email_email_contains_reset_link(self):
        """El email enviado contiene un link con uid y token."""
        mail.outbox = []
        self.client.post(
            RESET_REQUEST_URL,
            {"email": "jugador@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("/reset-password/", body)

    def test_unknown_email_sends_no_email(self):
        """Con email desconocido no se envia ningun email."""
        mail.outbox = []
        self.client.post(
            RESET_REQUEST_URL,
            {"email": "nadie@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_format_returns_400(self):
        """Formato de email invalido retorna 400 (validacion de serializer)."""
        response = self.client.post(
            RESET_REQUEST_URL,
            {"email": "no-es-un-email"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_email_field_returns_400(self):
        """Cuerpo vacio retorna 400."""
        response = self.client.post(
            RESET_REQUEST_URL,
            {},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetConfirm(PasswordResetTestBase):
    """Tests de POST /api/auth/password-reset/confirm/."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="jugador@test.localhost",
            password="original123",
            role=User.Role.PLAYER,
        )
        # Generar uid y token validos para los tests
        self.token_gen = PasswordResetTokenGenerator()
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = self.token_gen.make_token(self.user)

    def test_invalid_token_returns_400(self):
        """Token incorrecto retorna 400 con codigo INVALID_RESET_LINK."""
        response = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": "token-invalido-xyz",
                "new_password": "nuevaclave123",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "INVALID_RESET_LINK")

    def test_invalid_uid_returns_400(self):
        """UID malformado retorna 400 con codigo INVALID_RESET_LINK."""
        response = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": "uid-basura",
                "token": self.token,
                "new_password": "nuevaclave123",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "INVALID_RESET_LINK")

    def test_nonexistent_user_uid_returns_400(self):
        """UID de un pk que no existe retorna 400 con codigo INVALID_RESET_LINK."""
        fake_uid = urlsafe_base64_encode(force_bytes(99999))
        response = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": fake_uid,
                "token": self.token,
                "new_password": "nuevaclave123",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "INVALID_RESET_LINK")

    def test_password_too_short_returns_400(self):
        """Nueva contrasena con menos de 8 caracteres retorna 400 (validacion de serializer)."""
        response = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "corta",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_flow_returns_200(self):
        """Flujo valido: uid+token correctos retorna 200."""
        response = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "nuevaclave123",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("detail", data)

    def test_valid_flow_changes_password(self):
        """Tras el confirm exitoso, el usuario puede loguearse con la nueva contrasena."""
        nueva = "nuevaclave123"
        self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": nueva,
            },
            content_type="application/json",
        )

        # Verificar que login con contrasena nueva funciona
        login_response = self.client.post(
            LOGIN_URL,
            {"email": "jugador@test.localhost", "password": nueva},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.json())

    def test_valid_flow_old_password_no_longer_works(self):
        """Tras el confirm exitoso, la contrasena anterior ya no es valida."""
        self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "nuevaclave123",
            },
            content_type="application/json",
        )

        login_response = self.client.post(
            LOGIN_URL,
            {"email": "jugador@test.localhost", "password": "original123"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 401)

    def test_token_cannot_be_reused(self):
        """
        Un token ya consumido no puede usarse por segunda vez.
        Django invalida el token tras el cambio de contrasena porque el hash
        del password (que forma parte del seed del token) cambia.
        """
        payload = {
            "uid": self.uid,
            "token": self.token,
            "new_password": "nuevaclave123",
        }
        first = self.client.post(RESET_CONFIRM_URL, payload, content_type="application/json")
        self.assertEqual(first.status_code, 200)

        # Segundo intento con el mismo token — debe fallar
        second = self.client.post(
            RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "otraclaveXYZ",
            },
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json()["error"]["code"], "INVALID_RESET_LINK")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetEndToEnd(PasswordResetTestBase):
    """
    Flujo end-to-end: request -> extraer uid+token del outbox -> confirm -> login.

    Este test simula exactamente lo que haria el frontend al recibir el email.
    """

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="e2e@test.localhost",
            password="claveoriginal",
            role=User.Role.PLAYER,
        )

    def _extract_uid_token_from_email(self, email_body: str):
        """
        Extrae uid y token del link de reset en el cuerpo del email.

        El link tiene el formato: {FRONTEND_URL}/reset-password/{uid}/{token}/
        """
        for line in email_body.splitlines():
            if "/reset-password/" in line:
                parts = line.strip().split("/reset-password/")[1].rstrip("/").split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]
        raise ValueError("No se encontro el link de reset en el email")

    def test_full_reset_flow(self):
        """
        Flujo completo:
          1. Solicitar reset -> email en outbox.
          2. Extraer uid+token del cuerpo del email.
          3. Confirmar con la nueva contrasena -> 200.
          4. Login con la nueva contrasena -> 200 con tokens JWT.
        """
        mail.outbox = []

        # 1. Solicitar reset
        response = self.client.post(
            RESET_REQUEST_URL,
            {"email": "e2e@test.localhost"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # 2. Extraer uid y token del email
        uid, token = self._extract_uid_token_from_email(mail.outbox[0].body)
        self.assertTrue(uid)
        self.assertTrue(token)

        # 3. Confirmar el reset
        nueva_clave = "claveNueva456"
        confirm_response = self.client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token, "new_password": nueva_clave},
            content_type="application/json",
        )
        self.assertEqual(confirm_response.status_code, 200)

        # 4. Login con la nueva contrasena
        login_response = self.client.post(
            LOGIN_URL,
            {"email": "e2e@test.localhost", "password": nueva_clave},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.json())
        self.assertIn("refresh", login_response.json())
