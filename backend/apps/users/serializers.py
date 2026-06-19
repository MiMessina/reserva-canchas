"""
Serializers — app users

Los serializers validan estructura, no gobiernan negocio (RULES.md).

FIX R-08: EmailTokenObtainPairSerializer reemplaza al TokenObtainPairSerializer
por defecto de SimpleJWT, que espera `username`. El contrato del login queda:
  POST /api/auth/login/  body: {"email": "...", "password": "..."}
                         response: {"access": "...", "refresh": "..."}

Serializers de escritura:
  UserCreateSerializer — crea un usuario con role=OPERATOR (forzado en create()).
  UserUpdateSerializer — edita first_name, last_name, email, password (opcional).
"""

from django.db import connection
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
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

    def validate(self, attrs):
        """
        Extiende la validación de SimpleJWT para rechazar login cuando el tenant
        está inactivo (TENANT_INACTIVE).

        SimpleJWT valida user.is_active pero no verifica el estado del tenant.
        Este método agrega esa verificación después de que la autenticación del
        usuario fue exitosa. Si el esquema activo corresponde a un tenant con
        is_active=False, se lanza AuthenticationFailed con código TENANT_INACTIVE.

        El bloque try/except captura el caso de esquema 'public' u otros contextos
        donde el tenant no exista en la tabla; en esos casos no se bloquea.
        """
        data = super().validate(attrs)

        from django_tenants.utils import get_tenant_model
        TenantModel = get_tenant_model()
        try:
            tenant = TenantModel.objects.get(schema_name=connection.schema_name)
            if not tenant.is_active:
                raise AuthenticationFailed({
                    "error": {
                        "code": "TENANT_INACTIVE",
                        "message": "Este complejo no está disponible en este momento.",
                    }
                })
        except TenantModel.DoesNotExist:
            # Esquema public u otro contexto sin tenant de negocio — no bloquear.
            pass

        return data

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


# ---------------------------------------------------------------------------
# Serializers de escritura de operadores (Sprint 1+)
# ---------------------------------------------------------------------------

class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para POST /api/users/ — crear un operador.

    El role se fuerza a OPERATOR en create() independientemente de lo que
    envíe el cliente. El password se hashea con set_password().
    La respuesta del endpoint usa UserSerializer (sin password).
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # El role se fuerza a OPERATOR; nunca se puede crear un tenant_admin
        # desde este endpoint (RBAC.md §4).
        user = User(role=User.Role.OPERATOR, **validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para PATCH /api/users/{id}/ — editar un operador.

    Campos editables: first_name, last_name, email, password (opcional).
    El role y is_active no son editables desde este endpoint.
    Si se pasa password, se hashea correctamente con set_password().
    """

    password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# Serializers de password reset (Sprint 3 — flujo sin sesión activa)
# ---------------------------------------------------------------------------

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Valida el cuerpo de POST /api/auth/password-reset/.
    Solo requiere el email del usuario.
    """

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Valida el cuerpo de POST /api/auth/password-reset/confirm/.
    Recibe uid (base64 del pk) + token firmado + nueva contraseña.
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
