# RBAC.md
# Roles, Permisos, Scopes y Multi-tenant — SaaS Gestión de Canchas

## 1. Principio

> Todo acceso se controla por rol, pertenencia al tenant y alcance.
> El multi-tenant no se agrega después: se diseña desde el inicio (esquema por complejo).

## 2. Roles

| Rol | Descripción | Mapea a |
|---|---|---|
| `system_admin` | Equipo de la plataforma. Da de alta complejos (tenants), soporte global. Opera en el esquema `public`. | Nosotros (operación SaaS) |
| `tenant_admin` | Dueño del complejo. Administra canchas, precios, horarios y usuarios internos de su tenant. | Dueño del complejo |
| `operator` | Cajero / recepcionista. Confirma reservas, registra señas, cierra caja. | Personal del complejo |
| `player` | Jugador / cliente final. Ve la grilla y crea reservas. | Cliente final |

> En el modelo de datos, el `User` (custom) distingue **Admin** y **Player**; `tenant_admin` y `operator` son variantes de "staff" del complejo definidas por permisos/grupo.

## 3. Scopes

| Scope | Descripción |
|---|---|
| `global` | Acceso a la administración de tenants (solo `system_admin`, esquema public). |
| `tenant` | Acceso acotado al esquema del propio complejo. |
| `own` | Solo los recursos propios (ej: el jugador ve sus reservas). |
| `public` | Grilla de disponibilidad publicada del complejo (lectura). |

## 4. Matriz de permisos

| Recurso | Acción | system_admin | tenant_admin | operator | player |
|---|---|---:|---:|---:|---:|
| Tenants / Complejos | Crear / Baja | Sí | No | No | No |
| Usuarios internos | Crear / Ver | Sí | Sí (su tenant) | No | No |
| Canchas (`Court`) | ABM | Sí | Sí | No | No |
| Horarios (`ScheduleBlock`) | Configurar | Sí | Sí | No | No |
| Grilla de disponibilidad | Ver | Sí | Sí | Sí | Sí (público) |
| Reserva (`Booking`) | Crear | Sí | Sí | Sí | Sí |
| Reserva | Confirmar (`CONFIRMED`) | Sí | Sí | Sí | No |
| Reserva | Cancelar | Sí | Sí | Sí | Sí, solo la propia |
| Reserva | Ver listado del complejo | Sí | Sí | Sí | No (solo las propias) |
| Caja diaria (`CashMovement`) | Registrar / Ver | Sí | Sí | Sí | No |
| Configuración del complejo | Modificar | Sí | Sí | No | No |

## 5. Reglas multi-tenant

- Cada request resuelve el tenant por dominio/subdominio (middleware de `django-tenants`); todo corre dentro de ese esquema.
- Todo endpoint valida JWT + pertenencia al tenant (salvo la grilla pública, que igual está acotada al tenant del dominio).
- La caja, las reservas y los reportes siempre quedan acotados al esquema del tenant.
- Ningún usuario accede a datos de otro complejo aunque conozca un ID.
- El `system_admin` no opera datos de negocio de un tenant salvo soporte explícito y auditado.

## 6. Permisos por acción

Toda acción sensible debe responder:

- ¿Quién puede ejecutarla? (rol)
- ¿Sobre qué recurso? (cancha, reserva, caja)
- ¿Bajo qué scope? (tenant / own / public)
- ¿Con qué validaciones? (estado, concurrencia, no-pasado)
- ¿Se audita?
- ¿Notifica a alguien? (post-MVP)

## 7. Tests mínimos de permisos

Para cada endpoint sensible:

- usuario sin login no accede (salvo grilla pública);
- jugador no puede confirmar reservas ni ver la caja;
- usuario de otro tenant no accede a datos del complejo;
- cajero/admin correcto sí accede;
- la acción queda auditada si corresponde.

## 8. Prohibiciones

- No confiar en filtros del frontend para ocultar datos.
- No exponer endpoints de administración de tenants sin permiso `system_admin`.
- No permitir que un `player` confirme reservas o vea la caja.
- No devolver objetos de otro tenant aunque se conozca el ID.
- No exponer datos agregados que permitan inferir información de otro complejo.
