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

## Estructura del proyecto

```txt
reserva-canchas/
├── backend/                    # Django REST Framework + django-tenants
│   ├── apps/
│   │   ├── common/             # Modelo base abstracto (TimeStampedSoftDeleteModel)
│   │   ├── tenants/            # Modelo Tenant + Domain (schema public)
│   │   ├── users/              # Custom User, JWT, roles
│   │   ├── courts/             # ABM de canchas y ScheduleBlock
│   │   ├── bookings/           # Motor de reservas, concurrencia, estados
│   │   └── cashbox/            # Caja diaria, conciliación de señas
│   ├── config/                 # settings, urls, wsgi
│   ├── manage.py
│   └── requirements.txt
├── frontend/                   # React 18 + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── app/                # Bootstrap, providers
│   │   ├── assets/              # Estáticos importados por componentes (logo.svg, etc.)
│   │   ├── components/         # Componentes compartidos (NavBar, Sidebar, AdminLayout…)
│   │   ├── context/            # React Contexts (ThemeContext, SidebarContext)
│   │   ├── features/           # Dominios: booking, courts, cashbox, platform-admin, auth
│   │   ├── hooks/              # Hooks reutilizables
│   │   ├── lib/                # Cliente Axios, helpers de timezone
│   │   ├── routes/             # AppRouter, ProtectedRoute
│   │   └── types/              # Tipos del contrato de API
│   ├── package.json
│   └── vite.config.ts
├── landing/                    # Página pública de CANCHERO! (HTML estático, puerto 3000)
├── docker/                     # Nginx + scripts de arranque
│   └── nginx/nginx.conf        # Proxy reverso para producción
├── docker-compose.yml
├── .env.example                # Variables de entorno documentadas (sin secretos)
├── .claude/                    # Config ejecutable de Claude Code
│   ├── agents/                 # Subagentes por rol (orchestrator, backend, frontend, devops, security, qa)
│   └── commands/               # Slash commands (/sprint-0, /nueva-feature, /revisar-seguridad)
├── docs/                       # Source of truth documental
│   ├── PROJECT_CONTEXT.md
│   ├── ARCHITECTURE.md
│   ├── STACK.md
│   ├── RULES.md
│   ├── FOLDER_STRUCTURE.md
│   ├── WORKFLOW.md
│   ├── RBAC.md
│   ├── API_GUIDELINES.md
│   ├── DER.md                  # Modelo de datos core
│   └── USER_STORIES.md
├── prompts/
│   ├── MASTER_PROMPT.md
│   └── AGENT_TASK_TEMPLATE.md
├── templates/                  # ADR, Feature Spec, PR Checklist
└── checklists/                 # Architecture y Release Readiness
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

Editá `.env` y completá las variables obligatorias:

| Variable | Qué poner |
|---|---|
| `DJANGO_SECRET_KEY` | Una clave larga y aleatoria (ver comentario en `.env.example`) |
| `POSTGRES_PASSWORD` | Una contraseña segura (no usar la del ejemplo en producción) |
| `DEMO_ADMIN_PASSWORD` | **Obligatoria.** Contraseña del admin del tenant demo. El entrypoint falla si está vacía. |
| `PLATFORM_ADMIN_PASSWORD` | **Obligatoria.** Contraseña del system admin. El entrypoint falla si está vacía. |
| `VITE_CENTRAL_API_URL` | En dev: `http://app.localhost:8000/api` (valor por defecto). En producción: **obligatorio** — `http://app.<IP>.nip.io/api`. |
| El resto | Los valores por defecto del `.env.example` funcionan para desarrollo local. |

> **Si ya tenías el repo clonado y hiciste `git pull`:** comparás tu `.env` contra `.env.example`
> para detectar variables nuevas que se hayan agregado en sprints recientes. En particular,
> `PLATFORM_ADMIN_PASSWORD` se agregó en Sprint 4 (ADR-013); si tu `.env` es anterior a eso,
> no la tiene y el backend no levanta.

### Paso 2 — Levantar todo con un comando

```bash
docker compose up --build
```

Esto hace automaticamente:

