# ARCHITECTURE.md
# Arquitectura del Sistema — SaaS Gestión de Canchas

## 1. Principio rector

> El backend (Django REST Framework) es el **source of truth**.
> El frontend (React) presenta estado, pero **no decide** reglas de negocio, permisos, cupos, precios, concurrencia ni transiciones de estado de la reserva.

La validación dura (disponibilidad, concurrencia, permisos, multi-tenant) vive **estrictamente** en el backend.

## 2. Objetivos arquitectónicos

La arquitectura debe ser:

- modular (separada por dominio: canchas, reservas, caja, usuarios);
- mantenible y testeable;
- escalable a más tenants sin tocar el código de negocio;
- segura y con aislamiento absoluto entre complejos;
- **multi-tenant por esquema** desde el día cero;
- documentada (API-First, contrato Swagger);
- preparada para que post-MVP se integren agentes IA (WhatsApp) sobre la misma API.

## 3. Capas del sistema

```txt
Frontend (React + Vite + TS)
  ↓  (Axios + React Query, consume API REST con JWT)
API / ViewSets (DRF)
  ↓
Serializers / DTOs   (validan estructura, NO gobiernan negocio)
  ↓
Service Layer (services.py)   ← reglas de negocio, concurrencia, transiciones
  ↓
Models / ORM (Django)   ← scope multi-tenant automático (django-tenants)
  ↓
PostgreSQL (un esquema por tenant)
```

## 4. Regla de Service Layer

Toda lógica de negocio compleja vive en `backend/apps/[domain]/services.py`.

### Permitido en services

- el motor de reservas y la mitigación de concurrencia (`select_for_update()`);
- transiciones de estado de la reserva (`PENDING_PAYMENT → CONFIRMED → ...`);
- validaciones de negocio (no reservar en el pasado, cancha activa, horario dentro de la disponibilidad);
- cálculo de precio del turno;
- registro de movimientos de caja;
- auditoría y (post-MVP) notificaciones.

### Prohibido en vistas, serializers o frontend

- lógica de reservas y control de concurrencia;
- cálculo de disponibilidad real o precios definitivos;
- decisiones de transición de estado;
- reglas multi-tenant;
- validaciones de seguridad/permisos finales.

## 5. Módulos principales

| Módulo (backend app) | Responsabilidad | Owner principal |
|---|---|---|
| `tenants` | Alta/gestión de complejos, ruteo por esquema, dominios. | Backend Lead (Luka) |
| `users` | Custom user (Admin/Player), autenticación JWT, roles. | Backend Lead (Luka) |
| `courts` | ABM de canchas y `ScheduleBlock` (disponibilidad/horarios). | Backend API (Erik) |
| `bookings` | Motor de reservas, concurrencia, estados de la reserva. | Backend API (Erik) |
| `cashbox` | Caja diaria, conciliación manual de señas. | Backend API (Erik) |
| `frontend/features/booking` | Grilla pública y flujo de reserva del jugador. | Frontend (Nacho) |
| `frontend/features/admin` | Panel de Admin/Cajero (canchas, turnos, caja). | Frontend Lead (Cris) |
| `infra/docker` | Contenedores, Postgres, entorno reproducible. | DevOps (rotativo) |

## 6. Modelo de datos

### Entidades principales (DER base — dentro de cada esquema de tenant)

| Entidad | Descripción | Relaciones clave |
|---|---|---|
| `User` | Custom user heredando de `AbstractUser`. Roles: Admin, Player. | Crea/posee `Booking`. |
| `Court` (Cancha) | Tipo (Fútbol 5/7 / Pádel), superficie, precio base, `is_active`. | Tiene muchos `Booking` y `ScheduleBlock`. |
| `ScheduleBlock` | Disponibilidad: apertura/cierre del complejo por día/cancha. | Pertenece a `Court` (o al complejo). |
| `Booking` (Reserva) | `User` + `Court` + `datetime` + estado + precio. | FK a `User` y `Court`. |
| `CashMovement` | Movimiento de caja (seña/pago confirmado del día). | FK a `Booking` y al operador. |

> El modelo del **tenant** y sus **dominios** viven en el esquema `public` (gestionado por `django-tenants`); el resto de las entidades viven en el esquema de cada complejo.

### Reglas de datos

- Toda entidad tiene `is_active` (soft-delete), `created_at`, `updated_at`. **Prohibido `DELETE` físico.**
- Toda fecha/hora se guarda en **UTC**; la conversión a `America/Argentina/Buenos_Aires` es responsabilidad del frontend/serializer.
- El aislamiento por tenant lo da el esquema; **no** se usa una columna `tenant_id` compartida para datos críticos de reservas.
- No se hacen queries globales cruzando esquemas de tenants.
- No exponer IDs internos del jugador donde no haga falta.

