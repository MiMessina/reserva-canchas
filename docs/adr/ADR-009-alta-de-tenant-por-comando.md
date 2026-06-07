# ADR-009: Alta de tenant por management command (sin panel en MVP)

**Fecha:** 2026-06-02
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator) / Luka (Backend Lead)

## Contexto

Cada complejo es un tenant con su esquema y su dominio. Hay que decidir cómo se da de alta un complejo
nuevo en el MVP: con un panel web de `system_admin` o con un management command / Django admin operado
por el equipo de la plataforma.

## Decisión

El alta de tenant en el MVP se hace con un **management command** `create_tenant` (y el Django admin del
esquema `public`), operado por el equipo (`system_admin`). El comando crea el `Tenant`, su `Domain`,
ejecuta las migraciones del esquema y crea el `tenant_admin` inicial del complejo. **No** se construye un
panel web de administración de tenants en el MVP.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| Panel web de `system_admin` | Self-service para el equipo, escalable | Trabajo de UI/endpoints innecesario para 1-2 complejos en MVP |
| Management command / admin | Rápido, suficiente para el Cliente Cero, menos superficie | Requiere acceso al servidor/CLI para dar de alta |

## Consecuencias

### Positivas
- Foco del MVP en el flujo de reservas, no en herramientas internas.
- Menos superficie de seguridad (no hay endpoints de administración de tenants expuestos).

### Negativas / trade-offs
- El alta de un complejo requiere intervención del equipo por CLI.
- A escala (muchos complejos) habrá que construir el panel (futuro ADR).

## Impacto en el sistema
- Backend: management command `create_tenant` en la app `tenants`.
- DevOps: el script de arranque usa el comando para seedear el tenant de prueba.
- Seguridad: no se exponen endpoints de gestión de tenants; el `system_admin` opera en `public`.

## Documentos actualizados
- `docs/ARCHITECTURE.md` §10, `docs/SPRINT_0.md`

## Revisión futura
Construir un panel de `system_admin` cuando el alta manual no escale.
