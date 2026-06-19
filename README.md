# SaaS Gestión de Canchas — Documentación IA-Ready

Sistema operativo documental del proyecto **SaaS de Gestión y Reserva de Complejos Deportivos** (Fútbol 5/7 y Pádel), multi-tenant y marca blanca. Esta carpeta convierte el contexto del proyecto en documentación ejecutable para que el equipo (Milton, Luka, Erik, Cris, Nacho) y los agentes IA construyan software real sin romper arquitectura ni trazabilidad.

> La IA acelera el desarrollo, pero si no existe documentación ejecutable, acelera el caos.

## El proyecto en una línea

Un "recepcionista digital 24/7": cada complejo (tenant) tiene su URL de reservas en la nube integrada a su Instagram/WhatsApp, con grilla pública de turnos, motor de reservas sin overbooking y caja diaria básica. Objetivo: un MVP robusto, probado con un **Cliente Cero** real durante el semestre y vendible a un cliente.

## Stack

React + Vite + TypeScript + Tailwind (frontend, mobile-first) · Django REST Framework + PostgreSQL + `django-tenants` + Simple JWT (backend) · Docker. Detalle completo en `docs/STACK.md`.

## Reglas de arquitectura no negociables

- Multi-tenant por **esquema PostgreSQL** (`django-tenants`); nunca `tenant_id` compartido para datos críticos.
- Motor de reservas con bloqueo pesimista (`select_for_update()`) para evitar overbooking.
- La reserva nace en `PENDING_PAYMENT` (seña por transferencia, conciliación manual).
- Fechas en UTC; conversión a `America/Argentina/Buenos_Aires` en presentación.
- Soft-delete (`is_active`); prohibido `DELETE` físico.
- El backend es el source of truth; el frontend solo consume.

## Estructura del kit

```txt
reserva-canchas/
├── .claude/                    # Config ejecutable de Claude Code
│   ├── agents/                 # Subagentes (instrucciones + delegación) — fuente única
│   │   ├── orchestrator.md     # Milton (PO/Analista)
│   │   ├── backend.md          # Luka + Erik
│   │   ├── frontend.md         # Cris + Nacho
│   │   ├── devops.md
│   │   ├── security.md
│   │   └── qa.md
│   └── commands/               # Slash commands (/sprint-0, /nueva-feature, /revisar-seguridad)
├── docs/                       # Source of truth (contexto, arquitectura, reglas, RBAC, API, sprint 0)
│   ├── PROJECT_CONTEXT.md
│   ├── ARCHITECTURE.md
│   ├── STACK.md
│   ├── RULES.md
│   ├── FOLDER_STRUCTURE.md
│   ├── WORKFLOW.md
│   ├── RBAC.md
│   ├── API_GUIDELINES.md
│   ├── SPRINT_0.md
│   ├── DER.md                  # Modelo de datos core
│   └── USER_STORIES.md         # Historias INVEST
├── prompts/
│   ├── MASTER_PROMPT.md        # Prompt maestro del Orchestrator
│   └── AGENT_TASK_TEMPLATE.md
├── templates/
│   ├── FEATURE_SPEC_TEMPLATE.md  # incluye ejemplo: Motor de Reservas
│   ├── ADR_TEMPLATE.md           # incluye ejemplo: ADR-001 django-tenants
│   └── PR_CHECKLIST.md
└── checklists/
    ├── ARCHITECTURE_CHECKLIST.md
    └── RELEASE_READINESS_CHECKLIST.md
```

## Equipo y roles

| Integrante | Rol | Agente IA |
|---|---|---|
| Milton | Analista Funcional & PO (negocio, Jira, DER, HU) | Orchestrator |
| Luka | Backend Lead & Arquitectura DB (Django, PostgreSQL, `django-tenants`, Docker) | Backend |
| Erik | Backend API (DRF, modelos, motor de reservas, Swagger) | Backend |
| Cris | Frontend Lead & UX (React/Vite/Tailwind, design system) | Frontend |
| Nacho | Frontend UI (grilla, vistas transaccionales, consumo API) | Frontend |

Workflow: Sprints de 2 semanas. Tablero Jira: **To Do → In Progress → Code Review → QA → Done**.

## Cómo usarlo

1. Leer `docs/PROJECT_CONTEXT.md` para entender negocio y MVP.
2. Entregar `prompts/MASTER_PROMPT.md` al agente IA al iniciar una sesión.
3. Respetar `docs/RULES.md` como constitución del proyecto.
4. Usar `prompts/AGENT_TASK_TEMPLATE.md` para cada tarea de Jira.
5. Registrar decisiones relevantes con `templates/ADR_TEMPLATE.md`.
6. No iniciar features hasta cerrar `docs/SPRINT_0.md` (`SPRINT_0_STATUS: READY_FOR_FEATURES`).

