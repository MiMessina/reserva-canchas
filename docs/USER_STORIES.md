# USER_STORIES.md
# Historias de Usuario (INVEST) — SaaS Gestión de Canchas

> Entregable de Sprint 0 ("Historias de usuario iniciales del Motor de Reservas, formato INVEST").
> Formato: *Como [rol] quiero [acción] para [beneficio]*. Cada historia es Independiente, Negociable,
> Valiosa, Estimable, Small y Testeable. Roles según `RBAC.md`. Estados según `WORKFLOW.md`.

## 1. Sprint 0 — Cimientos (no son features de negocio)

### HU-0.1 — Entorno reproducible
**Como** integrante del equipo **quiero** levantar todo con `docker compose up` **para** trabajar sin configurar a mano.
**Criterios:** backend + frontend + db levantan con un comando; healthcheck `/api/health/` responde 200; README explica el arranque.

### HU-0.2 — Aislamiento multi-tenant
**Como** plataforma **quiero** que cada complejo tenga su esquema PostgreSQL **para** garantizar que un tenant no vea datos de otro.
**Criterios:** se crean dos tenants de prueba; un usuario del tenant A no accede a datos del tenant B; existe test de aislamiento.

### HU-0.3 — Autenticación JWT
**Como** usuario interno **quiero** loguearme y obtener un token **para** operar el panel de forma segura.
**Criterios:** login y refresh funcionan; el front guarda el token y lo adjunta vía interceptor; ruta protegida; test de login.

## 2. Configuración del complejo (Sprint 1 — Admin)

### HU-7 — ABM de canchas
**Como** dueño del complejo (`tenant_admin`) **quiero** dar de alta, editar y desactivar mis canchas **para** publicar qué espacios alquilo y a qué precio.
**Criterios de aceptación:**
- Creo una cancha con nombre, tipo (`FUTBOL_5`/`FUTBOL_7`/`PADEL`), superficie, precio base y duración del turno (`slot_duration_minutes`).
- Edito y desactivo (baja lógica: `is_active=False`, nunca borrado físico).
- Un `operator` puede listar pero no mutar (403); un `player` no muta (403).
- Las canchas quedan acotadas a mi complejo; no veo ni accedo a canchas de otro tenant (aislamiento).
- Endpoints documentados en Swagger; el panel admin maneja loading/empty/error (mobile-first).

### HU-8 — Configurar horarios de apertura/cierre
**Como** dueño del complejo (`tenant_admin`) **quiero** definir los horarios de apertura y cierre de cada cancha por día de la semana **para** que luego se pueda calcular la disponibilidad de turnos.
**Criterios de aceptación:**
- Defino bloques `ScheduleBlock` por cancha y día (`weekday` 0=lunes … 6=domingo) con `open_time` y `close_time`.
- No puedo crear un bloque con `open_time ≥ close_time` ni que se solape con otro bloque activo de la misma cancha y día (permitido turno partido mañana/tarde sin superposición).
- Sin cruce de medianoche en el MVP (apertura y cierre el mismo día).
- Solo `tenant_admin` configura horarios; `operator`/`player` no (403). Aislamiento por tenant.

## 3. Motor de Reservas (features — Sprint 2-3)

### HU-1 — Ver grilla pública de turnos
**Como** jugador **quiero** ver la disponibilidad de turnos de un complejo **para** elegir uno libre desde el celular.
**Criterios de aceptación:**
- Veo turnos libres/ocupados por cancha y día (mobile-first).
- La grilla queda acotada al tenant del dominio (sin login).
- Estado vacío si no hay turnos ("No hay turnos disponibles ese día").
- Las horas se muestran en hora de Buenos Aires (la API responde UTC).

### HU-2 — Crear una reserva
**Como** jugador **quiero** reservar un turno disponible **para** asegurar la cancha sin que me atienda un humano.
**Criterios:**
- La reserva nace en `PENDING_PAYMENT` y me muestra las instrucciones de transferencia de la seña.
- No puedo reservar en el pasado (`BOOKING_IN_PAST`), en cancha inactiva (`COURT_INACTIVE`) ni fuera de horario (`OUTSIDE_SCHEDULE`).
- La creación corre con `select_for_update()` dentro de una transacción.
- Queda auditada (`booking.created`).

### HU-3 — No overbooking (concurrencia)
**Como** dueño del complejo **quiero** que sea imposible reservar dos veces el mismo turno **para** no perder plata ni credibilidad.
**Criterios:**
- Dos reservas simultáneas para la misma cancha y turno solapado → solo una se crea; la otra recibe `SLOT_ALREADY_BOOKED`.
- El conflicto se evalúa por **solapamiento de intervalos** `[start_dt, end_dt)`, no por igualdad exacta.
- Existe test de concurrencia que lo demuestra.

### HU-4 — Confirmar la seña (caja)
**Como** cajero (`operator`) **quiero** confirmar una reserva tras verificar la transferencia **para** asegurar el turno y registrarlo en la caja del día.
**Criterios:**
- Transición `PENDING_PAYMENT → CONFIRMED` validada en el service.
- Genera un `CashMovement` del día.
- Un `player` no puede confirmar (403). Queda auditado.

### HU-5 — Cancelar una reserva
**Como** jugador **quiero** cancelar mi reserva (o **como** cajero, cancelar una del complejo) **para** liberar el turno.
**Criterios:**
- El jugador solo cancela **las propias**; el cajero/admin cualquiera del tenant.
- Cancelar requiere motivo; si estaba `CONFIRMED`, se anota/revierte el movimiento de caja.
- `CANCELLED` y `COMPLETED` son finales (no se "reviven").

### HU-6 — Caja diaria
**Como** cajero **quiero** ver los movimientos de caja del día **para** conciliar las señas recibidas.
**Criterios:**
- Listado filtrable por fecha, acotado al tenant.
- Un `player` no accede a la caja (403).

## 4. Trazabilidad

| Historia | Documento de soporte |
|---|---|
| HU-0.* | `SPRINT_0.md`, `ARCHITECTURE.md` |
| HU-7, HU-8 | `DER.md`, `RBAC.md`, `API_GUIDELINES.md` (Sprint 1 — ABM canchas y horarios) |
| HU-1, HU-2, HU-3 | `WORKFLOW.md`, `API_GUIDELINES.md`, `templates/FEATURE_SPEC_TEMPLATE.md` (ejemplo Motor de Reservas) |
| HU-4, HU-5, HU-6 | `WORKFLOW.md`, `RBAC.md` |
