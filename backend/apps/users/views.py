"""
Views — app users

Endpoints:
  POST /api/auth/login/                   — login por email+password → JWT (EmailTokenObtainPairView)
  POST /api/auth/password-reset/          — solicitar link de reset (AllowAny)
  POST /api/auth/password-reset/confirm/  — confirmar reset con uid+token (AllowAny)
  GET  /api/users/me/                     — perfil del usuario autenticado (IsAuthenticated)
  GET  /api/users/                        — lista de operadores activos del tenant (IsTenantAdmin)
  POST /api/users/                        — crear operador (IsTenantAdmin)
  GET  /api/users/{id}/                   — detalle de operador (IsTenantAdmin)
  PATCH /api/users/{id}/                  — editar operador (IsTenantAdmin)
  DELETE /api/users/{id}/                 — soft-delete: is_active=False (IsTenantAdmin)

Reglas:
  - Solo se crean usuarios con role=OPERATOR desde este endpoint (forzado en serializer).
  - Soft-delete: DELETE hace is_active=False, nunca borrado físico (RULES.md §4).
  - No se expone password en ninguna respuesta.
  - El endpoint me/ es accesible para cualquier rol autenticado.
  - Los endpoints de password reset son AllowAny pero se ejecutan en el esquema del
    tenant activo (el middleware de django-tenants lo resuelve por el Host header).
  - La vista de solicitud siempre retorna 200 aunque el email no exista (evita enumerar usuarios).
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .notifications import notify_password_reset
from .permissions import IsTenantAdmin
from .serializers import (
    EmailTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserCreateSerializer,
    UserMeSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class EmailTokenObtainPairView(TokenObtainPairView):
    """
    Vista de login por email+password → JWT (access + refresh).

    Endpoint: POST /api/auth/login/
    Cuerpo:   {"email": "...", "password": "..."}
    Respuesta: {"access": "...", "refresh": "..."}

    Reemplaza a TokenObtainPairView de SimpleJWT para usar el serializer
    custom que trabaja con email como identificador (FIX R-08, ADR-007).
    AllowAny: definido en urls.py (SimpleJWT lo hace por defecto también).
    """

    serializer_class = EmailTokenObtainPairSerializer


class UserViewSet(viewsets.GenericViewSet):
    """
    ViewSet para gestión de usuarios del tenant.

    me:
      GET /api/users/me/ — perfil del usuario autenticado. Cualquier rol.

    list:
      GET /api/users/ — lista de operadores activos. Solo tenant_admin.

    create:
      POST /api/users/ — crear operador. Solo tenant_admin.
      El role se fuerza a OPERATOR en el serializer.

    retrieve:
      GET /api/users/{id}/ — detalle de operador activo. Solo tenant_admin.

    partial_update:
      PATCH /api/users/{id}/ — editar operador. Solo tenant_admin.

    destroy:
      DELETE /api/users/{id}/ — soft-delete (is_active=False). Solo tenant_admin.
    """

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsTenantAdmin()]

    def get_queryset(self):
        """Retorna usuarios activos con role=OPERATOR del tenant."""
        return User.objects.filter(
            is_active=True,
            role=User.Role.OPERATOR,
        ).order_by("email")

    @extend_schema(
        summary="Perfil del usuario autenticado",
        description="Retorna el perfil del usuario que hizo la request. Accesible para cualquier rol.",
        tags=["users"],
        responses={200: UserMeSerializer},
    )
    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Listar operadores",
        description="Retorna la lista de operadores activos del tenant. Solo tenant_admin.",
        tags=["users"],
        responses={200: UserSerializer(many=True)},
    )
    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(UserSerializer(page, many=True).data)
        return Response(UserSerializer(qs, many=True).data)

    @extend_schema(
        summary="Crear operador",
        description=(
            "Crea un nuevo operador (cajero/recepcionista) en el tenant. "
            "El role se fuerza a OPERATOR. Solo tenant_admin."
        ),
        tags=["users"],
        request=UserCreateSerializer,
        responses={201: UserSerializer},
    )
    def create(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Detalle de operador",
        description="Retorna el detalle de un operador activo. Solo tenant_admin.",
        tags=["users"],
        responses={200: UserSerializer},
    )
    def retrieve(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        user = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(UserSerializer(user).data)

    @extend_schema(
        summary="Editar operador",
        description=(
            "Actualiza parcialmente los datos de un operador activo. "
            "Campos editables: first_name, last_name, email, password. Solo tenant_admin."
        ),
        tags=["users"],
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
    )
    def partial_update(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        user = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(UserSerializer(updated).data)

    @extend_schema(
        summary="Desactivar operador (soft-delete)",
        description=(
            "Desactiva el operador (is_active=False). No borra físicamente el registro. "
            "Solo tenant_admin."
        ),
        tags=["users"],
        responses={204: None},
    )
    def destroy(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        user = get_object_or_404(self.get_queryset(), pk=pk)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Password Reset (flujo sin sesión activa — AllowAny)
# ---------------------------------------------------------------------------

class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/

    Solicita el envío de un link para restablecer la contraseña.

    Siempre retorna 200 para no revelar si el email existe en el sistema.
    El link se construye con uid (base64 del pk) + token firmado por Django
    y apunta al FRONTEND_URL configurado en settings.

    Scope: tenant activo (resuelto por el middleware de django-tenants).
    Permiso: AllowAny — no requiere autenticación previa.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Solicitar reset de contraseña",
        description=(
            "Envía un email con el link de restablecimiento si el email está registrado "
            "y activo en el tenant. Siempre responde 200 para no filtrar información."
        ),
        tags=["auth"],
        request=PasswordResetRequestSerializer,
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=email, is_active=True)
            token_gen = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_gen.make_token(user)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
            reset_url = f"{frontend_url}/reset-password/{uid}/{token}/"
            notify_password_reset(user, reset_url)
        except UserModel.DoesNotExist:
            # No se revela si el email existe o no (anti-enumeración)
            pass

        return Response(
            {"detail": "Si el email está registrado, recibirás las instrucciones en breve."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/

    Confirma el restablecimiento de contraseña usando uid + token del email.

    El uid es el pk del usuario codificado en base64.
    El token lo genera/valida Django PasswordResetTokenGenerator (expira en
    PASSWORD_RESET_TIMEOUT segundos, default 3 días; en el email indicamos 1 hora
    como expectativa conservadora para el usuario).

    Retorna 400 con código INVALID_RESET_LINK si el uid o el token son inválidos.
    Retorna 200 y actualiza la contraseña si la validación es exitosa.

    Scope: tenant activo (resuelto por el middleware de django-tenants).
    Permiso: AllowAny — no requiere autenticación previa.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirmar reset de contraseña",
        description=(
            "Valida uid + token recibidos por email y establece la nueva contraseña. "
            "Retorna 400 con código INVALID_RESET_LINK si el link es inválido o expiró."
        ),
        tags=["auth"],
        request=PasswordResetConfirmSerializer,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                        },
                    }
                },
            },
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        UserModel = get_user_model()
        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = UserModel.objects.get(pk=user_pk, is_active=True)
        except (UserModel.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"error": {"code": "INVALID_RESET_LINK", "message": "El link es inválido o expiró."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_gen = PasswordResetTokenGenerator()
        if not token_gen.check_token(user, token):
            return Response(
                {"error": {"code": "INVALID_RESET_LINK", "message": "El link es inválido o expiró."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Contraseña actualizada correctamente. Ya podés iniciar sesión."},
            status=status.HTTP_200_OK,
        )
