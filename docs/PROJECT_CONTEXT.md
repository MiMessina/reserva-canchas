# PROJECT_CONTEXT.md
# Contexto del Proyecto

## 1. Nombre del proyecto

**Nombre:** `CANCHERO!` (SaaS de Gestión y Reserva de Complejos Deportivos)

> Nombre de trabajo interno. El producto es **marca blanca**: cada complejo opera bajo su propia URL/entorno, no bajo una marca común visible al jugador.

**Descripción breve:**
SaaS B2B **multi-tenant** que reemplaza la gestión de reservas por WhatsApp + Excel de los complejos de Fútbol 5/7 y Pádel. Funciona como un "recepcionista digital 24/7": cada complejo obtiene un link de reservas en la nube que integra a su Instagram/WhatsApp, donde los jugadores ven la grilla de turnos y reservan, mientras el dueño/cajero gestiona canchas, turnos y caja desde un panel de administración.

## 2. Problema que resuelve

Los complejos chicos y medianos gestionan sus reservas de forma manual y frágil, perdiendo turnos, generando overbooking y sin trazabilidad de la caja.

### Situación actual

- Las reservas se toman por WhatsApp y se anotan en una planilla de Excel o un cuaderno.
- No hay control de concurrencia: dos personas pueden reservar la misma cancha en el mismo horario.
- La seña/pago se cobra por transferencia y se concilia "de memoria", sin registro confiable de caja.
- El dueño no tiene visibilidad de ocupación, turnos ociosos ni ingresos del día.

### Dolor principal

> "Pierdo reservas y plata porque gestiono todo a mano por WhatsApp y Excel, y nunca sé con certeza qué cancha está libre ni cuánto entró hoy."

## 3. Objetivo del sistema

El sistema debe permitir:

- Que cada complejo (tenant) opere su propio entorno aislado bajo su URL de marca blanca.
- Que el jugador vea una grilla pública de turnos y reserve sin necesidad de que un humano atienda.
- Que el motor de reservas impida el overbooking incluso bajo reservas simultáneas (concurrencia).
- Que el cajero confirme señas/transferencias y lleve una caja diaria básica con conciliación manual.
- Que el dueño administre canchas, precios y horarios de apertura/cierre del complejo.

## 4. Usuarios principales

| Usuario / Actor | Descripción | Necesidad principal |
|---|---|---|
| `Dueño / Admin del complejo` (`tenant_admin`) | Administra su complejo: canchas, precios, horarios, usuarios internos. | Configurar y controlar su operación y ver la caja del día. |
| `Cajero / Recepcionista` (`operator`) | Personal que opera el día a día desde el panel. | Confirmar reservas, registrar señas y cerrar caja. |
| `Jugador / Cliente final` (`player` / `external_user`) | Quien quiere alquilar una cancha. | Ver disponibilidad y reservar un turno rápido desde el celular. |
| `Administrador de la plataforma` (`system_admin`) | El equipo (nosotros) que da de alta complejos y opera el SaaS. | Alta/baja de tenants y soporte global. |

## 5. Alcance inicial

### Incluido en el MVP

- Módulo Multi-tenant (aislamiento por esquema PostgreSQL con `django-tenants`).
- ABM de Canchas (tipo Fútbol/Pádel, superficie, precio base, activa/inactiva).
- Configuración de disponibilidad / horarios de apertura y cierre del complejo (`ScheduleBlock`).
- Grilla de Turnos Pública (vista de disponibilidad para el jugador).
- Motor de Reservas con **mitigación de concurrencia** (bloqueo pesimista).
- Módulo de Caja Diario Básico (conciliación manual de señas/transferencias).
- Autenticación JWT y RBAC (Admin / Cajero / Jugador).

### Fuera de alcance inicial (V1)

- Pasarelas de pago automatizadas (MercadoPago / Stripe).
- Facturación AFIP.
- Módulo Buffet / E-commerce.
- Agente de IA para tomar reservas por WhatsApp y alertas automáticas (visión post-MVP).
- App móvil nativa (el MVP es web responsive / mobile-first).

## 6. Reglas del negocio

