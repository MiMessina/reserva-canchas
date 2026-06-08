"""
URLs — app bookings

Registra los ViewSets de Booking y CashMovement con DefaultRouter,
y las views de disponibilidad, dashboard y grilla multi-cancha como rutas explícitas.

Rutas generadas:
  GET    /api/bookings/                     — listado (admin/operator)
  POST   /api/bookings/                     — crear reserva (AllowAny)
  GET    /api/bookings/{id}/                — detalle
  POST   /api/bookings/{id}/confirm/        — confirmar (operator/admin)
  POST   /api/bookings/{id}/cancel/         — cancelar
  POST   /api/bookings/{id}/complete/       — completar (operator/admin)
  GET    /api/cash-movements/               — caja (operator/admin)
  GET    /api/cash-movements/export/        — exportar CSV (operator/admin)
  GET    /api/dashboard/                    — resumen del día (operator/admin)
  GET    /api/bookings/daily-grid/          — grilla multi-cancha del día (operator/admin)
  GET    /api/courts/{court_id}/availability/?date=YYYY-MM-DD  — grilla (AllowAny)

Incluido en config/urls.py con:
    path("api/", include("apps.bookings.urls"))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.bookings.views import AvailabilityView, BookingViewSet, CashMovementViewSet, DailyGridView, DashboardView

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"cash-movements", CashMovementViewSet, basename="cash-movement")

urlpatterns = [
    # Las rutas explícitas deben preceder a include(router.urls) para evitar que
    # el patrón genérico {pk}/ del router capture rutas como bookings/daily-grid/.
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("bookings/daily-grid/", DailyGridView.as_view(), name="booking-daily-grid"),
    path(
        "courts/<int:court_id>/availability/",
        AvailabilityView.as_view(),
        name="court-availability",
    ),
    path("", include(router.urls)),
]