## 7. Multi-tenant y aislamiento

Estrategia: **un esquema PostgreSQL por complejo** vía `django-tenants` (no row-level).

- El tenant se resuelve por el dominio/subdominio de la request (middleware de `django-tenants`).
- Cada query corre dentro del esquema activo; el aislamiento es a nivel base de datos.
- Los reportes y la caja siempre quedan acotados al esquema del tenant.
- Ningún usuario puede inferir ni acceder a datos de otro complejo, aunque conozca un ID.
- Las migraciones se aplican a `public` (shared apps) y a cada esquema (tenant apps).

## 8. Auditoría

Toda acción relevante genera evento auditable (con autor, tenant y timestamp):

- login;
- creación/edición de cancha y horarios;
- **creación de reserva**;
- **cambio de estado de reserva** (confirmación, cancelación, completada);
- registro/confirmación de seña en caja;
- alta/baja de usuarios internos;
- (post-MVP) acciones de integraciones externas.

## 9. Integraciones externas

| Integración | Propósito | Responsable | Estado |
|---|---|---|---|
| Instagram / WhatsApp (link) | Difusión del link de reservas marca blanca. | Frontend / Negocio | MVP (solo link, sin API) |
| MercadoPago / Stripe | Pagos automáticos de señas. | Backend | Fuera de alcance (V1) |
| AFIP | Facturación electrónica. | Backend | Fuera de alcance (V1) |
| Agente IA WhatsApp | Tomar reservas por chat sobre la API. | Backend + IA | Post-MVP (visión) |
| Celery + Redis | Tareas async: alertas de turnos ociosos / quiebre de disponibilidad. | DevOps + Backend | Post-MVP (documentado, no instalado en Sprint 0) |

## 10. Decisiones arquitectónicas

Las decisiones relevantes se registran como ADR (`templates/ADR_TEMPLATE.md`). Ejemplos ya tomados para este proyecto:

- **ADR-001:** Multi-tenant por esquema PostgreSQL con `django-tenants` (en lugar de `tenant_id` compartido).
- **ADR-002:** Autenticación stateless con Simple JWT.
- **ADR-003:** Mitigación de overbooking con bloqueo pesimista (`select_for_update()`).
- **ADR-004:** Frontend en TypeScript (React + Vite) con React Query + Axios.
- **ADR-005:** Señas por transferencia con conciliación manual (sin pasarela en MVP).
- **ADR-006:** Duración del turno configurable por cancha (`Court.slot_duration_minutes`) y detección de overbooking por solapamiento de intervalos `[start_dt, end_dt)`, en lugar de igualdad exacta de `start_dt`.
- **ADR-007:** Custom User en TENANT_APPS (usuarios por tenant, no compartidos en `public`).
- **ADR-008:** Reserva del jugador como invitado (`guest_name`/`guest_phone`) o con cuenta (FK `user` nullable); regla `user` XOR `guest_*`.
- **ADR-009:** Alta de tenant por management command `create_tenant` / Django admin (sin panel web en MVP).
- **ADR-010:** `django-cors-headers` para la comunicación frontend ↔ backend (orígenes por entorno).
- **ADR-011:** Modelo base abstracto (`TimeStampedSoftDeleteModel`) en `apps/common` para `is_active`/`created_at`/`updated_at` reutilizables por herencia.
- **ADR-012:** Rebranding del producto de `CanchaYA` a `CANCHERO!` (cambio cosmético de naming; `CANCHERO!` en UI, `canchero` en identificadores técnicos).
- **ADR-013:** Panel web de System Admin (supersede ADR-009): endpoints `/api/platform/` en `PUBLIC_SCHEMA_URLCONF`, JWT contra `auth.User` superuser, hostname `platform.*` dedicado.

> Las ADR completas viven en `docs/adr/`.

## 11. Anti-patrones prohibidos

- Usar `tenant_id` en una base compartida para reservas/caja.
- Resolver disponibilidad o precio en el frontend.
- Crear reservas sin bloqueo de concurrencia.
- Usar `DELETE` físico en lugar de `is_active`.
- Guardar fechas en hora local de Argentina en la DB.
- Crear endpoints sin permisos o sin validación de tenant/JWT.
- Crear carpetas o módulos nuevos sin actualizar `FOLDER_STRUCTURE.md`.
- Agregar librerías npm/pip sin justificación y ADR.
- Duplicar lógica de negocio entre backend y frontend.