| Regla | Descripción | Impacto técnico |
|---|---|---|
| Aislamiento por tenant | Cada complejo ve únicamente sus propios datos. | Esquemas PostgreSQL separados vía `django-tenants`. Prohibido `tenant_id` compartido para datos críticos. |
| No overbooking | Una cancha no puede tener dos reservas en el mismo horario. | `select_for_update()` (bloqueo pesimista) en la transacción de reserva; el conflicto se evalúa por **solapamiento de intervalos** `[start_dt, end_dt)`. |
| Duración del turno | Cada cancha define la duración de su turno (ej: 60/90 min). | `Court.slot_duration_minutes`; `Booking.end_dt = start_dt + slot_duration_minutes`. Ver `WORKFLOW.md` y ADR-006. |
| Reserva nace pendiente | Como el pago es por transferencia externa, la reserva entra como `PENDING_PAYMENT`. | El cajero la transiciona a `CONFIRMED` al verificar la seña. Validado en backend (service layer). |
| Soft-delete obligatorio | No se borra físicamente nada. | Toda entidad tiene `is_active`, `created_at`, `updated_at`. Prohibido `DELETE`. |
| Tiempo en UTC | Todas las fechas/horas se guardan en UTC. | Conversión a `America/Argentina/Buenos_Aires` en frontend o serializer. |
| No reservar en el pasado | No se permite reservar un turno ya vencido. | Validación de negocio en el service de reservas. |

## 7. Glosario del dominio

| Término | Definición |
|---|---|
| Tenant / Complejo | Cliente B2B (el complejo deportivo). Cada uno tiene su esquema de datos aislado. |
| Marca blanca | Cada tenant opera bajo su propia URL/branding; no hay marca agregadora visible al jugador. |
| Cancha (`Court`) | Espacio alquilable. Tipo Fútbol 5/7 o Pádel, con superficie, precio base y estado. |
| Turno / Slot | Bloque horario reservable de una cancha. Su duración la define la cancha (`Court.slot_duration_minutes`, ej: 60/90 min); la reserva ocupa el intervalo `[start_dt, end_dt)`. |
| `ScheduleBlock` | Configuración de horarios de apertura/cierre y disponibilidad del complejo. |
| Reserva (`Booking`) | Relación Jugador + Cancha + fecha/hora, con estado (Pending, Confirmed, Cancelled, Completed). |
| Seña | Pago parcial por transferencia que el cajero concilia manualmente para confirmar la reserva. |
| Caja diaria | Registro de movimientos (señas/pagos confirmados) del día por tenant. |
| Overbooking | Doble asignación de la misma cancha y horario; debe ser técnicamente imposible. |

## 8. Métricas de éxito

El proyecto será considerado exitoso si:

- Un complejo real asociado al equipo lo usa en producción durante el semestre ("Cliente Cero").
- Cero casos de overbooking en uso real.
- El cliente puede dar de alta canchas, publicar su grilla y recibir reservas sin asistencia del equipo.
- La caja diaria refleja correctamente las señas confirmadas del día.
- El sistema es demostrable y vendible a un segundo complejo.

## 9. Restricciones conocidas

- **Técnica:** El aislamiento multi-tenant por esquema (`django-tenants`) condiciona migraciones y queries; no se puede improvisar.
- **Legal / organizacional:** Sin facturación AFIP ni pagos automáticos en el MVP; la seña es conciliación manual.
- **Presupuestaria:** Proyecto académico/freelance; stack open-source, sin servicios pagos innecesarios en MVP.
- **De tiempo:** Debe estar operativo para el "Cliente Cero" dentro del semestre; Sprints de 2 semanas.

## 10. Criterios de aceptación del MVP

- Un tenant nuevo se da de alta con su esquema aislado y su URL.
- El Admin configura canchas y horarios de apertura/cierre.
- El jugador ve la grilla pública y crea una reserva en estado `PENDING_PAYMENT`.
- El cajero confirma la reserva tras verificar la seña y queda registrada en la caja del día.
- Dos reservas simultáneas para el mismo turno no producen overbooking (una falla controladamente).
- Ningún usuario puede ver ni operar datos de otro tenant.
