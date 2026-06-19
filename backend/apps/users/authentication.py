"""
Backend de autenticación JWT para endpoints de tenant (ADR-013).

Sobreescribe JWTAuthentication estándar para rechazar tokens de platform
(que tienen claim 'iss' = 'platform'). Garantiza el aislamiento de JWT:
un token de system_admin no puede autenticarse en endpoints de tenant.

Uso: se configura en settings.py como DEFAULT_AUTHENTICATION_CLASSES,
reemplazando al JWTAuthentication estándar.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class TenantJWTAuthentication(JWTAuthentication):
    """
    Autenticación JWT para endpoints de tenant.

    Rechaza tokens con claim 'iss' = 'platform' (emitidos por el Panel de System Admin).
    Esto garantiza que un JWT de system_admin no sea válido en endpoints de tenant.

    ADR-013: Aislamiento de JWT entre platform y tenants.
    """

    def get_user(self, validated_token):
        """
        Verifica que el token NO sea de platform antes de buscar el usuario.

        Raises:
            InvalidToken: si el token tiene iss='platform' (es un token de system_admin).
        """
        if validated_token.get("iss") == "platform":
            raise InvalidToken(
                "Token de platform no es válido en endpoints de tenant. "
                "Usá /api/auth/login/ para obtener un token de tenant."
            )
        return super().get_user(validated_token)
