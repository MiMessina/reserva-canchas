"""
Serializers — app tenants.

Responsabilidad: validar estructura de datos (shape, tipos, longitudes).
La lógica de negocio vive en services.py.

Regla (RULES.md §1): los serializers validan estructura, NO gobiernan negocio.
"""

from rest_framework import serializers

from apps.tenants.models import ComplexSettings


class ComplexSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer completo de ComplexSettings.

    Usado para:
    - GET /api/settings/  → leer la configuración actual del complejo.
    - Respuesta de PATCH /api/settings/ tras actualización.

    Todos los campos se exponen (lectura + escritura).
    is_active, created_at y updated_at son de solo lectura.
    """

    class Meta:
        model = ComplexSettings
        fields = [
            "id",
            "complex_name",
            "payment_instructions",
            "cbu_alias",
            "cbu_number",
            "account_holder",
            "phone",
            "instagram",
            "whatsapp",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class ComplexSettingsUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de actualización parcial (PATCH) de ComplexSettings.

    Todos los campos son opcionales para soportar semántica PATCH:
    el cliente puede enviar solo los campos que quiere modificar.

    Usado en:
    - PATCH /api/settings/  → actualizar configuración (solo tenant_admin).
    """

    complex_name = serializers.CharField(max_length=200, required=False)
    payment_instructions = serializers.CharField(required=False, allow_blank=True)
    cbu_alias = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cbu_number = serializers.CharField(max_length=22, required=False, allow_blank=True)
    account_holder = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    instagram = serializers.CharField(max_length=100, required=False, allow_blank=True)
    whatsapp = serializers.CharField(max_length=30, required=False, allow_blank=True)

    class Meta:
        model = ComplexSettings
        fields = [
            "complex_name",
            "payment_instructions",
            "cbu_alias",
            "cbu_number",
            "account_holder",
            "phone",
            "instagram",
            "whatsapp",
        ]
