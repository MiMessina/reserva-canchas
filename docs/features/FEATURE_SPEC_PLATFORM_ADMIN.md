# FEATURE SPEC: Panel de Administración de Plataforma (System Admin)

## 1. Nombre de la feature

Panel de Administración de Plataforma — gestión de tenants por el equipo interno (`system_admin`)

## 2. Problema que resuelve

El alta de nuevos complejos (tenants) requiere hoy ejecutar un management command por CLI, lo que
implica acceso SSH al servidor y conocimiento técnico. Esto no escala cuando el equipo crece o cuando
los complejos se empiezan a incorporar con mayor frecuencia. El equipo necesita una UI web para dar
de alta, visualizar y gestionar los tenants del SaaS sin tocar el servidor.

## 3. Usuario objetivo

| Actor | Necesidad |
|---|---|
| `system_admin` (equipo interno) | Dar de alta complejos, activar/desactivar tenants, ver el estado de la plataforma sin acceso CLI |

## 4. Flujo principal

### Alta de nuevo tenant
1. El `system_admin` abre `platform.localhost:5173` (o `platform.<dominio>` en producción).
2. Hace login con sus credenciales de superuser Django (email + contraseña).
3. Ve la lista de todos los tenants registrados.
4. Hace clic en "Nuevo complejo".
5. Completa el formulario: nombre del complejo, `schema_name`, dominio primario, email del `tenant_admin` inicial, contraseña inicial.
6. El backend crea `Tenant` + `Domain`, ejecuta `migrate_schemas` para el nuevo esquema y crea el usuario `tenant_admin` en ese esquema.
7. El nuevo tenant aparece en la lista como activo.
8. El `tenant_admin` del nuevo complejo puede loguearse en su dominio.

### Activar / desactivar tenant
1. El `system_admin` busca el tenant en la lista.
2. Hace clic en "Desactivar" (o "Activar").
3. El backend actualiza `Tenant.is_active`.
4. Los usuarios del tenant desactivado no pueden loguearse (validación en el endpoint de login de tenant).

## 5. Reglas de negocio

| Regla | Descripción |
|---|---|
| Solo superuser | Solo `auth.User` con `is_superuser=True` puede acceder a los endpoints de `/api/platform/`. |
| `schema_name` inmutable | Una vez creado el tenant, `schema_name` no puede editarse (requeriría renombrar el esquema PostgreSQL). |
| `schema_name` válido | Solo `[a-z][a-z0-9_]*`, máx 63 chars, no puede ser `public`, `information_schema` ni ningún esquema reservado de PostgreSQL. |
| Dominio único | `Domain.domain` es único en la plataforma; no puede repetirse entre tenants. |
| Creación atómica | Si falla algún paso (migración, creación del admin), el tenant no queda en estado parcial. Se hace rollback o se documenta el estado de error claramente. |
| Soft-delete | Desactivar un tenant es `is_active = False`; no se elimina el esquema ni los datos. |
| No ver datos de negocio | Los endpoints de platform no exponen reservas, caja, canchas ni usuarios del tenant. Solo metadata del tenant (`name`, `schema_name`, `domain`, `is_active`, `created_at`). |
| Aislamiento de JWT | El JWT emitido por `/api/platform/auth/login/` no es válido en endpoints de tenant y viceversa. |

## 6. Estados del Tenant (para este panel)

| Estado | Descripción |
|---|---|
| Activo (`is_active=True`) | El tenant opera normalmente; sus usuarios pueden loguearse. |
| Inactivo (`is_active=False`) | El tenant está suspendido; sus usuarios no pueden loguearse. Los datos están intactos. |

## 7. Permisos

| Acción | Rol permitido | Scope |
|---|---|---|
| Login en `/api/platform/auth/login/` | `system_admin` (`is_superuser=True`) | `public` schema |
| Listar tenants | `system_admin` | `public` schema |
| Crear tenant | `system_admin` | `public` schema |
| Ver detalle de tenant | `system_admin` | `public` schema |
| Activar / desactivar tenant | `system_admin` | `public` schema |
| Editar nombre del tenant | `system_admin` | `public` schema |

## 8. API requerida

