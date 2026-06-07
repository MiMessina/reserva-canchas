# ADR_TEMPLATE.md
# Architecture Decision Record

> Plantilla reutilizable. Más abajo, un **ejemplo resuelto** (ADR-001) del proyecto.

## ADR-[Número]: [Título]

**Fecha:** `[YYYY-MM-DD]`
**Estado:** Propuesto / Aprobado / Rechazado / Reemplazado
**Responsable:** `[Nombre / Agente]`

## Contexto

`[Qué problema o decisión se debe resolver.]`

## Decisión

`[Qué se decidió.]`

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| `[Alternativa 1]` | `[Ventajas]` | `[Desventajas]` |

## Consecuencias

### Positivas

- `[Consecuencia positiva]`

### Negativas / trade-offs

- `[Consecuencia negativa]`

## Impacto en el sistema

- Backend: `[Impacto]`
- Frontend: `[Impacto]`
- DevOps: `[Impacto]`
- Seguridad: `[Impacto]`

## Documentos actualizados

- `[Documento]`

## Revisión futura

`[Cuándo o bajo qué condición se revisa esta decisión.]`

---

# EJEMPLO RESUELTO

## ADR-001: Multi-tenant por esquema PostgreSQL con `django-tenants`

**Fecha:** 2026-06-02
**Estado:** Aprobado
**Responsable:** Luka (Backend Lead) / Milton (Orchestrator)

## Contexto

Es un SaaS B2B donde cada complejo deportivo es un cliente independiente. Los datos de reservas y caja son sensibles y no pueden mezclarse entre complejos. Necesitamos una estrategia multi-tenant que garantice aislamiento desde el día cero y que escale a decenas de complejos.

## Decisión

Usar **aislamiento por esquema PostgreSQL** mediante `django-tenants`: un esquema por complejo, resuelto por dominio/subdominio. Las apps compartidas (`tenants`, `users`) viven en `public`; las de negocio (`courts`, `bookings`, `cashbox`) viven en cada esquema de tenant.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| Columna `tenant_id` compartida (row-level) | Simple de implementar, una sola DB | Riesgo alto de fuga entre tenants por un `filter` olvidado; mezcla datos críticos |
| Base de datos por tenant | Aislamiento máximo | Costo operativo y de migraciones alto para un equipo chico |
| Esquema por tenant (`django-tenants`) | Aislamiento fuerte a nivel DB, una sola instancia, librería madura | Migraciones en dos pasos (shared/tenant); más curva inicial |

## Consecuencias

### Positivas

- Aislamiento real: imposible leer datos de otro complejo con un query normal.
- Un `filter` olvidado no expone datos de otros tenants.
- Escala razonablemente para el segmento objetivo (2-5 canchas por complejo).

### Negativas / trade-offs

- Migraciones en dos comandos (`migrate_schemas --shared` y `migrate_schemas`).
- Mayor complejidad inicial de setup y de tests.

## Impacto en el sistema

- Backend: estructura `SHARED_APPS` / `TENANT_APPS`, middleware de tenant, modelos `Tenant`/`Domain`.
- Frontend: el tenant se infiere del dominio; el front no maneja `tenant_id`.
- DevOps: scripts de migración shared + tenant; seed de tenant de prueba.
- Seguridad: tests de aislamiento obligatorios; auditoría por tenant.

## Documentos actualizados

- `docs/ARCHITECTURE.md`, `docs/STACK.md`, `docs/RBAC.md`, `docs/SPRINT_0.md`

## Revisión futura

Revisar si el volumen de tenants supera lo que un único PostgreSQL maneja cómodamente, o si aparece la necesidad de sharding.