1. Levanta PostgreSQL 16 y espera a que este listo (healthcheck).
2. Instala dependencias Python y Node dentro de los contenedores.
3. Ejecuta `migrate_schemas --shared` (esquema `public`: Tenant, Domain, UserEmailIndex, OneTimeCode).
4. Ejecuta `migrate_schemas` (todos los esquemas de tenant: Users, Courts, Bookings, Cashbox).
5. Crea el tenant de prueba `demo` con su dominio `demo.localhost` (idempotente).
6. Crea el superuser del Panel de System Admin (idempotente).
7. Sincroniza el índice de emails para el login centralizado (`sync_email_index`, idempotente).
8. Arranca el backend Django en `http://localhost:8000` (modo dev con runserver).
9. Arranca el frontend Vite en `http://demo.localhost:5173` (con hot reload).

### Paso 3 — Configurar hostnames locales en Windows (unico paso manual)

Los tenants, el panel de system admin y el login centralizado resuelven por subdominio.
Agregar al archivo `hosts` de Windows (requiere abrir el Bloc de Notas como Administrador):

```
# Archivo: C:\Windows\System32\drivers\etc\hosts
127.0.0.1  demo.localhost
127.0.0.1  platform.localhost
127.0.0.1  app.localhost
```

En Linux/macOS: editar `/etc/hosts` con `sudo`.

Agregar una nueva linea por cada tenant adicional que se cree (ej: `127.0.0.1 complejo2.localhost`).

> **Nota sobre `app.localhost`:** es el subdominio del login centralizado (Sprint 14).
> Sin esta entrada en el archivo `hosts`, `http://app.localhost:5173/login` no va a resolver.

### Verificacion

Una vez que `docker compose up` termina de inicializar:

| Servicio | URL | Que hace |
|---|---|---|
| **Landing page** | `http://localhost:3000` | Página pública de presentación de CANCHERO! |
| Backend healthcheck | `http://localhost:8000/api/health/` | Devuelve `{"status": "ok"}` |
| Swagger UI | `http://demo.localhost:8000/api/schema/swagger-ui/` | Documentacion interactiva de la API |
| Frontend | `http://demo.localhost:5173` | App React (dev server con hot reload) |
| Login API | `POST http://demo.localhost:8000/api/auth/login/` | JWT con usuario del tenant demo |
| **Panel System Admin** | `http://platform.localhost:5173` | Panel interno del equipo (rol system_admin) |
| **Login centralizado** | `http://app.localhost:5173/login` | Login único para tenant_admin y operator (Sprint 14) |

### Credenciales de desarrollo

El `entrypoint.sh` crea automáticamente los usuarios al levantar, usando los valores del `.env`:

**Tenant demo** (`demo.localhost`):
- Email: valor de `DEMO_ADMIN_EMAIL` (default: `admin@demo.localhost`)
- Password: valor de `DEMO_ADMIN_PASSWORD`

**Panel System Admin** (`platform.localhost:5173`):
- Email: valor de `PLATFORM_ADMIN_EMAIL` (default: `admin@platform.localhost`)
- Password: valor de `PLATFORM_ADMIN_PASSWORD`

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

## Acceso al sistema — tres puertas de entrada

El sistema tiene **tres URLs de acceso distintas**, cada una para un actor diferente. Es importante no confundirlas: usan modelos de usuario, flujos de autenticación y JWTs completamente separados.

| URL | Para quién | Qué es |
|-----|-----------|--------|
| `http://app.localhost:5173/login` | Dueños y operadores de complejos | Login centralizado — Sprint 14 |
| `http://platform.localhost:5173` | El equipo de CANCHERO! | Panel de administración del SaaS |
| `http://<tenant>.localhost:5173` | Dueños y operadores (acceso directo) | Panel del complejo específico |

---

## Panel de System Admin (`platform.localhost`)

### Qué es

El panel de system admin es la herramienta **interna del equipo de CANCHERO!** para operar el SaaS. Desde acá se dan de alta los complejos (tenants), se activan o desactivan, y se configura el modo del bot.

**No es accesible para los dueños de complejos ni para los jugadores.** Es exclusivo del rol `system_admin` (el equipo).

