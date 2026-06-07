# AGENT_TASK_TEMPLATE.md
# Plantilla para Asignar Tareas a Agentes — SaaS Gestión de Canchas

> Copiá este bloque para cada tarea de Jira que entregues a un agente IA o a un integrante del equipo.

## Tarea

`[Nombre corto, ej: "Implementar endpoint de confirmación de reserva"]`

## Contexto

`[Qué se necesita y por qué, en términos de negocio. Ej: el cajero necesita confirmar la seña recibida por transferencia.]`

## Agente responsable

- `[Backend (Luka/Erik) / Frontend (Cris/Nacho) / DevOps / Security / QA / Orchestrator (Milton)]`

## Agentes secundarios

- `[Quién revisa o coordina. Ej: Security revisa permisos; QA valida el flujo.]`

## Documentos fuente

El agente debe leer antes de trabajar:

- `[Ej: docs/WORKFLOW.md, docs/RBAC.md, docs/API_GUIDELINES.md]`

## Alcance

### Incluido

- `[Item 1]`

### Excluido

- `[Item fuera de alcance, ej: notificaciones por WhatsApp (post-MVP)]`

## Archivos esperados

- `[Ej: backend/apps/bookings/services.py, views.py, tests/test_confirm.py]`

## Reglas específicas

- `[Ej: la transición PENDING_PAYMENT -> CONFIRMED se valida en el service y genera CashMovement.]`
- `[Ej: solo operator/tenant_admin pueden confirmar.]`

## Criterios de aceptación

- `[Criterio 1]`
- `[Criterio 2]`

## Tests requeridos

- `[Ej: test de permiso (player no puede confirmar), test de transición inválida, test de aislamiento de tenant]`

## Riesgos

- `[Ej: confirmar dos veces; doble registro en caja.]`

## Entrega esperada

El agente debe responder con:

- resumen;
- archivos modificados;
- decisiones tomadas;
- tests ejecutados;
- riesgos pendientes;
- documentación / Swagger actualizado.
