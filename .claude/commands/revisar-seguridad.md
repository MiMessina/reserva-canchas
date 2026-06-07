---
description: Corre la revisión del agente de seguridad sobre una ruta o feature (JWT, RBAC, aislamiento multi-tenant, datos sensibles, auditoría).
argument-hint: <ruta o feature a revisar>
---

Delegá en el subagente **security** una revisión de seguridad sobre: **$ARGUMENTS**.

El subagente debe leer `docs/RULES.md`, `docs/RBAC.md`, `docs/ARCHITECTURE.md`, `docs/API_GUIDELINES.md` y aplicar su checklist de revisión:

- JWT requerido (salvo grilla pública, igual acotada al tenant del dominio).
- Rol validado según `RBAC.md` + pertenencia al tenant / esquema correcto.
- Ownership (el jugador solo cancela sus propias reservas).
- Exposición de datos sensibles del jugador; rate limit en endpoints públicos.
- Auditoría de acciones críticas (reserva, confirmación, caja).
- Manejo de errores sin filtrar info interna; secrets fuera del repo; `DEBUG=False` en prod.
- Tests de permisos y de **aislamiento multi-tenant**.

Devolvé el informe con el formato del agente: Riesgos · Severidad (Crítica/Alta/Media/Baja) · Archivos afectados · Mitigación recomendada · Tests sugeridos (incluir siempre aislamiento de tenant y permisos por rol).