### Cómo acceder

```
URL: http://platform.localhost:5173
```

Tiene su propia página de login en esa misma URL. Las credenciales se definen en el `.env`:

```
PLATFORM_ADMIN_EMAIL=admin@platform.localhost   (default)
PLATFORM_ADMIN_PASSWORD=<definir en .env>       (obligatorio)
```

### Qué podés hacer

- **Listar todos los complejos** (tenants) del SaaS con su dominio, estado y modo del bot.
- **Crear un nuevo complejo:** define el nombre, el schema PostgreSQL, el dominio y las credenciales del admin inicial. El backend crea el esquema aislado automáticamente.
- **Activar / desactivar un complejo:** un complejo inactivo no permite login. Sus datos se conservan (soft-delete).
- **Cambiar el modo del bot:** `mock` (muestra conversaciones de demo) o `production` (mensajes reales del bot WhatsApp).
- **Ver el dominio como hipervínculo** para abrir directamente el panel del complejo.

### Por qué es diferente al login centralizado

| | Platform Admin | Login Centralizado |
|---|---|---|
| **URL** | `platform.localhost:5173` | `app.localhost:5173/login` |
| **Actor** | Equipo CANCHERO! | Dueños y operadores de complejos |
| **Modelo de usuario** | `PlatformAdmin` (schema public) | `User` (schema del tenant) |
| **JWT** | Claim `iss: "platform"` — no válido en endpoints de tenant | JWT estándar Simple JWT — válido en el panel del complejo |
| **Qué gestiona** | Tenants del SaaS | Canchas, reservas, caja, bot |
| **Intercambiables** | ❌ No | ❌ No |

> Un JWT obtenido en `platform.localhost` no sirve para operar un tenant, y viceversa.
> Son modelos de usuario y sistemas de auth completamente independientes.

---

## Login Centralizado (`app.localhost`)

### Qué es

Un único punto de entrada para que **dueños y operadores de cualquier complejo** inicien sesión
sin necesidad de conocer la URL específica de su subdominio. En lugar de ir a `demo.localhost:5173/login`,
el usuario va siempre a **`app.localhost:5173/login`** y el sistema detecta automáticamente a qué complejo pertenece.

### Flujo completo

```
1. El operador ingresa su email en app.localhost:5173/login
2. El sistema busca en qué complejo(s) tiene cuenta
   - 0 resultados → "Email no registrado"
   - 1 resultado  → pasa directo a la contraseña
   - N resultados → muestra selector de complejo
3. Ingresa la contraseña → el backend autentica en el schema del tenant
4. El backend genera un código de un solo uso (TTL: 60 segundos) y
   redirige el browser a http://<tenant>.localhost:5173/auth/callback?code=<otc>
5. La ruta pública /auth/callback intercambia el código por JWT
   y navega al dashboard — el código queda invalidado en el backend
```

### Restricciones

- Solo `tenant_admin` y `operator`. Los jugadores (`player`) no usan este flujo.
- El panel de system admin (`platform.localhost`) no se ve afectado — sigue igual.
- El código expira en 60 segundos y es de uso único (previene replay attacks).

### Endpoints disponibles (schema public — `app.localhost:8000`)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/auth/lookup-email/` | POST | Devuelve en qué complejo(s) existe el email |
| `/api/auth/central-login/` | POST | Autentica y genera el código de un uso |
| `/api/auth/exchange-code/` | POST | Intercambia el código por JWT (access + refresh) |

Estos endpoints responden a cualquier host que no esté registrado como dominio de tenant
(incluyendo `app.localhost` y `platform.localhost`).

### URL para una landing page o acceso directo

Si querés ofrecer a los complejos un link de acceso universal al panel de gestión,
la URL canónica es:

```
http://app.localhost:5173/login          ← desarrollo local
https://app.<tu-dominio-saas>.com/login  ← producción
```

Esta URL puede integrarse en una landing page pública, en el panel de bienvenida
del system admin, o en los correos que se envíen a los administradores de nuevos complejos.

### Agregar tenants creados antes del Sprint 14

