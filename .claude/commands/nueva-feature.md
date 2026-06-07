---
description: Planifica una nueva feature con el formato del Orchestrator y delega en los subagentes. Exige spec funcional y Sprint 0 cerrado.
argument-hint: <nombre de la feature>
---

Actuá como **Orchestrator** y planificá la feature: **$ARGUMENTS**.

## Guard previo (obligatorio)
Antes de planificar, verificá que **Sprint 0 esté cerrado** (`SPRINT_0_STATUS: READY_FOR_FEATURES`). Si no lo está, **no avances**: respondé que primero hay que cerrar Sprint 0 (`/sprint-0`) y explicá qué falta según `docs/SPRINT_0.md` §7.

## Antes de planificar, leé
`docs/PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`, `docs/RULES.md`, `docs/WORKFLOW.md`, `docs/RBAC.md`, `docs/API_GUIDELINES.md`, `docs/DER.md`, `docs/USER_STORIES.md`.

## Pasos
1. Redactá la spec con `templates/FEATURE_SPEC_TEMPLATE.md` (problema, actores, flujo, reglas, estados, permisos, API, UI, auditoría, criterios de aceptación, fuera de alcance, riesgos).
2. Identificá dominios y subagentes (`backend`, `frontend`, `devops`, `security`, `qa`) y el orden.
3. Marcá riesgos y casos borde: concurrencia/overbooking, reservar en el pasado, aislamiento multi-tenant, timezone, transiciones inválidas.
4. Si la feature implica nueva dependencia, cambio de contrato de API, o toca multi-tenant/concurrencia/workflow → registrá un **ADR** (`templates/ADR_TEMPLATE.md`).
5. Para cada tarea concreta de delegación, usá `prompts/AGENT_TASK_TEMPLATE.md`.

## Respuesta
Usá **estrictamente** el formato de `prompts/MASTER_PROMPT.md` (Objetivo entendido · Agentes/Roles · Archivos · Plan · Riesgos y Casos Borde · Criterios de aceptación · Próximo paso/Código propuesto). Recordá exigir tests de concurrencia y aislamiento, y verificación (`pytest`, `migrate_schemas`) antes de dar la tarea por DONE.
