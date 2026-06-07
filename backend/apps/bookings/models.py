"""
Modelos — app bookings

Sprint 0: VACÍO intencionalmente.

Los modelos Booking se construyen en Sprint 1+.
Ver docs/DER.md para la especificación completa.

Booking:
  - user (FK -> users.User, nullable — ADR-008: jugador registrado o invitado)
  - guest_name (str, nullable), guest_phone (str, nullable)
  - court (FK -> courts.Court)
  - start_dt (datetime UTC), end_dt (datetime UTC)
  - status: PENDING_PAYMENT | CONFIRMED | CANCELLED | COMPLETED
  - price (decimal)
  - is_active, created_at, updated_at

Regla XOR (ADR-008): user XOR guest_* (uno u otro, nunca ambos ni ninguno).
Validada en bookings/services.py.
"""
