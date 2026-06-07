"""
Views — app bookings

Sprint 0: placeholder.

Endpoints planificados (Sprint 1+):
  POST   /api/bookings/                  — crear reserva (jugador o cajero)
  GET    /api/bookings/                  — listado de reservas (staff; jugador solo las suyas)
  GET    /api/bookings/{id}/             — detalle de reserva
  POST   /api/bookings/{id}/confirm/     — PENDING_PAYMENT -> CONFIRMED (operator/admin)
  POST   /api/bookings/{id}/cancel/      — -> CANCELLED (jugador solo la suya; staff cualquiera)
  POST   /api/bookings/{id}/complete/    — CONFIRMED -> COMPLETED (staff)

Toda lógica de transición y concurrencia va en bookings/services.py.
"""