## Regla principal

> Ningún agente debe improvisar arquitectura, carpetas, permisos, endpoints, estados ni lógica de negocio fuera de lo definido en estos documentos. En particular: nunca romper el aislamiento multi-tenant ni la concurrencia de reservas.

---

## Ejecución local (Docker)

### Requisitos previos

- Docker Desktop instalado y corriendo.
- Git (para clonar el repo).
- En Windows: agregar la entrada al archivo `hosts` para el tenant demo (ver paso 3).

### Paso 1 — Clonar y preparar el entorno

```bash
git clone <url-del-repo>
cd reserva-canchas
cp .env.example .env
```

Editá `.env` y reemplazá los placeholders:

| Variable | Qué poner |
|---|---|
| `DJANGO_SECRET_KEY` | Una clave larga y aleatoria (ver comentario en `.env.example`) |
| `POSTGRES_PASSWORD` | Una contrasena segura (no usar la del ejemplo en produccion) |
| El resto | Los valores por defecto del `.env.example` funcionan para desarrollo local |

### Paso 2 — Levantar todo con un comando

```bash
docker compose up --build
```

Esto hace automaticamente:

1. Levanta PostgreSQL 16 y espera a que este listo (healthcheck).
2. Instala dependencias Python y Node dentro de los contenedores.
3. Ejecuta `migrate_schemas --shared` (esquema `public`: Tenant, Domain).
4. Ejecuta `migrate_schemas` (esquema `demo`: Users, Courts, Bookings, Cashbox).
5. Crea el tenant de prueba `demo` con su dominio `demo.localhost` (idempotente).
6. Arranca el backend Django en `http://localhost:8000` (modo dev con runserver).
7. Arranca el frontend Vite en `http://demo.localhost:5173` (con hot reload).

### Paso 3 — Configurar hostnames locales en Windows (unico paso manual)

Los tenants y el panel de system admin resuelven por subdominio. Agregar al archivo
`hosts` de Windows (requiere abrir el Bloc de Notas como Administrador):

```
# Archivo: C:\Windows\System32\drivers\etc\hosts
127.0.0.1  demo.localhost
127.0.0.1  platform.localhost
```

En Linux/macOS: editar `/etc/hosts` con `sudo`.

Agregar una nueva linea por cada tenant adicional que se cree (ej: `127.0.0.1 complejo2.localhost`).

### Verificacion

Una vez que `docker compose up` termina de inicializar:

| Servicio | URL | Que hace |
|---|---|---|
| **Landing page** | `http://localhost:3000` | Página pública de presentación de CANCHERO! |
| Backend healthcheck | `http://localhost:8000/api/health/` | Devuelve `{"status": "ok"}` |
| Swagger UI | `http://localhost:8000/api/docs/` | Documentacion interactiva de la API |
| Frontend | `http://demo.localhost:5173` | App React (dev server con hot reload) |
| Login API | `POST http://demo.localhost:8000/api/auth/login/` | JWT con usuario del tenant demo |
| **Panel System Admin** | `http://platform.localhost:5173` | Panel interno del equipo (rol system_admin) |

### Credenciales del tenant demo (desarrollo)

El `entrypoint.sh` crea automaticamente:

- Email: `admin@demo.localhost`
- Password: `adminpass123`
- Dominio del tenant: `demo.localhost`

Cambiar estas credenciales antes de cualquier despliegue real.

### ADVERTENCIA — No perder los datos de la base de datos

> **Leer esto antes de ejecutar cualquier comando de Docker.**

La base de datos vive en un volumen Docker llamado `postgres_data`. Ese volumen **sobrevive** a reinicios y rebuilds normales, pero **se elimina permanentemente** si usas el flag `-v`.

| Comando | Qué hace con la DB |
|---|---|
| `docker compose down` | Detiene los contenedores. **La DB queda intacta.** |
| `docker compose up --build` | Rebuild y arranca. **La DB queda intacta.** |
| `git pull` + `docker compose up --build` | Actualiza el código y relanza. **La DB queda intacta.** |
| `docker compose down -v` | **BORRA LA DB PERMANENTEMENTE.** Todos los datos se pierden. |

#### Para actualizar el código sin perder datos

```bash
git pull origin master
docker compose up --build -d
```