Los usuarios creados antes de este sprint no están indexados automáticamente.
Si agregás un complejo con tenants existentes, corré:

```bash
docker compose exec backend python manage.py sync_email_index
```

Este comando es idempotente y también se ejecuta automáticamente al arrancar el backend.

---

## Bot de WhatsApp (proyecto separado)

El bot de WhatsApp es un proceso **Node.js independiente** ubicado en un repositorio aparte. El panel admin del proyecto (pestaña "Asistente") muestra en tiempo real las conversaciones que el bot tiene con los jugadores.

> Repositorio del bot: [github.com/cn-10/canchero-bot](https://github.com/cn-10/canchero-bot)

### Opción A — Trabajar sin el bot (modo demo, recomendada)

No necesitás instalar el bot para desarrollar el visor. Un management command inserta conversaciones de prueba directamente en la base de datos:

```bash
# Una sola vez, después de levantar el proyecto
docker compose exec backend python manage.py seed_bot_demo
```

Abrí el panel admin en `http://demo.localhost:5173` → pestaña "Asistente". Vas a ver 6 conversaciones de prueba con mensajes realistas: reserva confirmada, cancelación, consulta de disponibilidad, consulta de precio, reserva F7 con seña y turno ocupado con alternativa.

Para limpiar los datos de prueba: usá el botón 🗑️ en el visor, o corré `seed_bot_demo --clear`.

### Opción B — Con el bot real instalado

Seguí la guía completa en el README del bot. Resumen de requisitos:

- Node.js v18+, Ollama con el modelo `phi3:mini`, un número de WhatsApp para vincular
- El backend Django debe estar corriendo con `docker compose up`
- Crear al menos una cancha y sus horarios en el panel admin antes de probar

Ambas opciones son compatibles. Si tenías datos de demo y querés conectar el bot real, borrá las conversaciones de prueba desde el visor con el botón 🗑️.

---

### Produccion / Cliente Cero

El entorno Docker actual es para desarrollo local. Para produccion (Cliente Cero):

- Copiar `.env.prod.example` al servidor: `cp .env.prod.example .env.prod`
  y reemplazar todos los `<placeholder>` con valores reales (especialmente `<SERVER_IP>`).
- `DJANGO_DEBUG=False` (obligatorio).
- `DJANGO_SECRET_KEY` con una clave segura y unica.
- Nginx ya está configurado en `docker/nginx/nginx.prod.conf` y se activa
  automáticamente con `docker-compose.prod.yml`. No requiere configuración adicional.
- SSL con Let's Encrypt / Certbot.
- Quitar el puerto `5432` expuesto al host en `docker-compose.yml`.
- Ver checklist completo en `.claude/agents/devops.md`.

#### Deploy en Oracle Cloud Free Tier (recomendado)

Los archivos de producción ya están listos en el repo:

- `docker-compose.prod.yml` — compose de producción con Nginx reverse proxy
- `docker/nginx/nginx.prod.conf` — routing por subdominio (nip.io)
- `docker/scripts/server_setup.sh` — setup del servidor desde cero
- `docker/scripts/deploy.sh` — deploy automatizado
- `.env.prod.example` — variables de entorno con placeholders

**Instancia requerida: ARM Ampere A1 (Always Free)**
- Shape: `VM.Standard.A1.Flex`
- Mínimo: 1 OCPU + 6 GB RAM
- Recomendado: 2 OCPU + 8 GB RAM

> ⚠️ **No usar la instancia AMD E2.1.Micro** (1 GB RAM) — no tiene suficiente memoria para correr Docker + PostgreSQL + Django + Nginx juntos. El build del frontend solo requiere picos de 1-2 GB.

**Pasos para el primer deploy:**
```bash
# 1. En el servidor (una sola vez)
git clone https://github.com/MiMessina/reserva-canchas.git
cd reserva-canchas
bash docker/scripts/server_setup.sh

# 2. Configurar variables con la IP real del servidor
cp .env.prod.example .env.prod
nano .env.prod   # reemplazar todos los <SERVER_IP>

# 3. Deploy
bash docker/scripts/deploy.sh
```
