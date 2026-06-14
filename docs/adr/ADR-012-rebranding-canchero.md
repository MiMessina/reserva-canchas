# ADR-012: Rebranding del producto — de CanchaYA a CANCHERO!

**Fecha:** 2026-06-14
**Estado:** Aprobado
**Responsable:** Milton (Orchestrator / PO)

## Contexto

El nombre comercial original del producto es `CanchaYA`. Durante el desarrollo del MVP se identificó que el nombre **CANCHERO!** posiciona mejor el producto para el segmento objetivo (complejos de fútbol 5/7 y pádel en CABA/GBA):

- Es más coloquial y reconocible en la cultura del fútbol argentino ("ser canchero").
- Diferencia mejor el producto de competidores genéricos.
- Es más memorable para el "Cliente Cero" y para una eventual expansión comercial.

El cambio es **puramente cosmético y de naming**: no implica modificaciones de arquitectura, modelos de datos, esquemas PostgreSQL, lógica de negocio, endpoints de API ni migraciones.

## Decisión

Se aprueba el rebranding de `CanchaYA` → `CANCHERO!` con las siguientes reglas de aplicación:

| Contexto | Nombre a usar | Ejemplo |
|---|---|---|
| UI visible (navbar, login, título, emails) | `CANCHERO!` | `CANCHERO!` |
| Identificadores técnicos (package, localStorage, alias CBU, dominios) | `canchero` | `canchero_access`, `canchero.com` |
| Título de API (Swagger) | `CANCHERO! API` | `"TITLE": "CANCHERO! API"` |

El signo `!` **no se usa** en identificadores técnicos (nombres npm, keys de localStorage, emails, dominios) por restricciones de esos sistemas.

## Alternativas consideradas

| Alternativa | Decisión |
|---|---|
| Mantener `CanchaYA` | Descartada — el stakeholder aprobó el cambio de nombre |
| `CANCHERO` (sin `!`) | Descartada — el `!` forma parte de la identidad visual aprobada |
| Cambiar también el dominio/URL del producto | Fuera de alcance del MVP; se evaluará al salir a producción con el Cliente Cero |

## Alcance del cambio (Sprint 8)

### Archivos a modificar

**Documentación:**
- `docs/PROJECT_CONTEXT.md` — nombre del producto
- `docs/ERS.md` — ~7 ocurrencias del nombre
- `PROGRESS.md` — título del documento
- `README.md` — referencia al repo del bot

**Backend:**
- `backend/config/settings.py` — título Swagger y email noreply
- `backend/apps/bookings/notifications.py` — firma de emails (3 ocurrencias)
- `backend/apps/agent/management/commands/seed_bot_demo.py` — mensajes demo y alias CBU
- `.env.example` — dominio y email de ejemplo

**Frontend:**
- `frontend/index.html` — `<title>`
- `frontend/src/components/NavBar.tsx` — texto de marca (2 ocurrencias)
- `frontend/src/features/auth/LoginPage.tsx` — texto de marca
- `frontend/src/lib/axios.ts` — keys de localStorage (`canchaYA_access` → `canchero_access`)
- `frontend/package.json` — nombre del paquete npm

**Generado automáticamente (no editar a mano):**
- `frontend/package-lock.json` — se regenera con `npm install`

### Archivos NO afectados

- Toda la lógica de negocio (`services.py`, `selectors.py`, modelos, migraciones)
- Esquemas PostgreSQL y datos de tenants
- Endpoints de API
- Tests
- Configuración Docker / docker-compose

## Consecuencias

### Positivas
- Identidad comercial más fuerte para presentación al Cliente Cero.
- Cambio atómico, reversible con un solo commit.

### Negativas / trade-offs
- Las keys de `localStorage` cambian (`canchaYA_access` → `canchero_access`): cualquier usuario logueado en el entorno dev quedará deslogueado al levantar la nueva versión. Acción requerida: limpiar el storage del browser una sola vez.
- El link al repo del bot en `README.md` (GitHub) no puede cambiar sin renombrar el repositorio remoto; se documenta como pendiente.

## Impacto por capa

| Capa | Impacto | Acción |
|---|---|---|
| Base de datos | Ninguno | — |
| Migraciones | Ninguno | — |
| API / endpoints | Ninguno (solo título Swagger) | — |
| Frontend | Mínimo (display + localStorage keys) | Limpiar storage en dev |
| Emails | Solo firma en notificaciones | — |
| Docker | Ninguno | — |
| Tests | Ninguno | — |

## Documentos actualizados
- `docs/PROJECT_CONTEXT.md` (nombre del producto)
- `docs/ERS.md` (nombre del producto)
- `PROGRESS.md` (título)
- `docs/ARCHITECTURE.md` §10 (esta lista de ADRs)

## Revisión futura
Cuando se defina el dominio de producción del Cliente Cero, evaluar si `canchero.com` / `canchero.com.ar` está disponible y actualizar `.env.example` y la documentación de despliegue con el dominio real.
