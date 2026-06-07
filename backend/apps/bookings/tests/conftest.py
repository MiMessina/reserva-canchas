"""
conftest.py — fixtures para tests del motor de reservas.

Configura el entorno de pruebas:
  - Desactiva el throttling de DRF para que los tests no sean afectados por
    el rate limiting activado en el FIX 1 del security review. El throttle
    usa LocMemCache y su estado persiste entre tests en la misma sesión de pytest,
    causando 429 en llamadas repetidas a /api/auth/login/. En tests siempre
    se deshabilita el throttle (Django test runner también lo hace implícitamente
    en algunos setups, pero lo hacemos explícito aquí para TenantTestCase).

QA: agregar aquí los fixtures críticos para Sprint 1+:

  @pytest.fixture
  def active_court(db):
      # Court activa con slot_duration_minutes=60
      ...

  @pytest.fixture
  def schedule_block(active_court):
      # ScheduleBlock: lunes-viernes 08:00-22:00
      ...

  @pytest.fixture
  def player_user(db):
      # User con role=player
      ...

  @pytest.fixture
  def operator_user(db):
      # User con role=operator
      ...

CRITICO — test de concurrencia:
  El test de dos reservas simultáneas al mismo turno requiere threading real:

  import threading
  results = []
  def attempt_booking():
      try:
          booking = create_booking(court=court, start_dt=slot, user=user)
          results.append(("ok", booking))
      except SlotAlreadyBooked:
          results.append(("error", None))

  t1 = threading.Thread(target=attempt_booking)
  t2 = threading.Thread(target=attempt_booking)
  t1.start(); t2.start()
  t1.join(); t2.join()

  ok_count = sum(1 for r, _ in results if r == "ok")
  assert ok_count == 1, "Solo una reserva debe ganar"
"""

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def disable_throttling(settings):
    """
    Desactiva el throttling de DRF en todos los tests de bookings.

    El rate limiting activado en el FIX 1 usa LocMemCache, cuyo estado persiste
    entre tests en la misma sesión de pytest. Esto causa 429 en llamadas repetidas
    a /api/auth/login/ durante el setUp() de TenantTestCase cuando se corren
    todos los tests seguidos.

    Esta fixture sobrescribe las clases de throttle a lista vacía para todos
    los tests de este directorio.
    """
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
