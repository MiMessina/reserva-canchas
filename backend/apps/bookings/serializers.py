"""
Serializers — app bookings

Sprint 0: placeholder.

Los serializers validan estructura, no gobiernan negocio (RULES.md).
El XOR user/guest, la concurrencia y las transiciones de estado viven
en bookings/services.py.

Expansión Sprint 1+:
  - BookingSerializer (lectura, lista)
  - BookingDetailSerializer (lectura, detalle)
  - CreateBookingSerializer (escritura: user o guest_name+guest_phone)
  - ConfirmBookingSerializer (solo confirmación: sin campos, acción por URL)
  - CancelBookingSerializer (motivo de cancelación)
"""
