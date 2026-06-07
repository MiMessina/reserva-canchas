# SPRINT_0.md
# Sprint 0 — Cimientos del Proyecto (SaaS Gestión de Canchas)

## 1. Regla de oro

> No se programa el motor de reservas ni features de negocio en Sprint 0.

El objetivo es construir la plataforma multi-tenant antes de construir la aplicación. Sin estos cimientos, el "Cliente Cero" no es viable.

## 2. Distribución recomendada

| Área | Porcentaje |
|---|---:|
| Cimientos técnicos y arquitectura (multi-tenant, auth, Docker) | 70% |
| Features de negocio | 0% |
| Preparación funcional (DER, contrato API, historias de usuario) | 30% |

## 3. Backend base (Luka + Erik)

Entregables:

- repo backend con estructura modular (`apps/tenants`, `users`, `courts`, `bookings`, `cashbox` vacías pero creadas);
- configuración Django + `config/settings` con `SHARED_APPS` / `TENANT_APPS`;
- **`django-tenants` funcionando**: crear un tenant de prueba y su esquema;
- conexión a PostgreSQL;
- Custom User model (Admin / Player) heredando de `AbstractUser`;
- autenticación JWT (Simple JWT): login / refresh;
- permisos base (RBAC inicial);
- service layer inicial (carpetas `services.py` por app, vacías);
- healthcheck (`/api/health/`);
- Swagger (`drf-spectacular`) sirviendo el contrato base;
- tests mínimos (healthcheck, login, aislamiento de tenant).

## 4. Frontend base (Cris + Nacho)

Entregables:

- repo frontend React + Vite + **TypeScript**;
- Tailwind configurado (Mobile-First);
- layout principal y sistema de rutas (React Router);
- cliente HTTP central (Axios) + interceptor para el JWT;
- React Query (QueryClient provider);
- helper de timezone (UTC ↔ `America/Argentina/Buenos_Aires`) en `lib/`;
- manejo de auth (login, guardado de token, ruta protegida);
- estados base loading / error / empty reutilizables;
- componentes base y design system mínimo;
- consumo del contrato de API (mocks o Swagger) para no depender del backend final.

## 5. DevOps inicial (rotativo)

Entregables:

- `Dockerfile` backend;
- `Dockerfile` frontend;
- `docker-compose.yml` con `backend`, `frontend`, `db` (PostgreSQL);
- `.env.example` versionado (sin secretos);
- scripts de arranque (migraciones shared + tenant, superuser);
- logs visibles;
- README de ejecución local (cómo levantar todo con un comando).

> Redis/Celery NO se incluyen en Sprint 0 (son Post-MVP).

## 6. Documentación obligatoria (Milton — PO/Analista)

Antes de avanzar a Sprint 1 deben existir y estar completos:

- `PROJECT_CONTEXT.md` ✔
- `ARCHITECTURE.md` ✔
- `STACK.md` ✔
- `RULES.md` ✔
- `FOLDER_STRUCTURE.md` ✔
- `WORKFLOW.md` ✔
- `RBAC.md` ✔
- `API_GUIDELINES.md` ✔
- **DER core** validado (User, Court, ScheduleBlock, Booking, CashMovement).
- **Contrato de API** (Swagger/JSON mocks) acordado para destrabar al frontend.
- Historias de usuario iniciales del Motor de Reservas (formato INVEST).

## 7. Definition of Done del Sprint 0

Sprint 0 está completo si:

- el proyecto corre localmente con `docker compose up`;
- backend y frontend se comunican (login real);
- existe autenticación JWT y permisos base;
- **`django-tenants` aísla dos tenants de prueba** (uno no ve datos del otro);
- la DB migra sin errores (shared + tenant);
- los contenedores levantan de forma reproducible;
- hay estructura modular de apps;
- hay tests mínimos (incluido un test de aislamiento de tenant);
- existe el contrato de API en Swagger;
- el equipo puede crear features sin romper arquitectura;
- los agentes IA tienen documentación suficiente para no improvisar.

## 8. No permitido en Sprint 0

- el motor de reservas (concurrencia, estados);
- grilla pública final;
- módulo de caja final;
- IA aplicada / agente WhatsApp;
- pasarelas de pago o AFIP;
- dashboards o reportes avanzados.

## 9. Salida de Sprint 0

Al finalizar, el Orchestrator emite:

```txt
SPRINT_0_STATUS: READY_FOR_FEATURES
```

Si falta documentación o arquitectura:

```txt
SPRINT_0_STATUS: BLOCKED
Motivo: [explicación]
```
