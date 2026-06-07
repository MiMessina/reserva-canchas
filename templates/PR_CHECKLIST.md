# PR_CHECKLIST.md
# Checklist de Pull Request — SaaS Gestión de Canchas

## Crítico del proyecto (revisar SIEMPRE)

- [ ] Si toca reservas, usa `select_for_update()` y respeta los estados de `WORKFLOW.md`.
- [ ] No introduce `tenant_id` compartido para datos críticos (multi-tenant por esquema).
- [ ] Las queries no cruzan esquemas de tenants.
- [ ] Fechas/horas se guardan en UTC (conversión a Buenos Aires solo en presentación).
- [ ] Usa soft-delete (`is_active`), no `DELETE` físico.

## Contexto

- [ ] El PR explica qué problema resuelve.
- [ ] La tarea tiene criterio de aceptación.
- [ ] Se identificaron archivos principales modificados.

## Arquitectura

- [ ] Respeta `ARCHITECTURE.md`.
- [ ] Respeta `FOLDER_STRUCTURE.md`.
- [ ] No introduce lógica de negocio en frontend.
- [ ] No duplica lógica existente.
- [ ] No agrega dependencias sin justificación.

## Backend

- [ ] Endpoints con permisos.
- [ ] Services para lógica compleja.
- [ ] Tests agregados/actualizados.
- [ ] Migraciones revisadas.
- [ ] Queries con scope correcto.

## Frontend

- [ ] Maneja loading.
- [ ] Maneja error.
- [ ] Maneja estado vacío.
- [ ] Es responsive.
- [ ] Usa componentes reutilizables.
- [ ] No hardcodea reglas críticas.

## Seguridad

- [ ] No expone secretos.
- [ ] Valida permisos.
- [ ] Valida tenant/ownership.
- [ ] No expone datos sensibles.
- [ ] Audita acciones críticas si corresponde.

## Documentación

- [ ] Se actualizó documentación afectada.
- [ ] Se agregó ADR si corresponde.
- [ ] Se actualizó API si corresponde.

## QA

- [ ] Tests ejecutados.
- [ ] Flujo principal probado.
- [ ] Casos de error probados.
- [ ] No rompe funcionalidades existentes.
