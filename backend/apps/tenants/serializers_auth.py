"""
Serializers para los endpoints de autenticación centralizada.

Sprint 14 — Login Centralizado.

Responsabilidad: validar estructura de los requests (campos requeridos, tipos).
La lógica de negocio (autenticación, generación de códigos) vive en services.py.
"""

from rest_framework import serializers


class LookupEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class CentralLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    schema_name = serializers.CharField(max_length=63)


class ExchangeCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)
