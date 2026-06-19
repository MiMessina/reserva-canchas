"""
Views del Panel de System Admin (ADR-013).

Endpoints bajo /api/platform/ — solo responden desde PUBLIC_SCHEMA_URLCONF.
Autenticación: JWT contra django.contrib.auth.User (superuser de Django).
Permiso: IsSystemAdmin (is_superuser=True).

No se expone ningún dato de negocio del tenant (reservas, canchas, caja, usuarios).
Solo metadata: name, schema_name, domain, is_active, created_at.

Endpoints:
  GET    /api/platform/tenants/           — listar todos los tenants
  POST   /api/platform/tenants/           — crear nuevo tenant
  GET    /api/platform/tenants/{id}/      — detalle de un tenant
  PATCH  /api/platform/tenants/{id}/      — editar nombre
  POST   /api/platform/tenants/{id}/toggle/ — activar / desactivar

Auditoría:
  platform.tenant_created  — se loguea al crear
  platform.tenant_toggled  — se loguea al toggle
  platform.login            — la emite el endpoint de auth (TokenObtainPairView)
"""

import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenants.authentication_platform import PlatformJWTAuthentication
from apps.tenants.models import Tenant
from apps.tenants.permissions_platform import IsSystemAdmin
from apps.tenants.serializers_platform import (
    TenantCreateSerializer,
    TenantListSerializer,
    TenantUpdateSerializer,
)
from apps.tenants.services import (
    DomainAlreadyExists,
    InvalidSchemaName,
    SchemaAlreadyExists,
    TenantCreationFailed,
    create_tenant_service,
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Listar todos los tenants",
        description=(
            "Retorna la lista de todos los complejos (tenants) registrados en la plataforma. "
            "Solo accesible para system_admin."
        ),
        tags=["platform"],
        responses={200: TenantListSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Crear nuevo tenant",
        description=(
            "Crea un nuevo complejo: genera el schema PostgreSQL, ejecuta migraciones "
            "y crea el usuario tenant_admin inicial. Operación sincrónica (puede tardar 5-15s). "
            "Solo accesible para system_admin."
        ),
        tags=["platform"],
        request=TenantCreateSerializer,
        responses={
            201: TenantListSerializer,
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
    ),
    retrieve=extend_schema(
        summary="Detalle de un tenant",
        description="Retorna el detalle de un complejo por ID. Solo accesible para system_admin.",
        tags=["platform"],
        responses={200: TenantListSerializer},
    ),
    partial_update=extend_schema(
        summary="Editar nombre del tenant",
        description=(
            "Actualiza el nombre del complejo. El schema_name y el dominio son inmutables. "
            "Solo accesible para system_admin."
        ),
        tags=["platform"],
        request=TenantUpdateSerializer,
        responses={200: TenantListSerializer},
    ),
)
class TenantViewSet(viewsets.GenericViewSet):
    """
    ViewSet para la gestión de tenants desde el Panel de System Admin.

    Autenticación: JWTAuthentication contra django.contrib.auth.User.
    Permiso: IsSystemAdmin (is_superuser=True).

    Acciones:
      list           — GET /api/platform/tenants/
      create         — POST /api/platform/tenants/
      retrieve       — GET /api/platform/tenants/{id}/
      partial_update — PATCH /api/platform/tenants/{id}/
      toggle         — POST /api/platform/tenants/{id}/toggle/
    """

    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsSystemAdmin]
    queryset = Tenant.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return TenantCreateSerializer
        if self.action == "partial_update":
            return TenantUpdateSerializer
        return TenantListSerializer

    # -----------------------------------------------------------------------
    # list — GET /api/platform/tenants/
    # -----------------------------------------------------------------------

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(TenantListSerializer(page, many=True).data)
        return Response(TenantListSerializer(qs, many=True).data)

    # -----------------------------------------------------------------------
    # create — POST /api/platform/tenants/
    # -----------------------------------------------------------------------

    def create(self, request):
        serializer = TenantCreateSerializer(data=request.data)

        if not serializer.is_valid():
            # Convertir errores de serializer al formato estándar del proyecto.
            # Los errores de unicidad del serializer tienen código explícito
            # (SCHEMA_ALREADY_EXISTS, DOMAIN_ALREADY_EXISTS).
            errors = serializer.errors
            # Buscar el primer error con código de negocio conocido
            for field, field_errors in errors.items():
                if isinstance(field_errors, list):
                    for err in field_errors:
                        code = getattr(err, "code", None) if hasattr(err, "code") else None
                        if code in ("SCHEMA_ALREADY_EXISTS", "DOMAIN_ALREADY_EXISTS"):
                            return Response(
                                {"error": {"code": code, "message": str(err)}},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
            # Error de validación genérico (campo requerido, formato inválido, etc.)
            return Response(
                {"error": {"code": "INVALID_SCHEMA_NAME" if "schema_name" in errors else "VALIDATION_ERROR",
                           "message": str(errors)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vd = serializer.validated_data
        try:
            tenant = create_tenant_service(
                name=vd["name"],
                schema_name=vd["schema_name"],
                domain=vd["domain"],
                admin_email=vd["admin_email"],
                admin_password=vd["admin_password"],
            )
        except (InvalidSchemaName, SchemaAlreadyExists, DomainAlreadyExists) as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TenantCreationFailed as exc:
            logger.error(
                "[TenantViewSet.create] TenantCreationFailed para schema '%s': %s",
                vd.get("schema_name"),
                exc.message,
            )
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception(
                "[TenantViewSet.create] Error inesperado creando tenant '%s': %s",
                vd.get("schema_name"),
                exc,
            )
            return Response(
                {
                    "error": {
                        "code": "TENANT_CREATION_FAILED",
                        "message": "Error al crear el tenant. El proceso fue revertido.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "[platform] platform.tenant_created | admin=%s | tenant=%s | schema=%s | domain=%s",
            request.user.email,
            tenant.name,
            tenant.schema_name,
            vd["domain"],
        )
        return Response(
            TenantListSerializer(tenant).data,
            status=status.HTTP_201_CREATED,
        )

    # -----------------------------------------------------------------------
    # retrieve — GET /api/platform/tenants/{id}/
    # -----------------------------------------------------------------------

    def retrieve(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        tenant = get_object_or_404(Tenant, pk=pk)
        return Response(TenantListSerializer(tenant).data)

    # -----------------------------------------------------------------------
    # partial_update — PATCH /api/platform/tenants/{id}/
    # -----------------------------------------------------------------------

    def partial_update(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        tenant = get_object_or_404(Tenant, pk=pk)
        serializer = TenantUpdateSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        logger.info(
            "[platform] platform.tenant_updated | admin=%s | tenant_id=%s | schema=%s",
            request.user.email,
            updated.id,
            updated.schema_name,
        )
        return Response(TenantListSerializer(updated).data)

    # -----------------------------------------------------------------------
    # toggle — POST /api/platform/tenants/{id}/toggle/
    # -----------------------------------------------------------------------

    @extend_schema(
        summary="Activar / desactivar tenant",
        description=(
            "Invierte el estado is_active del tenant. "
            "Un tenant inactivo impide el login de sus usuarios. "
            "Los datos permanecen intactos (soft-delete). "
            "Solo accesible para system_admin."
        ),
        tags=["platform"],
        request=None,
        responses={200: TenantListSerializer},
    )
    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        from rest_framework.generics import get_object_or_404
        tenant = get_object_or_404(Tenant, pk=pk)
        previous_state = tenant.is_active
        tenant.is_active = not tenant.is_active
        tenant.save(update_fields=["is_active", "updated_at"])

        logger.info(
            "[platform] platform.tenant_toggled | admin=%s | tenant=%s | is_active=%s -> %s",
            request.user.email,
            tenant.schema_name,
            previous_state,
            tenant.is_active,
        )
        return Response(TenantListSerializer(tenant).data)
