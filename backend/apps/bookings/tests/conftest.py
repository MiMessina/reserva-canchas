"""
conftest.py — fixtures para tests del motor de reservas.

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
