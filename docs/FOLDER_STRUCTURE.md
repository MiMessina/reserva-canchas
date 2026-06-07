# FOLDER_STRUCTURE.md
# Estructura de Carpetas IA-Ready — SaaS Gestión de Canchas

## 1. Principio

La estructura de carpetas define responsabilidades. Los agentes IA y los devs no mezclan dominios ni escriben código en cualquier lugar. Cada dominio (canchas, reservas, caja) es una app de Django aislada.

## 2. Estructura recomendada

```txt
reserva-canchas/
├── .claude/                      # Config ejecutable de Claude Code
│   ├── agents/                   # Subagentes (instrucciones + delegación) — fuente única
│   │   ├── orchestrator.md       # Milton (PO/Analista)
│   │   ├── backend.md            # Luka + Erik
│   │   ├── frontend.md           # Cris + Nacho
│   │   ├── devops.md
│   │   ├── security.md
│   │   └── qa.md
│   └── commands/                 # Slash commands
│       ├── sprint-0.md
│       ├── nueva-feature.md
│       └── revisar-seguridad.md
├── docs/                         # Source of truth documental
│   ├── PROJECT_CONTEXT.md
│   ├── ARCHITECTURE.md
│   ├── STACK.md
│   ├── RULES.md
│   ├── FOLDER_STRUCTURE.md
│   ├── WORKFLOW.md
│   ├── RBAC.md
│   ├── API_GUIDELINES.md
│   ├── SPRINT_0.md
│   ├── DER.md                    # Modelo de datos core (entregable Sprint 0)
│   ├── USER_STORIES.md           # Historias INVEST (entregable Sprint 0)
│   └── adr/                      # Architecture Decision Records (ADR-001..00N)
├── backend/
│   ├── apps/
│   │   ├── tenants/              # Modelo Tenant + Domain (esquema public)
│   │   ├── users/                # Custom User, JWT, roles
│   │   ├── courts/               # Court + ScheduleBlock (ABM canchas y horarios)
│   │   ├── bookings/             # Motor de reservas, concurrencia, estados
│   │   └── cashbox/              # Caja diaria, conciliación de señas
│   │       ├── models.py
│   │       ├── services.py       # Lógica de negocio (concurrencia, transiciones)
│   │       ├── selectors.py      # Queries de lectura complejas (disponibilidad)
│   │       ├── serializers.py
│   │       ├── views.py
│   │       ├── permissions.py
│   │       ├── urls.py
│   │       └── tests/
│   ├── config/                   # settings (SHARED_APPS / TENANT_APPS), urls, wsgi
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # bootstrap, providers (QueryClient, router)
│   │   ├── components/           # componentes compartidos (Button, Modal, etc.)
│   │   ├── features/
│   │   │   ├── booking/          # grilla pública + flujo de reserva (jugador)
│   │   │   ├── courts/           # ABM de canchas (admin)
│   │   │   └── cashbox/          # caja diaria (cajero)
│   │   ├── hooks/
│   │   ├── lib/                  # axios client, helpers de fecha/timezone
│   │   ├── routes/
│   │   ├── services/             # llamadas a la API (por dominio)
│   │   └── types/                # tipos del contrato de API
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── nginx/
│   └── scripts/
├── templates/                    # Plantillas de trabajo (feature spec, ADR, PR)
├── checklists/
├── docker-compose.yml
└── README.md
```

## 3. Responsabilidades por carpeta

| Carpeta | Responsabilidad | Agente / Owner |
|---|---|---|
| `.claude/agents/` | Subagentes (instrucciones por rol + delegación ejecutable). **Fuente única** | Orchestrator (Milton) |
| `.claude/commands/` | Slash commands (`/sprint-0`, `/nueva-feature`, `/revisar-seguridad`) | Orchestrator (Milton) |
| `docs/` | Source of truth documental | Orchestrator (Milton) |
| `backend/apps/tenants`, `users` | Multi-tenant, auth, roles | Backend Lead (Luka) |
| `backend/apps/courts`, `bookings`, `cashbox` | Negocio: canchas, reservas, caja | Backend API (Erik) |
| `frontend/features/booking` | Grilla pública y reserva del jugador | Frontend (Nacho) |
| `frontend/features/courts`, `cashbox`, `app/` | Panel admin y arquitectura UI | Frontend Lead (Cris) |
| `docker/`, `docker-compose.yml` | Infra local y despliegue | DevOps (rotativo) |
| `checklists/` | Validaciones de calidad | QA + Orchestrator |

> **Agentes: una sola carpeta.** Las instrucciones de cada subagente viven en `.claude/agents/*.md`
> (frontmatter que lee Claude Code para delegar + el detalle del rol en el cuerpo). No hay una carpeta
> paralela de documentación: si cambia un rol, se edita un solo archivo.

## 4. Reglas de separación

- `frontend/` no contiene lógica de negocio crítica (disponibilidad, precios, concurrencia).
- `backend/apps/[domain]/services.py` contiene las reglas de negocio del dominio.
- `backend/apps/bookings/services.py` es el único lugar donde vive el motor de reservas y `select_for_update()`.
- `backend/apps/[domain]/selectors.py` contiene queries de lectura (ej: cálculo de grilla de disponibilidad).
- `frontend/src/features/[domain]` agrupa pantallas y componentes por dominio.
- `frontend/src/components` solo contiene componentes compartidos.
- `frontend/src/lib` centraliza el cliente Axios y la conversión de timezone UTC ↔ Buenos Aires.

## 5. Prohibiciones

- No crear `utils.py` gigante con lógica mezclada.
- No crear `components/misc`.
- No mezclar lógica de dominios (reservas en `courts`, caja en `bookings`, etc.).
- No poner el motor de reservas fuera de `bookings/services.py`.
- No duplicar la conversión de fecha/timezone en cada componente: centralizarla en `lib`.
- No crear carpetas nuevas sin documentarlas acá.
