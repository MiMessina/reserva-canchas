# ADR-010: django-cors-headers para comunicación frontend ↔ backend

**Fecha:** 2026-06-02
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator) / Luka (Backend Lead)

## Contexto

El frontend (Vite, `http://localhost:5173`) y el backend (Django, `http://localhost:8000`) corren en
orígenes distintos en desarrollo. Sin una política CORS explícita, el navegador bloquea las peticiones
del frontend al backend, lo que impide el "login real" que exige la Definition of Done de Sprint 0
(`docs/SPRINT_0.md` §7). La revisión de seguridad lo marcó como bloqueante (R-03).

## Decisión

Agregar la dependencia **`django-cors-headers`** al backend y configurar `CORS_ALLOWED_ORIGINS` por
entorno (vía variable de entorno `DJANGO_CORS_ALLOWED_ORIGINS`). En desarrollo: `http://localhost:5173`.
En producción: el dominio real del complejo. No se usa `CORS_ALLOW_ALL_ORIGINS`.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas |
|---|---|---|
| `django-cors-headers` | Estándar de facto, configurable por entorno, mantenida | Una dependencia más |
| Proxy Nginx único origen (sin CORS) | Evita CORS en runtime | Requiere Nginx también en dev; complica el `docker compose up` de Sprint 0 |
| `CORS_ALLOW_ALL_ORIGINS=True` | Cero fricción | Inseguro; expone la API a cualquier origen |

## Consecuencias

### Positivas
- El frontend puede autenticarse y consumir la API desde el navegador en dev y prod.
- Orígenes restringidos por entorno (postura segura por defecto).

### Negativas / trade-offs
- Una dependencia adicional (justificada y acotada).
- Hay que mantener `DJANGO_CORS_ALLOWED_ORIGINS` por entorno.

## Impacto en el sistema
- Backend: `corsheaders` en `INSTALLED_APPS`, `CorsMiddleware` antes de `CommonMiddleware`,
  `CORS_ALLOWED_ORIGINS` desde env; `requirements.txt` actualizado.
- DevOps: `DJANGO_CORS_ALLOWED_ORIGINS` en `.env.example` (raíz) y compose.
- Seguridad: revisar que en producción solo figure el dominio real.

## Documentos actualizados
- `docs/STACK.md` (dependencia backend), `docs/ARCHITECTURE.md` §10

## Revisión futura
Si en producción se sirve front+back bajo el mismo origen detrás de Nginx (Sprint 4), CORS puede
quedar restringido al mínimo o volverse innecesario para ese origen.
