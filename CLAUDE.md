# CLAUDE.md — SaaS Gestión de Canchas (Multi-tenant)

> Este archivo lo carga Claude Code automáticamente al abrir el proyecto. Es la memoria viva del proyecto.

## Qué es este proyecto

SaaS B2B **multi-tenant**, marca blanca, para la gestión y reserva de complejos deportivos (Fútbol 5/7 y Pádel). Reemplaza la gestión por WhatsApp + Excel con un "recepcionista digital 24/7": grilla pública de turnos, motor de reservas sin overbooking y caja diaria básica. Objetivo: MVP robusto, probado con un "Cliente Cero" real y vendible.

## Cómo se trabaja en este repo (LEER PRIMERO)

**El desarrollo lo llevan adelante los agentes IA.** Vos (la sesión principal de Claude Code) actuás como **Orchestrator**: interpretás el pedido, leés la documentación fuente, planificás, y **delegás la ejecución en los subagentes** especializados (`.claude/agents/`). Las personas del equipo son **stakeholders**: dan dirección de negocio y aprueban; no se les asignan tareas de desarrollo.

Antes de proponer o programar cualquier cosa, leé y respetá la documentación fuente:

- @docs/PROJECT_CONTEXT.md — negocio, MVP, actores, glosario
- @docs/ARCHITECTURE.md — capas, service layer, multi-tenant, módulos
- @docs/STACK.md — tecnologías oficiales y versiones
- @docs/RULES.md — constitución del proyecto (reglas inviolables)
- @docs/FOLDER_STRUCTURE.md — dónde va cada cosa
- @docs/WORKFLOW.md — estados y transiciones de la reserva
- @docs/RBAC.md — roles, permisos y aislamiento por tenant
- @docs/API_GUIDELINES.md — diseño de la API
- @docs/SPRINT_0.md — qué construir primero (sin features)

El prompt maestro del Orchestrator está en @prompts/MASTER_PROMPT.md y debés seguir su formato de respuesta.

## Subagentes disponibles (delegá según el dominio)

- **orchestrator** — planificación, arquitectura, coordinación, ADRs. (Tu rol por defecto.)
- **backend** — Django REST Framework, modelos, motor de reservas, `django-tenants`, JWT, migraciones, tests backend.
- **frontend** — React + Vite + TypeScript + Tailwind, grilla, vistas, consumo de API.
- **devops** — Docker, docker-compose, PostgreSQL, entorno reproducible, despliegue.
- **security** — revisión de permisos, JWT, aislamiento multi-tenant, auditoría.
- **qa** — casos de prueba, concurrencia (overbooking), aislamiento, criterios de aceptación.

Delegá con el subagente apropiado y pasale el contexto. Si una tarea cruza dominios, coordinás vos (orchestrator) la secuencia.

## Reglas críticas no negociables (resumen de RULES.md)

1. **Multi-tenant por esquema PostgreSQL** (`django-tenants`). Nunca `tenant_id` compartido para datos críticos (reservas/caja).
2. **Sin overbooking**: toda reserva se crea dentro de una transacción con `select_for_update()`.
3. La reserva **nace en `PENDING_PAYMENT`** (seña por transferencia, conciliación manual). Transiciones: `PENDING_PAYMENT → CONFIRMED → COMPLETED` / `→ CANCELLED`.
4. **Fechas en UTC** en la DB; conversión a `America/Argentina/Buenos_Aires` solo en presentación.
5. **Soft-delete** (`is_active`); prohibido `DELETE` físico.
6. El **backend es el source of truth**; el frontend solo consume y nunca decide negocio/permisos/concurrencia.
7. Todo endpoint valida **JWT + tenant** (salvo la grilla pública, igual acotada al tenant del dominio).
8. **No se programan features en Sprint 0**, solo cimientos.
9. **No agregar dependencias** pip/npm sin justificación y ADR.
10. Si falta información crítica, **preguntar o marcar el supuesto**; no improvisar arquitectura.

## Stack (ver STACK.md)

- Backend: Python 3.12+ · Django 5.x · DRF · PostgreSQL 16+ · `django-tenants` · Simple JWT · `drf-spectacular`.
- Frontend: React 18 · Vite · TypeScript · Tailwind (mobile-first) · TanStack Query + Axios · React Hook Form + Zod.
- DevOps: Docker + Docker Compose. (Redis/Celery son **post-MVP**, no instalar en Sprint 0.)

## Comandos de proyecto (slash commands en .claude/commands/)

- `/sprint-0` — arranca el Sprint 0 (cimientos: multi-tenant, auth, Docker, contrato API).
- `/nueva-feature <nombre>` — planifica una feature con el formato del Orchestrator y delega.
- `/revisar-seguridad <ruta o feature>` — corre la revisión del agente de seguridad.

## Comandos de stack (una vez exista el código)

```bash
# Backend (en el contenedor)
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
pytest

# Frontend
npm install && npm run dev && npm run test

# Entorno completo
docker compose up -d --build
```

## Estado actual

El repositorio contiene la **documentación y el entorno de agentes**, no código todavía. El primer paso de desarrollo es ejecutar `/sprint-0`: el Orchestrator coordina a `devops` (Docker + Postgres), `backend` (django-tenants + custom user + JWT + estructura modular) y `frontend` (React+Vite+TS base), sin programar features de negocio. Al cerrar Sprint 0, el Orchestrator emite `SPRINT_0_STATUS: READY_FOR_FEATURES`.
