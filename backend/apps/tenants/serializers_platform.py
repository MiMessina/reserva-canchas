"""
Serializers para el Panel de System Admin (ADR-013).

Responsabilidad: validar estructura de datos (shape, tipos, longitudes, unicidad).
La lógica de negocio (crear esquema, migrar, crear admin) vive en services.py.

Regla (RULES.md §1): los serializers validan estructura, NO gobiernan negocio.

Serializers:
  TenantListSerializer   — lectura (list/retrieve)
  TenantCreateSerializer — escritura (create)
  TenantUpdateSerializer — escritura parcial (partial_update, solo name)
"""

import re

from rest_framework import serializers

from apps.tenants.models import Domain, Tenant

# Nombres reservados que no pueden usarse como schema_name.
# Misma lista que services.py para validación consistente en la capa de
# serializer (estructura) y en el service (negocio).
_RESERVED_SCHEMA_NAMES = frozenset({
    "public",
    "information_schema",
    "pg_catalog",
    "pg_toast",
    "pg_temp",
    "pg_internal",
    "test",
})

_SCHEMA_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


class TenantListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura de Tenant para el panel de platform.

    Expone solo metadata (no datos de negocio del complejo).
    El campo `domain` es el dominio primario del tenant.
    """

    domain = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["id", "name", "schema_name", "domain", "is_active", "created_at"]
        read_only_fields = ["id", "schema_name", "domain", "created_at"]

    def get_domain(self, obj) -> str:
        """Retorna el dominio primario del tenant o cadena vacía si no tiene."""
        primary = obj.domains.filter(is_primary=True).first()
        return primary.domain if primary else ""


class TenantCreateSerializer(serializers.Serializer):
    """
    Serializer de creación de Tenant.

    Valida:
      - name: requerido, max 200 chars.
      - schema_name: solo [a-z][a-z0-9_]*, máx 63 chars, no reservado, no existente.
      - domain: requerido, único en la plataforma.
      - admin_email: email válido.
      - admin_password: mínimo 8 chars, write-only.

    La creación real (esquema, migraciones, admin) la hace el service.
    """

    name = serializers.CharField(max_length=200)
    schema_name = serializers.CharField(max_length=63)
    domain = serializers.CharField(max_length=253)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(
        min_length=8,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_schema_name(self, value: str) -> str:
        value = value.lower().strip()

        if not value:
            raise serializers.ValidationError("El schema_name no puede estar vacío.")

        if len(value) > 63:
            raise serializers.ValidationError("El schema_name no puede superar los 63 caracteres.")

        if not _SCHEMA_NAME_PATTERN.match(value):
            raise serializers.ValidationError(
                "El schema_name solo puede contener letras minúsculas, números y guion bajo, "
                "y debe comenzar con una letra."
            )

        if value in _RESERVED_SCHEMA_NAMES or value.startswith("pg_"):
            raise serializers.ValidationError(
                f"'{value}' es un nombre reservado y no puede usarse como schema_name."
            )

        if Tenant.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError(
                f"El schema '{value}' ya existe.",
                code="SCHEMA_ALREADY_EXISTS",
            )

        return value

    def validate_domain(self, value: str) -> str:
        value = value.lower().strip()
        if Domain.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                f"El dominio '{value}' ya está en uso.",
                code="DOMAIN_ALREADY_EXISTS",
            )
        return value


class TenantUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de actualización parcial de Tenant.

    Solo permite editar `name`. El schema_name y domain son inmutables
    una vez creado el tenant (ADR-013 §Reglas de negocio).
    """

    class Meta:
        model = Tenant
        fields = ["name"]
