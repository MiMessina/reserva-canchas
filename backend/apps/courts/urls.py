"""
URLs — app courts

Registra los ViewSets de Court, ScheduleBlock y SlotBlock con DefaultRouter.

Rutas generadas:
  /api/courts/                 GET (list), POST (create)
  /api/courts/{id}/            GET (retrieve), PATCH (partial_update), DELETE (destroy)
  /api/schedule-blocks/        GET (list), POST (create)
  /api/schedule-blocks/{id}/   GET (retrieve), PATCH (partial_update), DELETE (destroy)
  /api/slot-blocks/            GET (list), POST (create)
  /api/slot-blocks/{id}/       DELETE (destroy — baja lógica)

Incluido en config/urls.py con:
    path("api/", include("apps.courts.urls"))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.courts.views import CourtViewSet, ScheduleBlockViewSet, SlotBlockViewSet

router = DefaultRouter()
router.register(r"courts", CourtViewSet, basename="court")
router.register(r"schedule-blocks", ScheduleBlockViewSet, basename="schedule-block")
router.register(r"slot-blocks", SlotBlockViewSet, basename="slot-block")

urlpatterns = [
    path("", include(router.urls)),
]
