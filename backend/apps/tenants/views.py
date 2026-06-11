"""
Views de la app tenants.

Endpoints:
  GET  /api/health/     — healthcheck, sin autenticación.
  GET  /api/settings/   — configuración pública del complejo (AllowAny, acotada al tenant).
  PATCH /api/settings/  — actualizar configuración del complejo (solo tenant_admin).

ADR-009: el alta de tenant es por management command, sin panel en MVP.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.serializers import ComplexSettingsSerializer, ComplexSettingsUpdateSerializer
from apps.tenants.services import get_complex_settings, update_complex_settings
from apps.users.permissions import IsTenantAdmin


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


@extend_schema_view(
    get=extend_schema(
        tags=["settings"],
        summary="Obtener configuración del complejo",
        description=(
            "Retorna la configuración pública/operativa del complejo activo. "
            "No requiere autenticación. La respuesta siempre existe: si el complejo "
            "aún no configuró sus datos, retorna un objeto con campos vacíos. "
            "El tenant se determina automáticamente por el dominio de la request."
        ),
        responses={200: ComplexSettingsSerializer},
        auth=[],
    ),
    patch=extend_schema(
        tags=["settings"],
        summary="Actualizar configuración del complejo",
        description=(
            "Actualiza parcialmente la configuración del complejo. "
            "Solo pueden hacerlo los administradores del complejo (tenant_admin). "
            "Semántica PATCH: solo se actualizan los campos enviados."
        ),
        request=ComplexSettingsUpdateSerializer,
        responses={200: ComplexSettingsSerializer},
    ),
)
class ComplexSettingsView(APIView):
    """
    GET  /api/settings/ — pública, acotada al tenant del dominio.
    PATCH /api/settings/ — solo tenant_admin.

    Singleton por diseño: cada tenant tiene una única instancia de
    ComplexSettings, garantizada por el aislamiento de esquema PostgreSQL.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsTenantAdmin()]

    def get(self, request, *args, **kwargs):
        settings_obj = get_complex_settings()
        serializer = ComplexSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = ComplexSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_complex_settings(data=serializer.validated_data)
        return Response(ComplexSettingsSerializer(updated).data)
