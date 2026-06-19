"""
Backend de autenticacion JWT para el Panel de System Admin (ADR-013).

El platform admin es un PlatformAdmin (apps.tenants, SHARED_APPS, esquema public).
PlatformAdmin es independiente de users.User y auth.User.

PlatformJWTAuthentication sobreescribe get_user() para:
  1. Verificar que el token tenga claim 'iss' = 'platform'.
  2. Buscar el PlatformAdmin por el user_id del token (pk).

Aislamiento de JWT (ADR-013):
  - Token de platform (iss='platform') llega a endpoint de tenant →
    JWTAuthentication busca user_id en users.User del tenant → no existe → 401.
  - Token de tenant (sin claim iss) llega a /api/platform/ →
    iss != 'platform' → 401.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.tenants.models import PlatformAdmin


class PlatformJWTAuthentication(JWTAuthentication):
    """
    Autenticacion JWT para endpoints de /api/platform/.
    Verifica iss='platform' y busca el usuario en PlatformAdmin (esquema public).
    """

    def get_user(self, validated_token):
        if validated_token.get("iss") != "platform":
            raise InvalidToken(
                "Token no es valido para el panel de platform. "
                "Usa /api/platform/auth/login/ para obtener un token de platform."
            )

        try:
            user_id = validated_token[jwt_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token no contiene un user_id valido.")

        try:
            admin = PlatformAdmin.objects.get(pk=user_id)
        except PlatformAdmin.DoesNotExist:
            raise InvalidToken("Administrador de plataforma no encontrado.")

        if not admin.is_active:
            raise InvalidToken("Administrador de plataforma inactivo.")

        return admin
