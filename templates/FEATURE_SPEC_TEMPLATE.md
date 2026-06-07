# FEATURE_SPEC_TEMPLATE.md
# Especificación Funcional de Feature

> Plantilla reutilizable. Más abajo hay un **ejemplo resuelto** ("Motor de Reservas") como referencia para el equipo.

## 1. Nombre de la feature

`[Nombre]`

## 2. Problema que resuelve

`[Descripción del problema]`

## 3. Usuario objetivo

| Actor | Necesidad |
|---|---|
| `[Actor]` | `[Necesidad]` |

## 4. Flujo principal

1. `[Paso 1]`
2. `[Paso 2]`

## 5. Reglas de negocio

| Regla | Descripción |
|---|---|
| `[Regla 1]` | `[Descripción]` |

## 6. Estados involucrados

| Estado | Descripción |
|---|---|
| `[Estado]` | `[Descripción]` |

## 7. Permisos

| Acción | Rol permitido | Scope |
|---|---|---|
| `[Acción]` | `[Rol]` | `[Scope]` |

## 8. API requerida

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/...` | `[Descripción]` |

## 9. UI requerida

- `[Pantalla / componente / estados]`

## 10. Auditoría

- `[Evento]`

## 11. Notificaciones

- `[Notificación]`

## 12. Criterios de aceptación

- `[Criterio]`

## 13. Fuera de alcance

- `[No incluido]`

## 14. Riesgos

- `[Riesgo]`

---

# EJEMPLO RESUELTO — Motor de Reservas

## 1. Nombre de la feature

Motor de Reservas (creación de reserva del jugador con mitigación de concurrencia)

## 2. Problema que resuelve

Hoy el complejo toma reservas por WhatsApp y las anota en Excel, lo que produce overbooking (dos personas en la misma cancha y horario) y pérdida de turnos. El jugador necesita reservar solo, desde el celular, viendo la disponibilidad real.

## 3. Usuario objetivo

| Actor | Necesidad |
|---|---|
| Jugador (`player`) | Ver turnos libres y reservar uno sin que lo atienda un humano. |
| Cajero (`operator`) | Que la reserva quede registrada y pendiente de seña para confirmarla luego. |

## 4. Flujo principal

1. El jugador abre la URL del complejo (tenant resuelto por dominio) y ve la grilla pública.
2. Selecciona cancha, día y turno disponible.
3. Confirma la reserva (con sus datos mínimos / logueado como player).
4. El backend valida disponibilidad con bloqueo pesimista y crea la reserva en `PENDING_PAYMENT`.
5. El jugador recibe los datos para transferir la seña.
6. El cajero, más tarde, confirma la reserva (otra feature: confirmación).

## 5. Reglas de negocio

| Regla | Descripción |
|---|---|
| No overbooking | No puede existir otra reserva `PENDING_PAYMENT`/`CONFIRMED` para la misma cancha y horario. |
| Bloqueo pesimista | La validación corre dentro de una transacción con `select_for_update()` sobre la cancha. |
| No reservar en el pasado | El turno debe ser futuro respecto del `now()` en UTC. |
| Cancha activa y dentro de horario | La cancha debe estar `is_active` y el turno dentro del `ScheduleBlock`. |
| Nace pendiente | La reserva se crea en `PENDING_PAYMENT` (pago de seña por transferencia, manual). |

## 6. Estados involucrados

| Estado | Descripción |
|---|---|
| `PENDING_PAYMENT` | Estado inicial tras crear la reserva. |
| `CONFIRMED` / `CANCELLED` | Transiciones posteriores (otras features). |

## 7. Permisos

| Acción | Rol permitido | Scope |
|---|---|---|
| Ver grilla pública | Cualquiera | public (acotado al tenant del dominio) |
| Crear reserva | `player`, `operator`, `tenant_admin` | tenant |

## 8. API requerida

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/courts/{id}/availability/?date=YYYY-MM-DD` | Turnos libres de la cancha ese día. |
| POST | `/api/bookings/` | Crea la reserva (`PENDING_PAYMENT`). |

Respuesta de error ante overbooking:

```json
{ "error": { "code": "SLOT_ALREADY_BOOKED", "message": "Ese turno ya fue reservado. Elegí otro horario." } }
```

## 9. UI requerida

- Pantalla grilla pública (mobile-first) con turnos libres/ocupados.
- Modal/flujo de confirmación de reserva.
- Estado vacío ("No hay turnos disponibles ese día").
- Estado error: mostrar `SLOT_ALREADY_BOOKED` y refrescar la grilla.
- Pantalla con instrucciones de transferencia de la seña.

## 10. Auditoría

- `booking.created` (tenant, jugador, cancha, datetime).
- `booking.overbooking_rejected` (para diagnóstico).

## 11. Notificaciones

- Post-MVP: aviso al cajero por turno nuevo pendiente de seña (vía WhatsApp/Celery).

## 12. Criterios de aceptación

- El jugador crea una reserva `PENDING_PAYMENT` desde la grilla.
- Dos reservas simultáneas al mismo turno → solo una se crea; la otra recibe `SLOT_ALREADY_BOOKED`.
- Reservar en el pasado o en cancha inactiva → rechazado.
- La reserva queda aislada al tenant correcto.
- Existen tests de creación, concurrencia, validación y aislamiento.

## 13. Fuera de alcance

- Pago automático de la seña (es transferencia manual).
- Confirmación de la reserva (feature separada del cajero).
- Notificaciones automáticas.

## 14. Riesgos

- Condición de carrera si no se usa `select_for_update()` correctamente.
- Errores de timezone (turno guardado/comparado fuera de UTC).
- Bloqueos largos si la transacción hace trabajo pesado dentro del lock.
