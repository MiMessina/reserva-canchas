"""
Vista de autenticacion para el Panel de System Admin (ADR-013).

El system_admin es un PlatformAdmin (apps.tenants, SHARED_APPS, esquema public).
PlatformAdmin es independiente de users.User y auth.User — vive solo en public.

El login en /api/platform/auth/login/ acepta {"email": ..., "password": ...}
y emite un JWT con claim "iss": "platform" para distinguirlo de tokens de tenant.
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.tenants.models import PlatformAdmin

logger = logging.getLogger(__name__)


class PlatformLoginThrottle(AnonRateThrottle):
    scope = "platform_login"


class PlatformTokenObtainPairView(APIView):
    """
    POST /api/platform/auth/login/

    Login del system_admin. Acepta {"email": ..., "password": ...}.
    Solo autentica PlatformAdmin activos.

    Respuesta exitosa (200): {"access": "...", "refresh": "..."}
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PlatformLoginThrottle]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"error": {"code": "MISSING_CREDENTIALS", "message": "Email y contrasena son requeridos."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            admin = PlatformAdmin.objects.get(email=email)
        except PlatformAdmin.DoesNotExist:
            return Response(
                {"error": {"code": "INVALID_CREDENTIALS", "message": "Credenciales invalidas."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not admin.check_password(password):
            return Response(
                {"error": {"code": "INVALID_CREDENTIALS", "message": "Credenciales invalidas."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not admin.is_active:
            return Response(
                {"error": {"code": "USER_INACTIVE", "message": "El usuario esta inactivo."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # JWT con claim 'iss' = 'platform' para aislamiento (ADR-013)
        refresh = RefreshToken.for_user(admin)
        refresh["iss"] = "platform"
        refresh.access_token["iss"] = "platform"

        logger.info("[platform] platform.login | admin=%s | id=%s", admin.email, admin.pk)

        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_200_OK,
        )


class PlatformTokenRefreshView(TokenRefreshView):
    """
    POST /api/platform/auth/refresh/

    Refresca el access token del system_admin.
    Valida que el refresh token tenga iss='platform' antes de procesarlo.
    """

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh", "")
        try:
            token = UntypedToken(refresh_token)
            if token.get("iss") != "platform":
                raise InvalidToken("Token no valido para esta plataforma.")
        except (InvalidToken, TokenError):
            return Response(
                {"error": {"code": "INVALID_TOKEN", "message": "Token no valido."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return super().post(request, *args, **kwargs)
