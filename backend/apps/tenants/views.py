"""
Views de la app tenants.

Sprint 0: solo el healthcheck. No hay endpoints de gestión de tenants
(ADR-009: el alta de tenant es por management command, sin panel en MVP).
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    GET /api/health/

    Endpoint de estado del servicio. No requiere autenticación.
    Usado por Docker healthcheck, load balancers y monitoreo externo.

    Response 200:
        {"status": "ok"}
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Sin autenticación requerida

    @extend_schema(
        tags=["health"],
        summary="Estado del servicio",
        description=(
            "Retorna 200 si el backend está activo. "
            "No requiere autenticación ni JWT. "
            "Usado por Docker healthcheck y monitoreo."
        ),
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        auth=[],
    )
    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"})
