"""
Views — app users

Endpoints:
  POST /api/auth/login/   — login por email+password → JWT (EmailTokenObtainPairView)
  GET  /api/users/me/     — perfil del usuario autenticado (IsAuthenticated)
  GET  /api/users/        — lista de operadores activos del tenant (IsTenantAdmin)
  POST /api/users/        — crear operador (IsTenantAdmin)
  GET  /api/users/{id}/   — detalle de operador (IsTenantAdmin)
  PATCH /api/users/{id}/  — editar operador (IsTenantAdmin)
  DELETE /api/users/{id}/ — soft-delete: is_active=False (IsTenantAdmin)

Reglas:
  - Solo se crean usuarios con role=OPERATOR desde este endpoint (forzado en serializer).
  - Soft-delete: DELETE hace is_active=False, nunca borrado físico (RULES.md §4).
  - No se expone password en ninguna respuesta.
  - El endpoint me/ es accesible para cualquier rol autenticado.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsTenantAdmin
from .serializers import (
    EmailTokenObtainPairSerializer,
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
