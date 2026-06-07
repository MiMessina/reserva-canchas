# STACK.md
# Stack Tecnológico Oficial — SaaS Gestión de Canchas

## 1. Principio

> Ningún agente ni desarrollador cambia tecnología, librería principal, framework o patrón de arquitectura sin aprobación del Orchestrator y registro ADR.

El stack está congelado para el MVP. Lo marcado como **Post-MVP** está documentado pero **no se instala** en Sprint 0.

## 2. Backend

| Componente | Tecnología oficial | Versión / Nota |
|---|---|---|
| Lenguaje | Python | 3.12+ |
| Framework | Django | 5.x |
| API | Django REST Framework (DRF) | API-First, JSON, desacoplado del front |
| Multi-tenant | `django-tenants` | Un esquema PostgreSQL por complejo |
| Autenticación | `djangorestframework-simplejwt` | JWT stateless |
| Docs de API | `drf-spectacular` (Swagger/OpenAPI) | Contrato de API obligatorio |
| CORS | `django-cors-headers` | ADR-010; orígenes por env `DJANGO_CORS_ALLOWED_ORIGINS` |
| Tareas async | Celery | **Post-MVP** (alertas, agente WhatsApp) |
| Cache / broker | Redis | **Post-MVP** (broker de Celery) |

## 3. Base de datos

| Componente | Tecnología |
|---|---|
| Motor principal | PostgreSQL 16+ |
| Migraciones | Django migrations (shared + tenant) |
| Multi-tenant | **Schema-based** (`django-tenants`) — NO `tenant_id` compartido |
| Concurrencia | Bloqueo pesimista `select_for_update()` en reservas |
| Backups | Definir antes de salir a producción con el Cliente Cero (dump diario por esquema) |
| Zona horaria | DB en **UTC**; conversión a `America/Argentina/Buenos_Aires` en capa de presentación |

## 4. Frontend

| Componente | Tecnología |
|---|---|
| Framework | React 18 |
| Build tool | Vite |
| Lenguaje | **TypeScript** |
| Estilos | Tailwind CSS (Mobile-First) |
| Server state / fetch | TanStack Query (React Query) + Axios |
| Estado cliente | Context / Zustand (solo si hace falta; evitar estado global innecesario) |
| Formularios | React Hook Form |
| Validaciones (UI) | Zod (validación de formularios; la validación dura es del backend) |
| Íconos | Lucide React |
| Routing | React Router |

## 5. DevOps

| Componente | Tecnología |
|---|---|
| Contenedores | Docker + Docker Compose (entorno estándar para los 5 integrantes) |
| Servicios en compose | `backend` (Django), `frontend` (Vite), `db` (PostgreSQL) |
| Proxy | Nginx (para producción / Cliente Cero) |
| SSL | Let's Encrypt / Certbot (producción) |
| CI/CD | GitHub Actions (lint + tests en cada PR) — incremental |
| Logs | Docker logs en local; revisar Sentry antes de producción |
| Variables | `.env` por entorno + `.env.example` versionado (sin secretos reales) |

> Redis no se levanta en Sprint 0 (Celery es Post-MVP). Se agregará al compose cuando se implemente la primera tarea async.

## 6. Testing

| Capa | Herramienta |
|---|---|
| Backend unit/service | Pytest + `pytest-django` |
| API tests | Pytest + DRF `APIClient` |
| Tests de concurrencia | Tests específicos del motor de reservas (overbooking) |
| Tests multi-tenant | Aislamiento entre esquemas |
| Frontend tests | Vitest + Testing Library |
| E2E | Playwright (flujo reserva) — incremental |
| Lint | Ruff (Python) / ESLint (TS) |
| Format | Black (Python) / Prettier (TS) |

## 7. Convenciones de versiones

- Backend: dependencias fijadas en `requirements.txt` (o `pyproject.toml`) con versiones.
- Frontend: `package-lock.json` versionado.
- Las migraciones deben ser reproducibles (shared y por tenant).
- Los cambios de API que rompan el contrato se versionan (`/api/v1/`, `/api/v2/`) y se registran en ADR.

## 8. Librerías prohibidas sin autorización

- Cualquier librería que duplique lo que ya hace DRF, `django-tenants` o React Query.
- Pasarelas de pago / SDKs de AFIP (fuera de alcance del MVP).
- Librerías abandonadas o sin mantenimiento.
- Librerías pesadas en el frontend que afecten el rendimiento mobile.
- Cualquier `npm install` / `pip install` nuevo sin justificación explícita y ADR (regla del Orchestrator).

## 9. Comandos base

```bash
# Backend (dentro del contenedor)
python manage.py migrate_schemas --shared   # migraciones del esquema public
python manage.py migrate_schemas            # migraciones de todos los tenants
python manage.py runserver
pytest

# Frontend
npm install
npm run dev
npm run build
npm run test

# Docker (entorno completo)
docker compose up -d --build
docker compose logs -f
docker compose exec backend python manage.py createsuperuser
```
