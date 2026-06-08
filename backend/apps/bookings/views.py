"""
Views — app bookings

ViewSets y Views para Booking, CashMovement y disponibilidad.

Endpoints registrados en apps/bookings/urls.py:
  GET    /api/bookings/                     — listado (admin/operator)
  POST   /api/bookings/                     — crear reserva (AllowAny)
  GET    /api/bookings/{id}/                — detalle (admin/operator/propio jugador)
  POST   /api/bookings/{id}/confirm/        — confirmar (operator/admin)
  POST   /api/bookings/{id}/cancel/         — cancelar (autenticado; jugador solo la suya)
  POST   /api/bookings/{id}/complete/       — completar (operator/admin)
  GET    /api/cash-movements/               — caja (operator/admin; filtro ?date=YYYY-MM-DD)
  GET    /api/courts/{court_id}/availability/?date=YYYY-MM-DD  — grilla (AllowAny)

Reglas:
  - Toda la lógica de negocio delega a bookings/services.py.
  - Los players solo ven sus propias reservas (filtrado en get_queryset).
  - Un player solo puede cancelar su propia reserva (verificado en cancel()).
  - AllowAny en create y availability: reservas de invitados sin JWT (ADR-008).
  - La concurrencia la garantiza el service con select_for_update().
"""

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, CashMovement
from apps.bookings.permissions import IsOperatorOrAdmin
from apps.bookings.selectors import get_availability
from apps.bookings.serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingPublicSerializer,
    BookingSerializer,
    BookingStaffSerializer,
    CashMovementSerializer,
)
from apps.bookings.services import (
    cancel_booking,
    complete_booking,
    confirm_booking,
    create_booking,
)
from apps.courts.models import Court

logger = logging.getLogger(__name__)


