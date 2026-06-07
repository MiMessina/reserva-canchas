# ADR-008: Reserva del jugador como invitado o con cuenta (ambos)

**Fecha:** 2026-06-02
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator) / Erik (Backend API)

## Contexto

El jugador necesita reservar rápido desde el celular. Hay que decidir si reserva sin cuenta (invitado,
nombre + teléfono), con cuenta registrada (JWT, historial, "mis reservas") o ambos. El objetivo del MVP
es bajar la fricción ("recepcionista digital") sin perder la posibilidad de self-service.

## Decisión

Se soportan **ambos** caminos sobre el mismo motor de reservas:
- **Invitado:** la reserva guarda `guest_name` + `guest_phone`, sin cuenta.
- **Cuenta:** jugador autenticado (JWT) con FK `user`.

Regla de integridad (validada en el service): una reserva tiene **`user` XOR `guest_*`** (uno u otro,
no ambos ni ninguno). El motor de concurrencia, estados y validaciones es idéntico para los dos caminos.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| Solo invitado | Mínima fricción, MVP simple | Sin historial ni cancelación self-service |
| Solo cuenta | Trazabilidad, "mis reservas" | Fricción alta; abandono en la grilla pública |
| Ambos | Flexibilidad: rápido para el casual, completo para el recurrente | Dos caminos y casos borde; más tests |

## Consecuencias

### Positivas
- El jugador casual reserva sin registrarse; el recurrente puede tener cuenta.
- Un único motor de reservas; los dos caminos convergen en `create_booking()`.

### Negativas / trade-offs
- `Booking.user` pasa a ser **nullable**; se agregan `guest_name`/`guest_phone`.
- Más casos borde (validar exclusividad; no exponer datos del invitado a terceros).

## Impacto en el sistema
- Backend: `Booking.user` nullable + `guest_name`/`guest_phone`; validación XOR en `bookings/services.py`.
- Frontend: el flujo de reserva ofrece "reservar como invitado" o "ingresar".
- Seguridad: no exponer `guest_phone` en listados públicos; ownership en cancelación.

## Documentos actualizados
- `docs/DER.md`, `docs/ARCHITECTURE.md` §10, `docs/USER_STORIES.md` (HU-2)

## Revisión futura
Revisar si se agrega verificación de teléfono (OTP) o login social.
