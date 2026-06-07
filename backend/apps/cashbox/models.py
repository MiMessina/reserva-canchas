"""
Modelos — app cashbox

Sprint 0: VACÍO intencionalmente.

El modelo CashMovement se construye en Sprint 1+.
Ver docs/DER.md para la especificación completa.

CashMovement:
  - booking (FK -> bookings.Booking)
  - operator (FK -> users.User)
  - amount (decimal)
  - movement_date (date)
  - created_at (inmutable: no se edita ni borra físicamente)

Regla: CashMovement es inmutable. No tiene is_active ni updated_at.
No se edita ni se borra; ante un error se genera un movimiento de corrección.
"""
