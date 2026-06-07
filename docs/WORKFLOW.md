# WORKFLOW.md
# Workflow, Estados y Transiciones — SaaS Gestión de Canchas

## 1. Objetivo

Definir cómo se mueve la **Reserva** (entidad central del sistema), qué estados existen, qué transiciones son válidas y qué reglas las gobiernan. Esto evita que la IA invente flujos paralelos.

## 2. Entidades con workflow

| Entidad | Tiene estados | Documento fuente |
|---|---|---|
| `Booking` (Reserva) | Sí | Este documento + `PROJECT_CONTEXT.md` |
| `Court` (Cancha) | Sí (binario: activa/inactiva vía `is_active`) | `PROJECT_CONTEXT.md` |
| `CashMovement` | No (registro inmutable de caja) | `ARCHITECTURE.md` |

## 3. Estados permitidos de la Reserva (`Booking`)

| Estado | Descripción | Visible para jugador | Estado final |
|---|---|---:|---:|
| `PENDING_PAYMENT` | Reserva creada, esperando seña/transferencia. | Sí | No |
| `CONFIRMED` | El cajero verificó la seña; el turno queda asegurado. | Sí | No |
| `CANCELLED` | Anulada (por el jugador, el cajero o por falta de pago). | Sí | Sí |
| `COMPLETED` | El turno ya se jugó. | Sí | Sí |

> Regla clave: una reserva **nace** en `PENDING_PAYMENT` porque el pago de la seña es por transferencia externa con conciliación manual.

## 4. Transiciones permitidas

| Desde | Hacia | Quién puede hacerlo | Validaciones |
|---|---|---|---|
| (nuevo) | `PENDING_PAYMENT` | Jugador / Cajero | Cancha activa, horario dentro de disponibilidad, **no en el pasado**, sin overbooking (`select_for_update()`) |
| `PENDING_PAYMENT` | `CONFIRMED` | Cajero / Admin | Seña verificada → genera `CashMovement` |
| `PENDING_PAYMENT` | `CANCELLED` | Jugador / Cajero / sistema | Motivo (ej: no pagó la seña) |
| `CONFIRMED` | `CANCELLED` | Cajero / Admin | Motivo obligatorio; revertir/anotar movimiento de caja |
| `CONFIRMED` | `COMPLETED` | Cajero / Admin / sistema | Solo después de la fecha/hora del turno |

## 5. Transiciones prohibidas

| Desde | Hacia | Motivo |
|---|---|---|
| `CANCELLED` | cualquier otro | Una reserva cancelada no se "revive"; se crea una nueva |
| `COMPLETED` | cualquier otro | El turno ya ocurrió |
| `PENDING_PAYMENT` | `COMPLETED` | No se completa un turno sin haber sido confirmado |

## 6. Eventos auditables del workflow

- creación de reserva (con tenant, jugador, cancha, datetime);
- confirmación de seña (cambio a `CONFIRMED` + movimiento de caja);
- cancelación (con motivo y autor);
- completado del turno;
- intento de overbooking rechazado (útil para diagnóstico).

## 7. Reglas de implementación

- Todas las transiciones se validan en `bookings/services.py` (backend).
- El frontend puede ocultar botones (ej: no mostrar "Confirmar" a un jugador), pero **no** decide la validez final.
- La creación de reserva corre dentro de una transacción con `select_for_update()` sobre la cancha/turno.
- **Duración y solapamiento:** el turno dura `Court.slot_duration_minutes`; la reserva ocupa `[start_dt, end_dt)` con `end_dt = start_dt + slot_duration_minutes`. El overbooking se detecta por **solapamiento de intervalos** sobre la misma cancha entre reservas en `PENDING_PAYMENT`/`CONFIRMED`, **no** por igualdad exacta de `start_dt` (ver `DER.md` y ADR-006).
- Cada transición relevante genera auditoría.
- Las reglas de workflow tienen tests, incluyendo el test de concurrencia (dos reservas simultáneas al mismo turno → solo una gana).

## 8. Sprint 0

Durante Sprint 0 **no** se programa el motor de reservas ni features de negocio. Sprint 0 construye:

- repos backend y frontend;
- multi-tenant base (`django-tenants`) y custom user;
- autenticación JWT y permisos base;
- estructura modular de apps;
- Docker + PostgreSQL;
- contrato de API (Swagger/mocks);
- documentación viva.

## 9. Definition of Done para el flujo de reserva

El flujo de reserva está completo si:

- el backend valida todas las transiciones y la concurrencia;
- el jugador puede crear una reserva (`PENDING_PAYMENT`) desde la grilla pública;
- el cajero puede confirmarla (`CONFIRMED`) y queda en la caja del día;
- hay tests (incluido overbooking y aislamiento multi-tenant);
- hay auditoría de cada transición;
- hay manejo de errores y estados vacíos en el front;
- respeta permisos (RBAC) y el aislamiento por tenant;
- está documentado en Swagger.