Todos los endpoints bajo `/api/platform/` se registran en `PUBLIC_SCHEMA_URLCONF` y solo responden
desde el hostname `platform.*`. Requieren JWT de `system_admin`.

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/platform/auth/login/` | Login JWT para `system_admin` (contra `auth.User`) |
| `POST` | `/api/platform/auth/refresh/` | Refresh del token |
| `GET` | `/api/platform/tenants/` | Listar todos los tenants |
| `POST` | `/api/platform/tenants/` | Crear nuevo tenant (crea schema, migra, crea tenant_admin) |
| `GET` | `/api/platform/tenants/{id}/` | Detalle de un tenant |
| `PATCH` | `/api/platform/tenants/{id}/` | Editar nombre (no schema_name ni domain) |
| `POST` | `/api/platform/tenants/{id}/toggle/` | Activar / desactivar |

### Request POST /api/platform/tenants/

```json
{
  "name": "Complejo Los Pinos",
  "schema_name": "lospinos",
  "domain": "lospinos.canchero.com",
  "admin_email": "admin@lospinos.com",
  "admin_password": "contraseña-segura"
}
```

### Response GET /api/platform/tenants/

```json
[
  {
    "id": 1,
    "name": "Complejo Demo",
    "schema_name": "demo",
    "domain": "demo.canchero.com",
    "is_active": true,
    "created_at": "2026-06-01T10:00:00Z"
  }
]
```

### Errores esperados

```json
{ "error": { "code": "SCHEMA_ALREADY_EXISTS", "message": "El schema 'lospinos' ya existe." } }
{ "error": { "code": "DOMAIN_ALREADY_EXISTS", "message": "El dominio 'lospinos.canchero.com' ya está en uso." } }
{ "error": { "code": "INVALID_SCHEMA_NAME", "message": "El schema_name solo puede contener letras minúsculas, números y guion bajo." } }
{ "error": { "code": "TENANT_CREATION_FAILED", "message": "Error al crear el tenant. El proceso fue revertido." } }
```

## 9. UI requerida

### Páginas / componentes

- **`PlatformLoginPage`** (`/login`): formulario email + contraseña. Error claro si las credenciales no son de superuser.
- **`TenantListPage`** (`/`): tabla con columnas Nombre, Schema, Dominio, Estado (badge), Fecha de alta. Acciones por fila: Ver detalle, Toggle activo/inactivo. Botón "Nuevo complejo".
- **`TenantCreateModal`**: modal con el formulario de alta. Loading state mientras corre `migrate_schemas` (puede tardar 5-15 seg). Mensaje de éxito con el dominio del nuevo tenant.
- **`TenantDetailPage`** (`/tenants/:id`): read-only con todos los campos + botón toggle estado.

### Estados de UI

- Loading, empty ("No hay complejos registrados"), error en cada pantalla.
- El botón "Crear" muestra spinner + texto "Creando esquema..." durante la migración.
- Un tenant inactivo se muestra con badge rojo en la lista.

## 10. Auditoría

- `platform.tenant_created` (system_admin, nombre, schema, dominio, timestamp)
- `platform.tenant_toggled` (system_admin, tenant_id, is_active nuevo, timestamp)
- `platform.login` (system_admin, timestamp)

## 11. Notificaciones

- Post-MVP: email de bienvenida al `tenant_admin` recién creado con sus credenciales y la URL de su panel.

## 12. Criterios de aceptación

1. El `system_admin` puede loguearse en `platform.localhost:5173` y ver la lista de tenants.
2. Puede crear un nuevo tenant desde la UI: el schema migra, el `tenant_admin` queda creado y el nuevo dominio responde.
3. Puede activar / desactivar un tenant; un tenant inactivo no permite login de sus usuarios.
4. El JWT de `system_admin` NO es válido en endpoints de tenant (recibe 401/403).
5. El JWT de tenant NO es válido en `/api/platform/` (recibe 401/403).
6. `schema_name` inválido o duplicado devuelve error 400 con código descriptivo.
7. Si la creación del tenant falla, no quedan datos parciales (rollback).
8. Los endpoints de `/api/platform/` no son accesibles desde hostnames de tenant.
9. Tests: `pytest` pasa (incluido tests de aislamiento de JWT y de permisos). `migrate_schemas` pasa. `docker compose up` levanta con el hostname `platform.localhost` configurado.

## 13. Fuera de alcance

- Ver datos de negocio de un tenant (reservas, canchas, caja, usuarios del tenant).
- Editar `schema_name` o dominio primario de un tenant existente.
- Múltiples `system_admin` (MVP soporta un único superuser Django).
- Email de bienvenida al nuevo `tenant_admin` (post-MVP, requiere Celery).
- Métricas agregadas cross-tenant (ocupación total, ingresos totales, etc.).
- Gestión de dominios secundarios por tenant.
- Impersonation (entrar al panel de un tenant como admin).
- Eliminación física de tenants (soft-delete solamente).

## 14. Riesgos

| Riesgo | Mitigación |
|---|---|
| `migrate_schemas` sincrónico tarda varios segundos | Loading state en UI + timeout generoso en Axios (60s); documentar para post-MVP con Celery |
| Creación parcial del tenant (schema creado pero falla el admin) | Service con manejo de errores explícito; documentar cómo remediar manualmente si ocurre |
| JWT de `system_admin` válido en endpoints de tenant | Permiso `IsSystemAdmin` es incompatible con `IsAuthenticated` de tenant (distintos backends de auth); verificar en tests |
| `schema_name` con nombre reservado de PostgreSQL | Validador en serializer con lista de nombres prohibidos |
| Dos admins crean el mismo schema en simultáneo | UNIQUE constraint en `Tenant.schema_name` a nivel DB; la segunda request recibe 400 |
