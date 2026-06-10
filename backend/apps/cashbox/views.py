"""
Views — app cashbox (sesiones de caja)

Endpoints registrados en apps/cashbox/urls.py:
  POST /api/cash-sessions/open/    — abrir sesión (operator/tenant_admin)
  POST /api/cash-sessions/close/   — cerrar sesión (operator/tenant_admin)
  GET  /api/cash-sessions/today/   — sesión del día actual o 404 (operator/tenant_admin)
  GET  /api/cash-sessions/         — historial paginado; filtro ?date=YYYY-MM-DD (operator/tenant_admin)

Reglas:
  - Toda la lógica delega a cashbox/services.py.
  - Los players reciben 403 en todos los endpoints.
  - Los errores de negocio (SESSION_ALREADY_OPEN, etc.) se retornan como 400
    con el payload estándar de API_GUIDELINES.md §7.
"""

import logging

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cashbox.models import CashSession
from apps.cashbox.serializers import (
    CashSessionSerializer,
    CloseCashSessionSerializer,
    OpenCashSessionSerializer,
)
from apps.cashbox.services import close_cash_session, open_cash_session
from apps.users.permissions import IsOperatorOrAdmin

logger = logging.getLogger(__name__)


class CashSessionViewSet(viewsets.GenericViewSet):
    """
    ViewSet para la gestión de sesiones de caja diaria.

    open:
      Abre una sesión de caja. Permisos: operator o tenant_admin.
      Lanza SESSION_ALREADY_OPEN si ya existe una sesión abierta para el día.

    close:
      Cierra la sesión abierta del día. Permisos: operator o tenant_admin.
      Calcula expected_amount y difference automáticamente.

    today:
      Retorna la sesión del día actual (en hora BA) o 404 si no existe.

    list:
      Historial paginado de sesiones. Filtro opcional ?date=YYYY-MM-DD.
    """

    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]
    serializer_class = CashSessionSerializer

    def get_queryset(self):
        """
        Queryset base: sesiones activas del tenant, ordenadas por fecha desc.
        django-tenants garantiza el scope del esquema activo.
        """
        return CashSession.objects.filter(is_active=True).order_by("-session_date")

    # -----------------------------------------------------------------------
    # GET /api/cash-sessions/
    # -----------------------------------------------------------------------

    @extend_schema(
        summary="Historial de sesiones de caja",
        description=(
            "Retorna el historial paginado de sesiones de caja del tenant. "
            "Filtro opcional por fecha exacta: ?date=YYYY-MM-DD."
        ),
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por fecha de sesión (YYYY-MM-DD). Opcional.",
                required=False,
            ),
        ],
        responses={200: CashSessionSerializer(many=True)},
    )
    def list(self, request):
        """Historial paginado de sesiones. Filtro ?date=YYYY-MM-DD."""
        qs = self.get_queryset()

        date_param = request.query_params.get("date")
        if date_param:
            from datetime import date as date_type
            try:
                from datetime import datetime
                filter_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                qs = qs.filter(session_date=filter_date)
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Formato de fecha inválido. Use YYYY-MM-DD.",
                            "details": {"date": date_param},
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = CashSessionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CashSessionSerializer(qs, many=True)
        return Response(serializer.data)

    # -----------------------------------------------------------------------
    # POST /api/cash-sessions/open/
    # -----------------------------------------------------------------------

    @extend_schema(
        summary="Abrir sesión de caja",
        description=(
            "Abre una nueva sesión de caja para el día indicado (o el día actual en BA "
            "si no se especifica session_date). Solo operator o tenant_admin."
        ),
        request=OpenCashSessionSerializer,
        responses={201: CashSessionSerializer},
    )
    @action(detail=False, methods=["post"], url_path="open")
    def open(self, request):
        """POST /api/cash-sessions/open/ — abre una sesión de caja."""
        serializer = OpenCashSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = open_cash_session(
            operator=request.user,
            opening_amount=serializer.validated_data["opening_amount"],
            session_date=serializer.validated_data.get("session_date"),
        )

        return Response(
            CashSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    # -----------------------------------------------------------------------
    # POST /api/cash-sessions/close/
    # -----------------------------------------------------------------------

    @extend_schema(
        summary="Cerrar sesión de caja",
        description=(
            "Cierra la sesión abierta del día (o del día especificado en el request). "
            "Calcula expected_amount (opening_amount + movimientos del día) y la "
            "difference (closing_amount - expected_amount). Solo operator o tenant_admin."
        ),
        request=CloseCashSessionSerializer,
        responses={200: CashSessionSerializer},
    )
    @action(detail=False, methods=["post"], url_path="close")
    def close(self, request):
        """POST /api/cash-sessions/close/ — cierra la sesión abierta del día."""
        serializer = CloseCashSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = close_cash_session(
            operator=request.user,
            closing_amount=serializer.validated_data["closing_amount"],
            notes=serializer.validated_data.get("notes", ""),
            session_date=serializer.validated_data.get("session_date"),
        )

        return Response(
            CashSessionSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------------------------------------
    # GET /api/cash-sessions/today/
    # -----------------------------------------------------------------------

    @extend_schema(
        summary="Sesión de caja del día actual",
        description=(
            "Retorna la sesión de caja del día actual (en hora Buenos Aires). "
            "404 si no existe sesión para hoy."
        ),
        responses={200: CashSessionSerializer, 404: None},
    )
    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        """GET /api/cash-sessions/today/ — sesión del día actual o 404."""
        from apps.cashbox.services import _today_ba

        today = _today_ba()
        try:
            session = CashSession.objects.get(
                session_date=today,
                is_active=True,
            )
        except CashSession.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "SESSION_NOT_FOUND",
                        "message": f"No existe una sesión de caja para el {today}.",
                        "details": {"date": str(today)},
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(CashSessionSerializer(session).data)
