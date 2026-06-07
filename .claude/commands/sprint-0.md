---
description: Arranca el Sprint 0 (cimientos multi-tenant, auth, Docker, contrato API). NO se programan features de negocio.
---

Actuá como **Orchestrator** y coordiná el **Sprint 0** según `docs/SPRINT_0.md`. El objetivo es construir la plataforma multi-tenant **antes** que la aplicación. No se programa el motor de reservas, ni la grilla final, ni la caja, ni pagos: solo cimientos.

## Antes de arrancar, leé
`docs/SPRINT_0.md`, `docs/ARCHITECTURE.md`, `docs/STACK.md`, `docs/RULES.md`, `docs/FOLDER_STRUCTURE.md`, `docs/RBAC.md`, y respondé con el formato de `prompts/MASTER_PROMPT.md`.

## Secuencia de delegación
1. **devops** → `Dockerfile` backend/frontend, `docker-compose.yml` (`backend`, `frontend`, `db`), `.env.example`, scripts de migración + seed de tenant de prueba, healthcheck.
2. **backend** → proyecto Django + `config/settings` (`SHARED_APPS`/`TENANT_APPS`), `django-tenants` con un tenant de prueba y su esquema, Custom User (Admin/Player), Simple JWT (login/refresh), permisos base, apps modulares vacías (`tenants`, `users`, `courts`, `bookings`, `cashbox`), `/api/health/`, Swagger (`drf-spectacular`), tests mínimos.
3. **frontend** → React+Vite+TS, Tailwind, React Router, cliente Axios + interceptor JWT, React Query, helper de timezone en `lib/`, login + ruta protegida, estados base loading/empty/error.
4. **qa/security** → test de aislamiento entre dos tenants, login real back↔front, permisos base.

## Reglas del Sprint 0
- Sin features de negocio (RULES §6). Sin Redis/Celery (Post-MVP).
- Toda nueva dependencia o decisión de arquitectura → ADR (`templates/ADR_TEMPLATE.md`).
- Si delegás una tarea concreta, pasá el contexto con `prompts/AGENT_TASK_TEMPLATE.md`.

## Cierre
Cuando se cumpla la Definition of Done de `docs/SPRINT_0.md` §7, emití:
```txt
SPRINT_0_STATUS: READY_FOR_FEATURES
```
Si falta algo crítico:
```txt
SPRINT_0_STATUS: BLOCKED
Motivo: [explicación]
```

Contexto adicional del usuario (opcional): $ARGUMENTS