Eso es todo. Las migraciones nuevas se aplican solas al arrancar. Los datos persisten.

#### Para empezar desde cero (reset total intencional)

Solo hacé esto si querés una base de datos limpia a propósito (por ejemplo, para replicar el entorno de otro integrante o resolver una migración rota):

```bash
# ATENCION: el siguiente comando borra todos los datos de la DB sin posibilidad de recuperacion
docker compose down -v
docker compose up --build
```

Si tenés datos que querés conservar, hacé un backup antes:

```bash
docker compose exec db pg_dump -U canchas_user canchas_db > backup_$(date +%Y%m%d_%H%M).sql
```

---

### Comandos utiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo del backend
docker compose logs -f backend

# Abrir una shell en el contenedor backend
docker compose exec backend bash

# Correr los tests del backend
docker compose exec backend pytest

# Correr las migraciones manualmente (si se agregan modelos nuevos)
docker compose exec backend python manage.py migrate_schemas --shared
docker compose exec backend python manage.py migrate_schemas

# Detener los contenedores (DB intacta)
docker compose down

# Reset total — BORRA LA DB (ver advertencia arriba)
docker compose down -v
```

### Puertos expuestos

| Puerto | Servicio | Notas |
|---|---|---|
| `3000` | Landing page | HTML estático servido por Nginx Alpine |
| `8000` | Backend Django | API REST + Swagger. Accesible en `localhost:8000`, `demo.localhost:8000` y `platform.localhost:8000` |
| `5173` | Frontend Vite | Dev server con hot reload. El hostname determina el tenant activo (`demo.localhost:5173`, `platform.localhost:5173`) |
| `5432` | PostgreSQL | Solo para dev (DBeaver, TablePlus, etc.) — comentar en produccion |

### Variables de entorno requeridas

Ver `.env.example` en la raiz del proyecto. Todas las variables estan documentadas ahi.

### Rollback / reset de base de datos

Ver la sección **ADVERTENCIA — No perder los datos** más arriba antes de ejecutar esto.

```bash
# Reset total: elimina el volumen de datos (PERDES TODOS LOS DATOS, sin recuperacion)
docker compose down -v

# Volver a levantar desde cero (recrea DB, migraciones y tenant demo)
docker compose up --build
```

---

## Bot de WhatsApp (proyecto separado)

El bot de WhatsApp es un proceso **Node.js independiente** ubicado en un repositorio aparte. El panel admin del proyecto (pestaña "Asistente") muestra en tiempo real las conversaciones que el bot tiene con los jugadores.

> Repositorio del bot: [github.com/cn-10/CanchaYa_bot](https://github.com/cn-10/CanchaYa_bot)
> ⚠️ **Pendiente de renombrar** a `canchero-bot` en GitHub como parte del rebranding (Sprint 8).

### Opción A — Trabajar sin el bot (modo demo, recomendada)

No necesitás instalar el bot para desarrollar el visor. Un management command inserta conversaciones de prueba directamente en la base de datos:

```bash
# Una sola vez, después de levantar el proyecto
docker compose exec backend python manage.py seed_bot_demo
```

Abrí el panel admin en `http://demo.localhost:5173` → pestaña "Asistente". Vas a ver 3 conversaciones de prueba con mensajes realistas: reserva confirmada, cancelación y consulta de disponibilidad.

Para limpiar los datos de prueba: usá el botón 🗑️ en el visor, o corré `seed_bot_demo --clear`.

### Opción B — Con el bot real instalado

Seguí la guía completa en el README del bot. Resumen de requisitos:

- Node.js v18+, Ollama con el modelo `phi3:mini`, un número de WhatsApp para vincular
- El backend Django debe estar corriendo con `docker compose up`
- Crear al menos una cancha y sus horarios en el panel admin antes de probar

Ambas opciones son compatibles. Si tenías datos de demo y querés conectar el bot real, borrá las conversaciones de prueba desde el visor con el botón 🗑️.

---

### Produccion / Cliente Cero

El entorno Docker de este Sprint 0 es para desarrollo local. Para produccion (Cliente Cero):

- Copiar `.env.example` al servidor y completar con valores reales.
- `DJANGO_DEBUG=False` (obligatorio).
- `DJANGO_SECRET_KEY` con una clave segura y unica.
- Agregar Nginx como proxy reverso (ver `docker/nginx/` cuando se configure en Sprint 4).
- SSL con Let's Encrypt / Certbot.
- Quitar el puerto `5432` expuesto al host en `docker-compose.yml`.
- Ver checklist completo en `.claude/agents/devops.md`.
