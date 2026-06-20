"""
Views para los endpoints de autenticación centralizada (Sprint 14).

Endpoints (PUBLIC_SCHEMA_URLCONF — config/urls_public.py):
  POST /api/auth/lookup-email/   — encuentra en qué tenant(s) existe un email
  POST /api/auth/central-login/  — autentica y genera un OneTimeCode
  POST /api/auth/exchange-code/  — intercambia el OTC por JWT (access + refresh)

Permisos: AllowAny (los endpoints son públicos; el control de negocio está en services.py).
Auditoría: los intentos fallidos se loguean en services.py.

Regla (ARCHITECTURE.md §4):
  Las views solo despachan al service y mapean excepciones a respuestas HTTP.
  No hay lógica de negocio ni transiciones de estado en este archivo.
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants import services as tenant_services
from apps.tenants.serializers_auth import (
    CentralLoginSerializer,
    ExchangeCodeSerializer,
    LookupEmailSerializer,
)

logger = logging.getLogger(__name__)

# Mapeo de códigos de negocio a (http_status, mensaje amigable)
ERROR_MAP = {
    "TENANT_INACTIVE": (
        status.HTTP_401_UNAUTHORIZED,
        "El complejo está inactivo.",
    ),
    "INVALID_CREDENTIALS": (
        status.HTTP_401_UNAUTHORIZED,
        "Credenciales inválidas.",
    ),
    "ROLE_NOT_ALLOWED": (
        status.HTTP_403_FORBIDDEN,
        "Rol no permitido para el login centralizado.",
    ),
    "CODE_NOT_FOUND": (
        status.HTTP_400_BAD_REQUEST,
        "Código no encontrado.",
    ),
    "CODE_ALREADY_USED": (
        status.HTTP_400_BAD_REQUEST,
        "El código ya fue utilizado.",
    ),
    "CODE_EXPIRED": (
        status.HTTP_400_BAD_REQUEST,
        "El código ha expirado.",
    ),
}


def _error_response(code: str) -> Response:
    """Construye una respuesta de error estándar (API_GUIDELINES.md §7)."""
    http_status, message = ERROR_MAP.get(
        code, (status.HTTP_400_BAD_REQUEST, code)
    )
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


class LookupEmailView(APIView):
    """
    POST /api/auth/lookup-email/

    Recibe un email y retorna la lista de tenants donde ese email tiene cuenta.
    Permite que el frontend muestre al usuario en qué complejo quiere ingresar.

    Request:  {"email": "user@example.com"}
    Response: [{"schema_name": "lospinos", "tenant_name": "Los Pinos", "domain": "lospinos.localhost"}, ...]

    Permiso: público (AllowAny). El email no revela datos sensibles más allá de
    en qué complejos el usuario tiene cuenta.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LookupEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenants = tenant_services.lookup_email(serializer.validated_data["email"])
        return Response(tenants, status=status.HTTP_200_OK)


class CentralLoginView(APIView):
    """
    POST /api/auth/central-login/

    Autentica al usuario en el tenant indicado y genera un OneTimeCode (TTL 60s).
    El frontend redirige al subdominio del tenant con el código en la URL.

    Request:
        {"email": "user@example.com", "password": "secret", "schema_name": "lospinos"}
    Response:
        {"code": "<token_urlsafe>", "redirect_url": "http://lospinos.localhost"}

    Permiso: público. La autenticación se verifica en services.py.
    Solo roles tenant_admin y operator pueden usar este endpoint (players no).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CentralLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = tenant_services.central_login(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                schema_name=serializer.validated_data["schema_name"],
            )
        except ValueError as exc:
            return _error_response(str(exc))
        return Response(result, status=status.HTTP_200_OK)


class ExchangeCodeView(APIView):
    """
    POST /api/auth/exchange-code/

    Intercambia el OneTimeCode por un par JWT (access + refresh).
    El código es de un solo uso y expira a los 60 segundos.

    Request:  {"code": "<token_urlsafe>"}
    Response: {"access": "<jwt>", "refresh": "<jwt>"}

    Permiso: público. La validez del código la verifica services.py.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ExchangeCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = tenant_services.exchange_code(serializer.validated_data["code"])
        except ValueError as exc:
            return _error_response(str(exc))
        return Response(result, status=status.HTTP_200_OK)
