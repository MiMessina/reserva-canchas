"""
Serializers — app users

Sprint 0: serializers base + autenticación por email (FIX R-08).
Los serializers validan estructura, no gobiernan negocio (RULES.md).

FIX R-08: EmailTokenObtainPairSerializer reemplaza al TokenObtainPairSerializer
por defecto de SimpleJWT, que espera `username`. El contrato del login queda:
  POST /api/auth/login/  body: {"email": "...", "password": "..."}
                         response: {"access": "...", "refresh": "..."}

Expansión Sprint 1+:
  - Serializer de registro de player.
  - Serializer de perfil (ver/editar datos propios).
  - Serializer de creación de operator (solo tenant_admin).
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


# ---------------------------------------------------------------------------
# Autenticación por email (FIX R-08)
# ---------------------------------------------------------------------------

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer custom de login que acepta `email` en lugar de `username`.

    SimpleJWT usa USERNAME_FIELD del modelo para construir el campo del
    serializer base; como User.USERNAME_FIELD = "email", la herencia directa
    ya funciona correctamente. Este subclase existe para:
      1. Documentar explícitamente la decisión (FIX R-08).
      2. Permitir agregar claims custom al token en el futuro (ej: `role`).

    Contrato de entrada:  {"email": "...", "password": "..."}
    Contrato de salida:   {"access": "...", "refresh": "..."}
    """

    # Al heredar de TokenObtainPairSerializer con USERNAME_FIELD="email",
    # el campo se llama automáticamente "email". No hace falta redefinirlo.

    @classmethod
    def get_token(cls, user):
        """
        Agrega claims custom al payload del JWT.
        Actualmente: rol del usuario (para que el frontend pueda adaptar la UI
        sin hacer una llamada extra; la validación dura siempre es en el backend).
        """
        token = super().get_token(user)
        token["role"] = user.role
        return token


# ---------------------------------------------------------------------------
# Serializers de lectura de User
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura del User.
    No expone password ni campos sensibles.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer para el endpoint GET /api/users/me/ (perfil propio).
    No expone password. El role no es editable por el usuario.

    Sprint 0: definido. El endpoint se construye en Sprint 1+.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "role", "is_active", "created_at", "updated_at"]
