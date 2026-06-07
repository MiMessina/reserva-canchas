# ADR-007: Custom User en TENANT_APPS (usuarios por tenant)

**Fecha:** 2026-06-02
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator) / Luka (Backend Lead)

## Contexto

El producto es marca blanca: cada complejo opera bajo su propia URL y no hay marca agregadora visible
al jugador. Hay que decidir dónde vive el modelo de usuario (`AUTH_USER_MODEL`) en la arquitectura
`django-tenants`: en el esquema `public` (SHARED_APPS, una tabla de usuarios para toda la plataforma)
o en cada esquema de tenant (TENANT_APPS, una tabla por complejo).

## Decisión

El **Custom User vive en TENANT_APPS**: cada complejo tiene su propia tabla de usuarios en su esquema.
Un usuario (staff o jugador) pertenece a un único complejo; no existe ni es visible en otro.
`Tenant` y `Domain` permanecen en el esquema `public`. El `system_admin` es el superuser del esquema
`public` y administra tenants, no usuarios de negocio.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| User en `public` (compartido) | Un jugador podría reusar cuenta entre complejos | Mezcla identidades entre tenants; rompe el espíritu de marca blanca; riesgo de fuga |
| User en TENANT_APPS (por tenant) | Aislamiento total de identidades; coherente con marca blanca | Un mismo jugador que use dos complejos tiene dos cuentas |

## Consecuencias

### Positivas
- Aislamiento de identidades a nivel esquema; imposible enumerar usuarios de otro complejo.
- Coherente con la regla de no cruzar esquemas y con `RBAC.md`.

### Negativas / trade-offs
- Si en el futuro se quisiera una "cuenta única de jugador" multi-complejo, requeriría rediseño (nuevo ADR).
- `createsuperuser` opera por esquema; el alta de staff inicial del tenant se hace en su esquema.

## Impacto en el sistema
- Backend: `AUTH_USER_MODEL` en una app dentro de TENANT_APPS (`users`); migraciones de user por tenant.
- DevOps: el seed/`create_tenant` crea el `tenant_admin` dentro del esquema del tenant.
- Seguridad: tests de aislamiento de usuarios entre tenants.

## Documentos actualizados
- `docs/DER.md`, `docs/ARCHITECTURE.md` §10

## Revisión futura
Reabrir si aparece la necesidad de identidad única de jugador entre complejos.
