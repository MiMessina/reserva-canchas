"""
Service layer — app cashbox

Sprint 0: placeholder.

Toda lógica de caja vive aquí (RULES.md). Nunca en views ni serializers.

Expansión Sprint 1+:
  - register_cash_movement(*, booking, operator, amount) -> CashMovement
    (se llama automáticamente desde bookings/services.py al confirmar una reserva)
  - get_daily_summary(date: date) -> dict
    (total de señas confirmadas en el día para el tenant activo)
"""
