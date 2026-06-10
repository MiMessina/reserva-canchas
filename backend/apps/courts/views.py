"""
Views — app courts

ViewSets para Court, ScheduleBlock y SlotBlock.

Endpoints registrados en apps/courts/urls.py con DefaultRouter:
  GET    /api/courts/                   — lista canchas
  POST   /api/courts/                   — crear cancha (solo tenant_admin)
  GET    /api/courts/{id}/              — detalle cancha
  PATCH  /api/courts/{id}/             — editar cancha (solo tenant_admin)
  DELETE /api/courts/{id}/              — baja lógica (solo tenant_admin)

  GET    /api/schedule-blocks/          — lista bloques horarios
  POST   /api/schedule-blocks/          — crear bloque (solo tenant_admin)
  GET    /api/schedule-blocks/{id}/     — detalle bloque
  PATCH  /api/schedule-blocks/{id}/    — editar bloque (solo tenant_admin)
  DELETE /api/schedule-blocks/{id}/     — baja lógica (solo tenant_admin)

  GET    /api/slot-blocks/              — lista bloqueos de slots (operator/admin)
  POST   /api/slot-blocks/              — crear bloqueo (operator/admin)
  DELETE /api/slot-blocks/{id}/         — baja lógica (operator/admin)

Reglas:
  - DELETE = baja lógica (perform_destroy llama al service de deactivación).
  - Filtros sin django-filter (no está en requirements): se leen query params
    manualmente en get_queryset().
  - Toda lógica de negocio delega a apps/courts/services.py (RULES.md §4).
  - Serializer de lectura vs. escritura: CourtSerializer / CourtWriteSerializer.
"""

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.courts.models import Court, ScheduleBlock, SlotBlock
from apps.courts.permissions import IsTenantAdminOrReadOnly
from apps.courts.serializers import (
    CourtSerializer,
    CourtWriteSerializer,
    ScheduleBlockSerializer,
    SlotBlockSerializer,
)
from apps.courts import services

logger = logging.getLogger(__name__)


class CourtViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el ABM de canchas.

    list:
      Retorna las canchas del tenant activo. Filtrable por court_type y is_active.

    create:
      Crea una nueva cancha. Solo tenant_admin.

    retrieve:
      Retorna el detalle de una cancha.

    partial_update:
      Edita parcialmente una cancha. Solo tenant_admin.

    destroy:
      Baja lógica (is_active=False). Solo tenant_admin. El registro NO se borra físicamente.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        # list y retrieve son públicos: el jugador necesita ver canchas sin JWT
        # para poder usar la grilla de reservas (igual que /availability/).
        # Mutaciones requieren tenant_admin.
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated(), IsTenantAdminOrReadOnly()]

    def get_queryset(self):
        """
        Retorna canchas del tenant activo.

        Filtros disponibles (query params):
          court_type  — filtra por tipo (futbol_5, futbol_7, padel).
          is_active   — filtra por estado activo/inactivo (true/false).
                        Si no se indica, retorna TODAS (activas e inactivas).
        """
        qs = Court.objects.all()

        court_type = self.request.query_params.get("court_type")
        if court_type:
            qs = qs.filter(court_type=court_type)

        is_active_param = self.request.query_params.get("is_active")
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")
            qs = qs.filter(is_active=is_active)

        return qs

    def get_serializer_class(self):
        """Serializer de escritura para mutaciones; de lectura para el resto."""
        if self.action in ("create", "partial_update", "update"):
            return CourtWriteSerializer
        return CourtSerializer

    @extend_schema(
        summary="Listar canchas",
        description=(
            "Retorna la lista paginada de canchas del complejo. "
            "Filtrable por court_type (futbol_5, futbol_7, padel) y is_active (true/false)."
        ),
        parameters=[
            OpenApiParameter(
                name="court_type",
                description="Filtrar por tipo: futbol_5, futbol_7, padel.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="is_active",
                description="Filtrar por estado activo: true o false.",
                required=False,
                type=bool,
            ),
        ],
        tags=["courts"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Crear cancha",
        description="Crea una nueva cancha activa. Solo tenant_admin.",
        tags=["courts"],
        responses={201: CourtSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = CourtWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        court = services.create_court(**serializer.validated_data)
        return Response(CourtSerializer(court).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Detalle de cancha",
        description="Retorna el detalle de una cancha.",
        tags=["courts"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Editar cancha",
        description="Actualiza parcialmente los campos de una cancha. Solo tenant_admin.",
        tags=["courts"],
        responses={200: CourtSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        court = self.get_object()
        serializer = CourtWriteSerializer(court, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        court = services.update_court(court=court, **serializer.validated_data)
        return Response(CourtSerializer(court).data)

    @extend_schema(
        summary="Baja de cancha",
        description=(
            "Baja lógica de la cancha (is_active=False). El registro NO se elimina físicamente. "
            "Solo tenant_admin."
        ),
        tags=["courts"],
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        court = self.get_object()
        services.deactivate_court(court=court)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScheduleBlockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el ABM de bloques horarios de disponibilidad.

    list:
      Retorna los bloques horarios del tenant activo. Filtrable por court y weekday.

    create:
      Crea un nuevo bloque horario. Solo tenant_admin.
      Valida open < close y no solapamiento en services.py.

    retrieve:
      Retorna el detalle de un bloque.

    partial_update:
      Edita un bloque. Solo tenant_admin. Revalida solapamiento excluyendo el propio id.

    destroy:
      Baja lógica (is_active=False). Solo tenant_admin. El registro NO se borra físicamente.
    """

    serializer_class = ScheduleBlockSerializer
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """
        Retorna bloques horarios del tenant activo.

        Filtros disponibles (query params):
          court    — PK de la cancha.
          weekday  — día de la semana (0-6).
          is_active — filtra por estado activo/inactivo (true/false).
        """
        qs = ScheduleBlock.objects.select_related("court").all()

        court_id = self.request.query_params.get("court")
        if court_id:
            qs = qs.filter(court_id=court_id)

        weekday = self.request.query_params.get("weekday")
        if weekday is not None:
            qs = qs.filter(weekday=weekday)

        is_active_param = self.request.query_params.get("is_active")
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")
            qs = qs.filter(is_active=is_active)

        return qs

    @extend_schema(
        summary="Listar bloques horarios",
        description=(
            "Retorna la lista paginada de bloques de disponibilidad. "
            "Filtrable por court (PK), weekday (0-6) e is_active (true/false)."
        ),
        parameters=[
            OpenApiParameter(
                name="court",
                description="Filtrar por PK de cancha.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="weekday",
                description="Filtrar por día de semana (0=lunes … 6=domingo).",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="is_active",
                description="Filtrar por estado activo: true o false.",
                required=False,
                type=bool,
            ),
        ],
        tags=["courts"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Crear bloque horario",
        description=(
            "Crea un bloque de disponibilidad para una cancha y día. "
            "Valida open_time < close_time y no solapamiento con bloques activos. "
            "Solo tenant_admin."
        ),
        tags=["courts"],
        responses={201: ScheduleBlockSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = ScheduleBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        block = services.create_schedule_block(
            court=data["court"],
            weekday=data["weekday"],
            open_time=data["open_time"],
            close_time=data["close_time"],
        )
        return Response(ScheduleBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Detalle de bloque horario",
        description="Retorna el detalle de un bloque de disponibilidad.",
        tags=["courts"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Editar bloque horario",
        description=(
            "Actualiza parcialmente un bloque de disponibilidad. "
            "Revalida solapamiento excluyendo el propio bloque. Solo tenant_admin."
        ),
        tags=["courts"],
        responses={200: ScheduleBlockSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        block = self.get_object()
        serializer = ScheduleBlockSerializer(block, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        block = services.update_schedule_block(
            schedule_block=block,
            **serializer.validated_data,
        )
        return Response(ScheduleBlockSerializer(block).data)

    @extend_schema(
        summary="Baja de bloque horario",
        description=(
            "Baja lógica del bloque (is_active=False). El registro NO se elimina físicamente. "
            "Solo tenant_admin."
        ),
        tags=["courts"],
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        block = self.get_object()
        services.deactivate_schedule_block(schedule_block=block)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SlotBlockViewSet(viewsets.GenericViewSet):
    """
    ViewSet para bloqueos manuales de slots (torneos, mantenimiento, etc.).

    list:
      GET /api/slot-blocks/?court=ID&date=YYYY-MM-DD
      Solo operator o admin. Filtra por cancha y/o fecha (start_dt__date).

    create:
      POST /api/slot-blocks/
      Crea un bloqueo de slot. Solo operator o admin.
      Asigna created_by = request.user y delega a create_slot_block() del service.

    destroy:
      DELETE /api/slot-blocks/{id}/
      Baja lógica (is_active=False). Solo operator o admin.
      Llama a delete_slot_block() del service (NO instance.delete()).
    """

    serializer_class = SlotBlockSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        from apps.bookings.permissions import IsOperatorOrAdmin
        return [IsAuthenticated(), IsOperatorOrAdmin()]

    def get_queryset(self):
        """
        Retorna bloqueos activos del tenant activo.

        Filtros disponibles (query params):
          court — PK de la cancha.
          date  — fecha en YYYY-MM-DD; filtra por start_dt__date.
        """
        qs = SlotBlock.objects.select_related("court", "created_by").filter(is_active=True)

        court_id = self.request.query_params.get("court")
        if court_id:
            qs = qs.filter(court_id=court_id)

        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(start_dt__date=date_param)

        return qs

    @extend_schema(
        summary="Listar bloqueos de slots",
        description=(
            "Retorna bloqueos de slots activos del tenant. "
            "Filtrable por court (PK) y date (YYYY-MM-DD). "
            "Solo operator o admin."
        ),
        parameters=[
            OpenApiParameter(
                name="court",
                description="Filtrar por PK de cancha.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="date",
                description="Filtrar por fecha de inicio del bloqueo (YYYY-MM-DD).",
                required=False,
                type=str,
            ),
        ],
        tags=["courts"],
        responses={200: SlotBlockSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(SlotBlockSerializer(page, many=True).data)
        return Response(SlotBlockSerializer(qs, many=True).data)

    @extend_schema(
        summary="Crear bloqueo de slot",
        description=(
            "Crea un bloqueo manual de slot (torneo, mantenimiento, cierre anticipado). "
            "Valida start_dt < end_dt. Solo operator o admin."
        ),
        tags=["courts"],
        request=SlotBlockSerializer,
        responses={201: SlotBlockSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = SlotBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        block = services.create_slot_block(
            court=data["court"],
            start_dt=data["start_dt"],
            end_dt=data["end_dt"],
            reason=data.get("reason", ""),
            created_by=request.user,
        )
        return Response(SlotBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Eliminar bloqueo de slot",
        description=(
            "Baja lógica del bloqueo (is_active=False). El registro NO se elimina físicamente. "
            "Solo operator o admin."
        ),
        tags=["courts"],
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        block = self.get_object()
        services.delete_slot_block(block)
        return Response(status=status.HTTP_204_NO_CONTENT)
