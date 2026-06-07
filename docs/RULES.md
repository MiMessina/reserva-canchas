# RULES.md
# Constitución del Proyecto — SaaS Gestión de Canchas

Reglas inviolables. Todo agente IA y todo desarrollador humano (Milton, Luka, Erik, Cris, Nacho) debe obedecerlas.

## 1. Reglas de arquitectura

- El backend (DRF) es el source of truth. El frontend nunca decide negocio.
- La lógica compleja (motor de reservas, concurrencia, transiciones, caja) vive en `services.py`.
- Los serializers validan estructura, no gobiernan el negocio.
- El multi-tenant es por **esquema PostgreSQL** (`django-tenants`). Prohibido `tenant_id` compartido para datos críticos.
- No se crea una carpeta/módulo nuevo sin actualizar `FOLDER_STRUCTURE.md`.
- No se agrega una dependencia (pip/npm) nueva sin justificarla y registrar ADR.
- No se rompe compatibilidad de la API sin versionar y registrar ADR.

## 2. Reglas de seguridad

- Todo endpoint requiere autenticación JWT y validación de tenant, salvo la grilla pública (que igual valida el tenant por dominio).
- Toda query sensible respeta el esquema del tenant; ningún usuario accede a datos de otro complejo.
- No se guardan secretos en el repo. No se hardcodean tokens, claves ni credenciales (usar `.env`).
- Toda acción crítica (reserva, confirmación, caja) debe ser auditable.
- En producción, `DEBUG = False` y los errores no exponen stack traces.

## 3. Reglas de frontend

- Componentes reutilizables; nada de lógica de negocio crítica en el cliente.
- No hardcodear estados, precios ni disponibilidad que vienen del backend.
- Mobile-first y responsive (el jugador reserva desde el celular).
- Toda pantalla maneja loading, empty y error states.
- Usar React Query para server state; invalidar cache tras cada mutación.
- Usar Lucide React como sistema de íconos.
- No mostrar acciones que el backend va a rechazar por permisos.
- No crear pantallas que no estén conectadas al flujo real.

## 4. Reglas de backend

- Toda mutación compleja pasa por un service (especialmente crear/confirmar reserva).
- **Toda reserva usa `select_for_update()`** para evitar overbooking. No hay excepción.
- Las fechas/horas se guardan en **UTC**.
- Toda transición de estado de la reserva se valida en backend.
- Soft-delete obligatorio: `is_active`. Prohibido `DELETE` físico.
- No reservar en el pasado: validar siempre.
- No hacer queries que crucen esquemas de tenants.
- No retornar más campos de los necesarios.
- Toda creación/transición relevante tiene tests (incluido test de concurrencia y de aislamiento).

## 5. Reglas de API

- Sustantivos en plural: `/api/courts/`, `/api/bookings/`, `/api/cash-movements/`.
- Acciones de dominio con rutas claras: `POST /api/bookings/{id}/confirm/`, `POST /api/bookings/{id}/cancel/`.
- Errores con formato estándar (ver `API_GUIDELINES.md`).
- Paginar listados; filtros explícitos (por fecha, cancha, estado).
- Documentar todos los endpoints en Swagger (`drf-spectacular`).
- Versionar cambios incompatibles.

## 6. Reglas de IA / agentes

- Ningún agente improvisa arquitectura: se ciñe a DRF, esquemas y a estos docs.
- Ningún agente programa features funcionales durante Sprint 0 (solo setup).
- Ningún agente mezcla responsabilidades (Frontend solo consume; el negocio vive en Backend).
- Ningún agente modifica archivos fuera de su scope sin permiso del Orchestrator.
- Ningún agente elimina código sin explicar impacto.
- Todo cambio informa archivos modificados y criterios de aceptación.
- Si falta información crítica, el agente pregunta o marca el supuesto. No avanza a ciegas.

## 7. Reglas de documentación

- Todo módulo nuevo queda documentado.
- Toda decisión importante (stack, multi-tenant, concurrencia, pagos) se registra como ADR.
- Toda regla de negocio nueva se agrega a `PROJECT_CONTEXT.md` o `WORKFLOW.md`.
- Toda modificación de estructura se refleja en `FOLDER_STRUCTURE.md`.
- Toda nueva integración se documenta en `ARCHITECTURE.md`.

## 8. Regla de oro

> Si un cambio puede romper el aislamiento multi-tenant, la concurrencia de reservas, los permisos, el workflow de la reserva o la integridad de la caja, debe ser revisado por el Orchestrator antes de implementarse.
