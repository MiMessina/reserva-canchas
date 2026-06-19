# ADR-013: Panel web de System Admin (supersede ADR-009)

**Fecha:** 2026-06-17
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator)

## Contexto

ADR-009 decidió diferir el panel web de `system_admin` para el MVP, resolviendo el alta de tenants
con el management command `create_tenant`. Con el "Cliente Cero" operativo y múltiples tenants en uso
(`demo`, `complejo2`, `lospinos`), el alta por CLI ya no escala: requiere acceso SSH al servidor y
conocimiento técnico del equipo. Es el momento de construir el panel.

## Decisión

Construir el **Panel de Administración de Plataforma** como una sección del frontend existente
(accesible desde el hostname `platform.localhost` / `platform.<dominio>` en producción) y un conjunto
de endpoints REST bajo `/api/platform/` que operan **exclusivamente en el esquema `public`** de
PostgreSQL via `PUBLIC_SCHEMA_URLCONF` de `django-tenants`.

Autenticación del `system_admin`: JWT contra `django.contrib.auth.User` (el superuser de Django,
que vive en SHARED_APPS / esquema `public`). No usa el Custom User de TENANT_APPS.
El permiso `IsSystemAdmin` valida `request.user.is_superuser`.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| Seguir con management command | Sin superficie de ataque nueva | No escala; requiere CLI/SSH; no apto para equipo no-técnico |
| Panel web con auth propia (modelo PlatformUser) | Flexibilidad para múltiples admins | Over-engineering para MVP; un solo equipo admin |
| Usar Django Admin (built-in) | Rápido de implementar | UX inconsistente; no mobile-friendly; no integra con el frontend React |
| Panel web + JWT contra auth.User | Consistente con el stack (JWT ya en uso); auth.User ya existe en public | Necesita endpoint de login separado; dos "sabores" de JWT en el sistema |

## Consecuencias

### Positivas

- El alta de tenants es self-service para cualquier miembro del equipo con credenciales de superuser.
- No se expone ningún dato de negocio de los tenants (reservas, caja, usuarios) en estos endpoints.
- Reutiliza la infraestructura JWT existente; no agrega librerías nuevas.
- La separación por hostname es un control de seguridad adicional (endpoints de platform no responden desde hostnames de tenant).

### Negativas / trade-offs

- Dos "sabores" de JWT en el sistema: uno para tenant users (Custom User) y uno para system_admin (auth.User). Hay que documentarlo claramente.
- La creación de tenant es sincrónica (migrate_schemas bloquea la request varios segundos). Aceptable para MVP; se migrará a Celery cuando el volumen de altas lo justifique.
- Solo un `system_admin` soportado en MVP (el superuser Django). Múltiples admins requerirán un nuevo ADR y modelo `PlatformUser`.

## Impacto en el sistema

- **Backend:** nuevos archivos `views_platform.py`, `serializers_platform.py`, `permissions_platform.py`, `urls_platform.py` en `apps/tenants/`. Nuevo `urls_public.py` en `config/`. Refactor de `create_tenant` management command → `tenants/services.py`. Ajuste en `settings.py` para `PUBLIC_SCHEMA_URLCONF`.
- **Frontend:** nueva sección `frontend/src/features/platform-admin/` con login, listado, creación y detalle de tenants. Nuevo `platformApiClient.ts`. Routing condicional por hostname.
- **DevOps:** hostname `platform.localhost` en `extra_hosts` de docker-compose. En producción: virtual host `platform.<dominio>` en Nginx.
- **Seguridad:** los endpoints `/api/platform/` no deben ser accesibles desde hostnames de tenant. El JWT de system_admin no debe ser válido en endpoints de tenant y viceversa.

## Documentos actualizados

- `docs/ARCHITECTURE.md` §10 (agregar ADR-013 a la lista)
- `docs/features/FEATURE_SPEC_PLATFORM_ADMIN.md` (nuevo)
- `docs/adr/ADR-009-alta-de-tenant-por-comando.md` (marcar como parcialmente superado)

## Revisión futura

- Cuando el equipo crezca y se necesiten múltiples `system_admin`: crear modelo `PlatformUser` en SHARED_APPS (nuevo ADR).
- Cuando el alta de tenants sea frecuente (>10/mes): mover `migrate_schemas` a tarea Celery asíncrona.