class BookingViewSet(viewsets.GenericViewSet):
    """
    ViewSet para el motor de reservas.

    list:
      Listado de reservas del tenant. Solo operator/admin.
      Players obtienen 403. Filtros: court, status, date_from, date_to.

    create:
      Crear reserva. AllowAny (invitado o jugador autenticado).
      La lógica XOR user/guest se valida en el service.

    retrieve:
      Detalle de reserva. Admin/operator ven cualquiera.
      El jugador solo ve las suyas (filtrado en get_queryset).

    confirm:
      PENDING_PAYMENT → CONFIRMED. Solo operator/admin.

    cancel:
      PENDING_PAYMENT|CONFIRMED → CANCELLED. Autenticado.
      El jugador solo puede cancelar su propia reserva.

    complete:
      CONFIRMED → COMPLETED. Solo operator/admin.
    """

    # -----------------------------------------------------------------------
    # Helpers internos
    # -----------------------------------------------------------------------

    def _get_booking_serializer(self, *args, **kwargs):
        """
        Retorna el serializer apropiado según el rol del usuario.

        Staff (operator / tenant_admin): BookingStaffSerializer (incluye contacto).
        Resto (player, invitado, anónimo): BookingPublicSerializer (sin datos personales).
        """
        if (
            self.request.user.is_authenticated
            and self.request.user.is_staff_of_complex
        ):
            return BookingStaffSerializer(*args, **kwargs)
        return BookingPublicSerializer(*args, **kwargs)

    def _get_staff_booking(self, pk):
        """
        Obtiene una reserva activa del tenant actual.
        Uso exclusivo de acciones staff (confirm, complete).
        Delega en get_queryset() para respetar el scope del tenant.
        """
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action in ("confirm", "complete"):
            return [IsAuthenticated(), IsOperatorOrAdmin()]
        # list, retrieve, cancel: requieren auth
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Retorna el queryset base de Booking activos del tenant.

        Filtros disponibles (query params):
          court     — PK de la cancha.
          status    — estado de la reserva.
          date_from — fecha de inicio (YYYY-MM-DD), filtro sobre start_dt.
          date_to   — fecha de fin (YYYY-MM-DD).

        Si el usuario es un player, solo ve sus propias reservas.
        """
        qs = Booking.objects.filter(is_active=True).select_related("court", "user")

        # Filtros explícitos (RULES.md §5, API_GUIDELINES.md §6)
        court_id = self.request.query_params.get("court")
        status_param = self.request.query_params.get("status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if court_id:
            qs = qs.filter(court_id=court_id)
        if status_param:
            qs = qs.filter(status=status_param)
        if date_from:
            qs = qs.filter(start_dt__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_dt__date__lte=date_to)

        # Players solo ven sus propias reservas (RBAC.md §4)
        user = self.request.user
        if user.is_authenticated and user.is_player:
            qs = qs.filter(user=user)

        return qs

    @extend_schema(
        summary="Listar reservas",
        description=(
            "Retorna el listado paginado de reservas del complejo. "
            "Solo operator y admin. Players obtienen 403. "
            "Filtros: court (PK), status, date_from, date_to (YYYY-MM-DD)."
        ),
        parameters=[
            OpenApiParameter("court", type=int, description="Filtrar por PK de cancha."),
            OpenApiParameter("status", type=str, description="Filtrar por estado."),
            OpenApiParameter("date_from", type=str, description="Fecha desde (YYYY-MM-DD)."),
            OpenApiParameter("date_to", type=str, description="Fecha hasta (YYYY-MM-DD)."),
        ],
        tags=["bookings"],
        responses={200: BookingSerializer(many=True)},
    )
    def list(self, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_player:
            return Response(
                {"error": {"code": "TENANT_FORBIDDEN", "message": "Los jugadores no pueden ver el listado completo."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(BookingStaffSerializer(page, many=True).data)
        return Response(BookingStaffSerializer(qs, many=True).data)

    @extend_schema(
        summary="Crear reserva",
        description=(
            "Crea una reserva en estado PENDING_PAYMENT. "
            "Acceso público (AllowAny): invitados sin JWT o jugadores autenticados. "
            "Regla XOR (ADR-008): si hay JWT no enviar guest_name/guest_phone; "
            "si no hay JWT son obligatorios."
        ),
        tags=["bookings"],
        request=BookingCreateSerializer,
        responses={201: BookingSerializer},
    )
    def create(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user if request.user.is_authenticated else None

        booking = create_booking(
            court_id=data["court"].pk,
            start_dt=data["start_dt"],
            user=user,
            guest_name=data.get("guest_name", ""),
            guest_phone=data.get("guest_phone", ""),
        )
        return Response(BookingPublicSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Detalle de reserva",
        description=(
            "Retorna el detalle de una reserva. "
            "Admin y operator ven cualquier reserva del tenant. "
            "El jugador solo ve sus propias reservas (otras retornan 404)."
        ),
        tags=["bookings"],
        responses={200: BookingSerializer},
    )
    def retrieve(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(self._get_booking_serializer(booking).data)

    @extend_schema(
        summary="Confirmar reserva",
        description=(
            "Transición PENDING_PAYMENT → CONFIRMED. "
            "Genera un CashMovement. Solo operator o admin."
        ),
        tags=["bookings"],
        responses={200: BookingSerializer},
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self._get_staff_booking(pk)
        updated = confirm_booking(booking=booking, operator=request.user)
        return Response(BookingStaffSerializer(updated).data)

    @extend_schema(
        summary="Cancelar reserva",
        description=(
            "Transición PENDING_PAYMENT|CONFIRMED → CANCELLED. "
            "El jugador solo puede cancelar su propia reserva. "
            "Operator y admin pueden cancelar cualquier reserva del tenant."
        ),
        tags=["bookings"],
        request=BookingCancelSerializer,
        responses={200: BookingSerializer},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # Para cancel usamos el queryset completo de reservas activas del tenant
        # (sin el filtro de usuario de get_queryset) para poder evaluar el ownership
        # y retornar 403 en lugar de 404. Un 404 ocultaría la existencia del recurso,
        # pero la semántica correcta es 403: "el recurso existe pero no tenés permiso".
        booking = get_object_or_404(
            Booking.objects.filter(is_active=True).select_related("court", "user"),
            pk=pk,
        )

        # Verificación de ownership defensiva (RBAC.md §4).
        # Si el usuario NO es staff del complejo, solo puede cancelar su propia reserva
        # (booking.user == request.user). Esto cubre players y cualquier rol futuro
        # que no sea staff, en lugar de checar exclusivamente is_player.
        user = request.user
        if not (user.is_authenticated and user.is_staff_of_complex):
            if booking.user != user:
                return Response(
                    {
                        "error": {
                            "code": "TENANT_FORBIDDEN",
                            "message": "No podés cancelar una reserva que no es tuya.",
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = cancel_booking(
            booking=booking,
            cancelled_by=user if user.is_authenticated else None,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(self._get_booking_serializer(updated).data)

    @extend_schema(
        summary="Completar reserva",
        description=(
            "Transición CONFIRMED → COMPLETED. "
            "Solo válido después del end_dt del turno. Solo operator o admin."
        ),
        tags=["bookings"],
        responses={200: BookingSerializer},
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = self._get_staff_booking(pk)
        updated = complete_booking(booking=booking)
        return Response(BookingStaffSerializer(updated).data)


class CashMovementViewSet(viewsets.GenericViewSet):
    """
    ViewSet de solo lectura para movimientos de caja.

    list:
      GET /api/cash-movements/?date=YYYY-MM-DD
      Solo operator o admin. Filtro por fecha obligatorio recomendado.
    """

    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get_queryset(self):
        # Solo movimientos de reservas activas (soft-delete awareness)
        qs = CashMovement.objects.select_related(
            "booking", "booking__court", "operator"
        ).filter(booking__is_active=True)

        date = self.request.query_params.get("date")
        if date:
            # Filtrar por fecha en hora Buenos Aires: se convierte el día local
            # a un rango UTC para evitar desfase de 3 horas (UTC-3).
            from datetime import datetime, date as date_type
            from zoneinfo import ZoneInfo
            BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
            try:
                day = date_type.fromisoformat(date)
            except ValueError:
                # Fecha inválida: marcamos el flag para retornar 400 en list()
                self._invalid_date = True
                return CashMovement.objects.none()
            self._invalid_date = False
            day_start = datetime(day.year, day.month, day.day, 0, 0, tzinfo=BUENOS_AIRES)
            day_end = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=BUENOS_AIRES)
            qs = qs.filter(created_at__gte=day_start, created_at__lte=day_end)
        else:
            self._invalid_date = False
        return qs

    @extend_schema(
        summary="Listar movimientos de caja",
        description=(
            "Retorna el listado paginado de movimientos de caja del tenant. "
            "Solo operator o admin. Filtro recomendado: ?date=YYYY-MM-DD."
        ),
        parameters=[
            OpenApiParameter("date", type=str, description="Filtrar por fecha (YYYY-MM-DD)."),
        ],
        tags=["cashbox"],
        responses={200: CashMovementSerializer(many=True)},
    )
    def list(self, request):
        qs = self.get_queryset()
        if getattr(self, "_invalid_date", False):
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Formato de fecha inválido. Usar YYYY-MM-DD.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(CashMovementSerializer(page, many=True).data)
        return Response(CashMovementSerializer(qs, many=True).data)


class AvailabilityView(APIView):
    """
    Vista de grilla de disponibilidad para una cancha.

    GET /api/courts/{court_id}/availability/?date=YYYY-MM-DD

    Pública (AllowAny): el jugador no necesita JWT para ver la grilla.
    El tenant se resuelve por dominio (middleware de django-tenants).

    Respuesta:
      {
        "date": "YYYY-MM-DD",
        "court": <id>,
        "slots": [
          {"start_dt": "...", "end_dt": "...", "is_available": true/false},
          ...
        ]
      }
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Grilla de disponibilidad",
        description=(
            "Retorna los slots disponibles para una cancha en una fecha (hora Buenos Aires). "
            "Público: no requiere JWT. El tenant se resuelve por dominio."
        ),
        parameters=[
            OpenApiParameter(
                "date",
                type=str,
                required=True,
                description="Fecha en formato YYYY-MM-DD (hora Buenos Aires).",
            ),
        ],
        tags=["bookings"],
    )
    def get(self, request, court_id):
        from datetime import date as date_type, timedelta as td

        court = get_object_or_404(Court, pk=court_id, is_active=True)

        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "El parámetro 'date' es obligatorio. Formato: YYYY-MM-DD.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar formato antes del límite de 90 días
        try:
            requested_date = date_type.fromisoformat(date_str)
        except ValueError:
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Formato de fecha inválido. Usar YYYY-MM-DD.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limitar a 90 días de anticipación para evitar abuso y saturación de DB
        max_date = date_type.today() + td(days=90)
        if requested_date > max_date:
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No se puede consultar disponibilidad con más de 90 días de anticipación.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            slots = get_availability(court, date_str)
        except ValueError:
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Formato de fecha inválido. Usar YYYY-MM-DD.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"date": date_str, "court": court_id, "slots": slots})
