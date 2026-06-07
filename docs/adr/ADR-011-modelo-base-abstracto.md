# ADR-011: Modelo base abstracto (TimeStamped + SoftDelete) en `apps/common`

**Fecha:** 2026-06-07
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator) / Erik (Backend API)

## Contexto

`RULES.md` y `ARCHITECTURE.md` §6 exigen que **toda entidad** tenga `is_active` (soft-delete),
`created_at` y `updated_at`. En Sprint 0, el modelo `User` definió esos campos a mano. A partir de
Sprint 1 entran `Court` y `ScheduleBlock`, y en Sprints 2-3 `Booking` y `CashMovement`: repetir los
mismos tres campos en cada modelo duplica código y abre la puerta a inconsistencias (un modelo que se
olvide del soft-delete y permita `DELETE` físico).

## Decisión

Se crea una app **`backend/apps/common/`** con un modelo abstracto reutilizable:

```python
class TimeStampedSoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)        # soft-delete
    created_at = models.DateTimeField(auto_now_add=True) # UTC
    updated_at = models.DateTimeField(auto_now=True)     # UTC

    class Meta:
        abstract = True
```

`Court`, `ScheduleBlock` y los modelos de negocio de Sprints siguientes heredan de esta base.
`User` **no** se migra a la base en este ADR (su soft-delete viene de `AbstractBaseUser.is_active`
y tocarlo implicaría una migración de auth innecesaria); queda como deuda menor opcional.

`apps.common` va en **TENANT_APPS** y **no define tablas propias** (solo modelos abstractos), por lo
que no genera migraciones con tablas en ningún esquema.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| Repetir los 3 campos en cada modelo | Sin carpeta nueva | Duplicación; riesgo de olvido del soft-delete; contra DRY |
| Modelo base en `apps/common` (elegida) | DRY; soft-delete garantizado por herencia; un solo lugar para auditar | Carpeta nueva (requiere actualizar `FOLDER_STRUCTURE.md`) |
| Usar una librería externa (django-model-utils) | Listo de fábrica | Dependencia nueva sin justificación fuerte (regla del Orchestrator); preferimos 10 líneas propias |

## Consecuencias

### Positivas
- Soft-delete y timestamps consistentes en todo el dominio por herencia.
- Punto único para evolucionar la base (ej: agregar `deleted_at` o un manager que excluya inactivos).

### Negativas / trade-offs
- Carpeta nueva `apps/common` (documentada en `FOLDER_STRUCTURE.md`).
- `User` queda fuera de la base por ahora (inconsistencia menor y deliberada).

## Impacto en el sistema
- Backend: nueva app `apps/common` en `TENANT_APPS`; `Court`/`ScheduleBlock` heredan de la base.
- Migraciones: `apps.common` no genera tablas (modelo abstracto); las migraciones de `courts` incluyen
  los campos heredados.
- Sin impacto en frontend ni DevOps.

## Documentos actualizados
- `docs/FOLDER_STRUCTURE.md` (carpeta `apps/common`), `docs/ARCHITECTURE.md` §10 (esta lista).

## Revisión futura
Reabrir si se decide unificar `User` bajo la misma base o introducir un manager de soft-delete global
(`objects` que excluya `is_active=False`).
