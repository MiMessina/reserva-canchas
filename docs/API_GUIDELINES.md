# API_GUIDELINES.md
# Guía de Diseño de APIs — SaaS Gestión de Canchas

## 1. Principio

API-First: el contrato (Swagger/OpenAPI vía `drf-spectacular`) es la fuente de verdad que destraba al frontend. Las APIs deben ser consistentes, predecibles, documentadas, seguras y multi-tenant.

## 2. Convenciones de naming

Sustantivos en plural:

```txt
/api/courts/
/api/schedule-blocks/
/api/bookings/
/api/cash-movements/
```

Evitar nombres ambiguos:

```txt
/api/do_stuff/
/api/process/
/api/data/
```

## 3. Métodos HTTP

| Método | Uso |
|---|---|
| GET | Lectura (listar canchas, ver grilla, listar reservas) |
| POST | Creación o acción controlada (crear reserva) |
| PUT | Reemplazo completo |
| PATCH | Actualización parcial (editar precio de una cancha) |
| DELETE | Baja lógica (`is_active = false`), nunca borrado físico |

## 4. Acciones especiales (transiciones de dominio)

Las transiciones de estado de la reserva van como sub-recursos de acción:

```txt
POST /api/bookings/{id}/confirm/      # PENDING_PAYMENT -> CONFIRMED (cajero)
POST /api/bookings/{id}/cancel/       # -> CANCELLED (con motivo)
POST /api/bookings/{id}/complete/     # CONFIRMED -> COMPLETED
GET  /api/courts/{id}/availability/   # grilla de disponibilidad de una cancha
GET  /api/cash-movements/?date=YYYY-MM-DD   # caja del día
```

## 5. Paginación

Todo listado grande se pagina (reservas, movimientos de caja):

```json
{
  "count": 120,
  "next": "...",
  "previous": null,
  "results": []
}
```

## 6. Filtros

Filtros explícitos, clave para la grilla y la caja:

```txt
/api/bookings/?court=3&status=CONFIRMED&date_from=2026-06-01&date_to=2026-06-07
/api/courts/?type=PADEL&is_active=true
```

> Las fechas en los filtros y respuestas viajan en ISO 8601 con timezone; el backend trabaja en UTC.

## 7. Errores

Formato estándar. El motor de reservas usa códigos claros para que el front muestre el mensaje correcto:

```json
{
  "error": {
    "code": "SLOT_ALREADY_BOOKED",
    "message": "Ese turno ya fue reservado. Elegí otro horario.",
    "details": {
      "court": 3,
      "datetime": "2026-06-05T20:00:00Z"
    }
  }
}
```

Códigos de negocio sugeridos: `SLOT_ALREADY_BOOKED` (overbooking evitado), `BOOKING_IN_PAST` (turno vencido), `COURT_INACTIVE`, `OUTSIDE_SCHEDULE`, `INVALID_TRANSITION`, `VALIDATION_ERROR`, `TENANT_FORBIDDEN`.

## 8. Versionado

Si un cambio rompe el contrato, se versiona y se registra ADR:

```txt
/api/v1/bookings/
/api/v2/bookings/
```

## 9. Seguridad

- Cada endpoint tiene permisos explícitos (ver `RBAC.md`).
- Validar JWT y pertenencia al tenant (la grilla pública igual queda acotada al tenant del dominio).
- No exponer campos sensibles del jugador.
- Rate limit en endpoints públicos (grilla, creación de reserva por el jugador).
- Auditar creación/confirmación/cancelación de reservas y movimientos de caja.

## 10. Documentación

Cada endpoint documenta en Swagger:

- propósito;
- permisos requeridos;
- request / response;
- errores posibles (incluidos los códigos de negocio);
- filtros y paginación;
- side effects (ej: confirmar reserva genera movimiento de caja);
- eventos auditables.

## 11. Checklist antes de crear un endpoint

- ¿Ya existe uno similar?
- ¿Respeta el naming en plural?
- ¿Tiene permisos y valida tenant?
- ¿Tiene tests (incluido permisos y aislamiento)?
- ¿Está documentado en Swagger?
- ¿Necesita auditoría?
- Si toca reservas, ¿respeta la concurrencia y los estados del `WORKFLOW.md`?
