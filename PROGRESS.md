# PROGRESS.md — Estado del Proyecto CANCHERO!

> Este archivo es la memoria viva del avance del proyecto.
> Se actualiza al cerrar cada sprint o tarea significativa.
> **Última actualización:** 2026-06-14 — Sprint 8 CERRADO (rebranding CANCHERO! mergeado a master)

---

## Estado general

| Sprint | Nombre | Estado |
|---|---|---|
| Sprint 0 | Cimientos multi-tenant, auth, Docker | ✅ CERRADO |
| Sprint 1 | ABM canchas, grilla pública, reservas | ✅ CERRADO |
| Sprint 2 | Caja diaria, conciliación de señas | ✅ CERRADO |
| Sprint 3 | Panel admin completo, reportes | ✅ CERRADO |
| Sprint 4 | Users/services, dark mode, agente IA | ✅ CERRADO |
| **Sprint 5** | **Visor bot WhatsApp (demo)** | ✅ CERRADO |
| **Sprint 6** | **Mejoras visor: dark mode, borrar, agenda, teléfono** | ✅ CERRADO |
| **Sprint 7** | **Fix teléfonos @lid y player_name en visor bot** | 🔵 PLANIFICADO |
| **Sprint 8** | **Rebranding CanchaYA → CANCHERO!** | ✅ CERRADO |

---

## Rama activa

**Rama:** `feat/modificacion-bot`
**Base:** `master` (commit `45193fa` — migrar agente IA de Anthropic a Gemini)
**Responsable:** Cristian Narvaez (`cristian.narvaez21@gmail.com`)

> El `/clear` de Claude Code NO elimina la rama. Solo borra el historial de conversación.
> Para retomar: `git checkout feat/modificacion-bot` y abrir este archivo.

---

## Sprint 5 — Visor bot WhatsApp (demo)

### Objetivo

Reemplazar la pestaña "Asistente" del panel admin (actualmente un chat con Gemini IA)
por un **visor en tiempo real** de las conversaciones que el bot de WhatsApp tiene con
los jugadores. Permite mostrar en la presentación, desde el panel del admin proyectado,
cómo un jugador reserva una cancha por WhatsApp en vivo.

### Contexto clave

- El bot de WhatsApp es un proceso **Node.js separado** ubicado en:
  `C:\Users\Clerc\Desktop\Analista\2do año\1er cuatrimestre\Programación 3\reserva_canchas info\bot-whatsapp`
- El bot usa: `whatsapp-web.js` (Puppeteer), Ollama `phi3:mini` (IA local, sin API key)
- El bot ya se comunica con Django para reservas usando endpoints públicos (sin JWT)
- Las conversaciones hoy se guardan SOLO en RAM del bot (se pierden al reiniciar)
- Para la demo: alguien manda mensajes WhatsApp reales desde un celular y el panel
  del admin los muestra actualizándose automáticamente cada pocos segundos

### Flujo completo de la demo

```
Celular (jugador) → WhatsApp → Bot Node.js → Django (guarda log) → Panel Admin (visor)
                                    ↓
                              API Django (reserva creada)
```

### Lo que se elimina (Gemini / agente IA actual)

| Archivo | Acción |
|---|---|
| `backend/apps/agent/services.py` | Eliminar contenido (reemplazar) |
| `backend/apps/agent/tools.py` | Eliminar contenido (reemplazar) |
| `backend/apps/agent/views.py` | Reemplazar completamente |
| `backend/requirements.txt` | Sacar dependencia `google-genai` |
| `frontend/src/features/agent/ChatDemoPage.tsx` | Reemplazar |
| `frontend/src/features/agent/components/ChatHeader.tsx` | Eliminar |
| `frontend/src/features/agent/components/ChatInput.tsx` | Eliminar |
| `frontend/src/features/agent/hooks/useChat.ts` | Eliminar |
| `frontend/src/features/agent/services/agentApi.ts` | Reemplazar |

### Tareas del Sprint 5

---

#### T5-01 — Modelo `BotConversationLog` en Django

**Archivo:** `backend/apps/agent/models.py`
**Responsable:** Cristian
**Estado:** ⬜ Pendiente

Crear modelo con los campos:
```python
class BotConversationLog(TimeStampedSoftDeleteModel):
    phone        # CharField — número de teléfono del jugador (ej: "5491112345678@c.us")
    player_name  # CharField, blank=True — nombre que dio el jugador al bot
    direction    # CharField choices: "inbound" (jugador→bot) | "outbound" (bot→jugador)
    message      # TextField — texto del mensaje
    booking      # FK nullable a Booking — si este mensaje generó una reserva
```

**Criterios de aceptación:**
- [ ] El modelo existe y migra sin errores en el esquema del tenant
- [ ] Los campos `phone`, `direction` y `message` son obligatorios
- [ ] `player_name` y `booking` son opcionales (pueden ser vacíos)
- [ ] Hereda de `TimeStampedSoftDeleteModel` (tiene `created_at`, `is_active`)

---

#### T5-02 — Endpoints de log en Django

**Archivo:** `backend/apps/agent/views.py` + `backend/apps/agent/urls.py`
**Responsable:** Cristian
**Estado:** ⬜ Pendiente

Crear dos endpoints:

**`POST /api/bot/log/`** — el bot llama esto después de cada mensaje
- Permiso: `AllowAny` (igual que los otros endpoints del bot, sin JWT)
- Body: `{ phone, direction, message, player_name?, booking_id? }`
- Guarda un `BotConversationLog` en el esquema activo del tenant
- Responde `201` con el log creado

**`GET /api/bot/conversations/`** — el panel admin consulta los logs
- Permiso: JWT requerido (`tenant_admin` u `operator`)
- Devuelve conversaciones agrupadas por `phone`, ordenadas por `created_at` DESC
- Incluye para cada conversación: lista de mensajes, `player_name` más reciente,
  y el detalle de la reserva si `booking` está relacionado
- Filtro opcional: `?phone=XXXX` para ver solo una conversación

**Criterios de aceptación:**
- [ ] `POST /api/bot/log/` responde 201 sin JWT
- [ ] `GET /api/bot/conversations/` responde 401 sin JWT y 200 con JWT válido
- [ ] Los logs quedan en el esquema del tenant correcto (aislamiento multi-tenant)
- [ ] Los mensajes aparecen ordenados cronológicamente dentro de cada conversación

---

#### T5-03 — Modificar el bot para guardar logs

**Archivo:** `bot-whatsapp/src/services/reservationService.ts`
**Directorio bot:** `C:\Users\Clerc\Desktop\Analista\2do año\1er cuatrimestre\Programación 3\reserva_canchas info\bot-whatsapp`
**Responsable:** Cristian
**Estado:** ⬜ Pendiente

En la función `handleMessage()`, después de generar la respuesta del bot:
1. Guardar el mensaje del jugador (`direction: "inbound"`)
2. Guardar la respuesta del bot (`direction: "outbound"`)
3. Si el intercambio generó una reserva, incluir el `booking_id`

El bot ya tiene `djangoApiService.ts` con el cliente axios configurado con el
header `Host: demo.localhost`. Agregar ahí la función `logMessage()`.

**Criterios de aceptación:**
- [ ] Cada mensaje del jugador queda guardado en Django como `inbound`
- [ ] Cada respuesta del bot queda guardada en Django como `outbound`
- [ ] Si el bot creó una reserva, el log `outbound` tiene el `booking_id`
- [ ] Si Django no está disponible, el bot NO se rompe (el log falla silenciosamente)

---

#### T5-04 — Visor de conversaciones en el frontend

**Directorio:** `frontend/src/features/agent/`
**Responsable:** Cristian
**Estado:** ⬜ Pendiente

Reemplazar el chat de Gemini por un visor con dos paneles:

**Panel izquierdo — lista de conversaciones:**
- Cada fila muestra: número/nombre del jugador y timestamp del último mensaje
- Al hacer click, carga esa conversación en el panel derecho
- Se actualiza automáticamente cada 5 segundos (polling con React Query)

**Panel derecho — conversación seleccionada:**
- Burbujas de chat estilo WhatsApp
  - Mensajes `inbound` (jugador): burbuja izquierda, fondo blanco
  - Mensajes `outbound` (bot): burbuja derecha, fondo verde
- Recuadro resumen en la parte superior con:
  - Nombre del jugador
  - Número de teléfono
  - Si hay reserva creada: cancha, fecha, hora, estado
- Auto-scroll al mensaje más reciente
- Se actualiza automáticamente cada 5 segundos junto con la lista

**Archivos a crear/modificar:**
```
frontend/src/features/agent/
  BotViewerPage.tsx          ← página principal (reemplaza ChatDemoPage.tsx)
  components/
    ConversationList.tsx     ← panel izquierdo
    ConversationDetail.tsx   ← panel derecho con burbujas
    BookingSummary.tsx       ← recuadro de reserva creada
  hooks/
    useBotConversations.ts   ← polling con React Query
  services/
    botApi.ts                ← GET /api/bot/conversations/
  types/
    index.ts                 ← tipos BotConversation, BotMessage, etc.
```

**Criterios de aceptación:**
- [ ] La pestaña "Asistente" muestra el visor (no el chat de Gemini)
- [ ] La lista de conversaciones se actualiza sola cada 5 segundos
- [ ] Las burbujas distinguen visualmente jugador vs bot
- [ ] Si hay reserva generada, el recuadro la muestra con cancha, fecha y hora
- [ ] Si no hay conversaciones, muestra un estado vacío descriptivo
- [ ] Funciona en mobile (responsive)

---

#### T5-05 — Limpieza: eliminar Gemini del backend

**Archivos:** `backend/apps/agent/services.py`, `backend/apps/agent/tools.py`, `backend/requirements.txt`
**Responsable:** Cristian
**Estado:** ⬜ Pendiente

- Eliminar `services.py` (AgentService con Gemini) y `tools.py` (TOOL_DEFINITIONS)
- Eliminar `google-genai` de `requirements.txt`
- Eliminar `GEMINI_API_KEY` de `backend/config/settings.py`
- Eliminar `GEMINI_API_KEY` del `.env.example` (dejar comentario de que fue removido)
- Verificar que `docker compose up --build` no falla sin la dependencia

**Criterios de aceptación:**
- [ ] El contenedor backend levanta sin `google-genai` instalado
- [ ] No quedan imports de `google.genai` en ningún archivo del backend
- [ ] La variable `GEMINI_API_KEY` no aparece en settings ni en .env.example

---

### Orden de ejecución recomendado

```
T5-01 (modelo) → T5-02 (endpoints) → T5-03 (bot) → T5-04 (frontend) → T5-05 (limpieza)
```

T5-01 y T5-02 van primero porque el resto depende de que los endpoints existan.
T5-05 va al final para no romper nada mientras se desarrolla.

### Definition of Done del Sprint 5

- [ ] El bot guarda cada mensaje en Django automáticamente
- [ ] El panel admin muestra las conversaciones del bot actualizándose solas
- [ ] Se puede ver en el visor: nombre del jugador, mensajes del intercambio y la reserva creada
- [ ] La pestaña "Asistente" ya no tiene nada de Gemini
- [ ] El proyecto levanta con `docker compose up --build` sin errores
- [ ] La demo funciona: celular → WhatsApp → bot → visor en pantalla

---

## Información técnica para retomar

### Cómo levantar el proyecto

```bash
# Desde la raíz del proyecto Django
docker compose up -d

# El bot corre FUERA de Docker, en una terminal separada
cd "C:\Users\Clerc\Desktop\Analista\2do año\1er cuatrimestre\Programación 3\reserva_canchas info\bot-whatsapp"
npm start
# Escanear el QR con WhatsApp del celular que va a atender
```

### Credenciales de desarrollo

| Qué | Valor |
|---|---|
| Admin email | `admin@demo.localhost` |
| Admin password | `adminpass123` |
| Tenant URL | `http://demo.localhost:8000` |
| Frontend | `http://localhost:5173` |
| DB user | `canchas_user` |
| DB password | `dev_postgres_secure_2026` |

### Endpoints del bot (ya existentes, sin JWT)

| Método | URL | Uso |
|---|---|---|
| GET | `/api/courts/?is_active=true` | Listar canchas |
| GET | `/api/courts/{id}/availability/?date=YYYY-MM-DD` | Disponibilidad |
| POST | `/api/bookings/` | Crear reserva como invitado |
| GET | `/api/bookings/guest-lookup/?phone=X` | Buscar reservas por teléfono |
| POST | `/api/bookings/{id}/cancel-guest/` | Cancelar reserva propia |

### Endpoints nuevos a crear en Sprint 5

| Método | URL | JWT | Uso |
|---|---|---|---|
| POST | `/api/bot/log/` | No | Bot guarda mensaje |
| GET | `/api/bot/conversations/` | Sí | Admin ve conversaciones |

### Archivos clave del bot

| Archivo | Qué hace |
|---|---|
| `src/main.ts` | Punto de entrada, inicia WhatsApp |
| `src/services/reservationService.ts` | Lógica principal: recibe mensaje, llama a Ollama, responde |
| `src/services/djangoApiService.ts` | Cliente HTTP hacia Django (agregar `logMessage()` aquí) |
| `src/config.ts` | Variables de entorno del bot |
| `src/ia/ollama.ts` | Cliente hacia Ollama (phi3:mini) |

### Notas importantes

- El bot resuelve el tenant Django enviando el header `Host: demo.localhost` en cada request
- El modelo Ollama `phi3:mini` debe estar corriendo: `ollama serve` (en otra terminal)
- Para la demo ambos procesos (Docker + bot Node.js) deben estar activos en la misma máquina
- Los logs de conversación quedan en el esquema `demo` de PostgreSQL (aislamiento multi-tenant)

---

## Sprint 6 — Mejoras visor bot WhatsApp

### Objetivo

Mejorar la experiencia del visor de conversaciones del bot con cuatro mejoras:
1. Borrar conversaciones (soft-delete desde el panel)
2. Estilo visual idéntico al dark mode real de WhatsApp
3. Mostrar número de teléfono en formato argentino legible
4. Bot recuerda el nombre del jugador entre conversaciones

### Rama activa

`feat/modificacion-bot` (misma rama del Sprint 5)

### Paleta de colores WhatsApp dark mode (real)

Estos son los colores exactos del dark mode de WhatsApp Web, extraídos de su CSS:

| Elemento | Color |
|---|---|
| Fondo de app / área de chat | `#0b141a` |
| Sidebar izquierda (lista de convs.) | `#111b21` |
| Conversación seleccionada en lista | `#2a3942` |
| Hover sobre conversación en lista | `#202c33` |
| Header del chat (nombre + teléfono) | `#202c33` |
| Burbuja inbound (jugador, izquierda) | `#202c33` |
| Burbuja outbound (bot, derecha) | `#005c4b` |
| Texto principal | `#e9edef` |
| Texto secundario / timestamps | `#8696a0` |
| Íconos | `#aebac1` |
| Divisor / borde | `#222e35` |
| Avatar placeholder | `#6b7c85` |

Regla de legibilidad: todo texto sobre burbujas usa `#e9edef`; los timestamps usan `#8696a0`.

---

### Tareas del Sprint 6

---

#### T6-01 — Backend: endpoint DELETE para borrar conversación

**Archivos:** `backend/apps/agent/views.py` + `backend/apps/agent/urls.py`
**Estado:** ⬜ Pendiente

**Endpoint:** `DELETE /api/bot/conversations/{phone}/`
- Permiso: `IsAuthenticated` (JWT — solo admin/operador)
- El `phone` en la URL viene URL-encoded (ej: `5491112345678%40c.us`)
- Acción: `BotConversationLog.objects.filter(phone=phone, is_active=True).update(is_active=False)`
- Respuesta: `204 No Content`
- Si no existe ningún log activo para ese phone: `404 Not Found`

**Criterios de aceptación:**
- [ ] `DELETE /api/bot/conversations/PHONE/` sin JWT → 401
- [ ] Con JWT y phone válido → 204 y los logs quedan `is_active=False`
- [ ] `GET /api/bot/conversations/` después del borrado NO muestra esa conversación
- [ ] Con phone inexistente → 404

---

#### T6-02 — Frontend: WhatsApp dark mode real

**Archivos a modificar:**
- `frontend/src/features/agent/BotViewerPage.tsx`
- `frontend/src/features/agent/components/ConversationList.tsx`
- `frontend/src/features/agent/components/ConversationDetail.tsx`
- `frontend/src/features/agent/components/BookingSummary.tsx`

**Qué cambiar:**
- Reemplazar todos los colores Tailwind estándar por colores arbitrarios de la paleta de arriba
- Usar `bg-[#0b141a]`, `bg-[#111b21]`, `bg-[#005c4b]`, etc.
- Burbujas inbound: `bg-[#202c33]` con texto `text-[#e9edef]`
- Burbujas outbound: `bg-[#005c4b]` con texto `text-[#e9edef]`
- Timestamps: `text-[#8696a0]` en todas las burbujas
- Header del panel derecho: `bg-[#202c33]`
- Lista izquierda: `bg-[#111b21]`; fila seleccionada: `bg-[#2a3942]`; hover: `hover:bg-[#202c33]`
- Divisores: `border-[#222e35]`
- Texto de nombre en lista: `text-[#e9edef]`; preview de mensaje: `text-[#8696a0]`
- Avatar circular de placeholder: `bg-[#6b7c85]` con inicial en blanco

**Agregar también el botón de borrar (T6-03 frontend):**
- Ícono de papelera (`Trash2` de Lucide) visible al hacer hover sobre una fila de la lista
- Color: `text-[#8696a0]` en reposo, `text-red-400` en hover
- Al hacer click: llama al endpoint DELETE, refresca la lista, deselecciona si era la conversación activa

**Criterios de aceptación:**
- [ ] La página entera usa la paleta de dark mode de WhatsApp
- [ ] Las burbujas son visualmente distinguibles y legibles
- [ ] El botón papelera aparece en hover sobre cada conversación de la lista
- [ ] El diseño es responsive (mobile funciona)

---

#### T6-03 — Frontend: helper de formateo de teléfono argentino

**Archivo a crear:** `frontend/src/lib/formatPhone.ts`

```typescript
// Convierte "5491112345678@c.us" → "+54 9 11 1234-5678"
// Convierte "5493515551234@c.us" → "+54 9 351 555-1234" (córdoba, 10 dígitos locales)
// Fallback: si no coincide el patrón, devuelve el número limpio sin "@c.us"
export function formatPhone(raw: string): string
```

**Lógica:**
1. Quitar sufijo `@c.us` y el `@g.us` (grupos, por si aparece)
2. Si empieza con `549` + 10 dígitos: es Argentina móvil
   - Para Buenos Aires (549 + 11 + 8 dígitos): `+54 9 11 XXXX-XXXX`
   - Para el resto (549 + código 3 dígitos + 7 dígitos): `+54 9 XXX XXX-XXXX`
3. Fallback: agregar `+` al inicio y devolver

**Dónde usarlo:**
- `ConversationList.tsx`: en el preview de la fila (cuando no hay `player_name`)
- `ConversationDetail.tsx`: en el header del chat (debajo del nombre)

**Criterios de aceptación:**
- [ ] `"5491112345678@c.us"` → `"+54 9 11 1234-5678"`
- [ ] `"5493515551234@c.us"` → `"+54 9 351 555-1234"`
- [ ] Un número sin `@c.us` devuelve el número con `+` al inicio
- [ ] Se usa en lista y en header del chat

---

#### T6-04 — Bot: recordar nombre del jugador entre conversaciones

**Archivos del bot a modificar:**
- `src/services/djangoApiService.ts` — agregar `getPlayerName(phone)`
- `src/services/reservationService.ts` — usar el nombre guardado al iniciar conversación

**Directorio bot:** `C:\Users\Clerc\Desktop\Analista\2do año\1er cuatrimestre\Programación 3\reserva_canchas info\bot-whatsapp`

**Endpoint disponible (ya existe, sin JWT):**
`GET /api/bot/conversations/?phone=XXXX` → devuelve conversaciones con `player_name`

**Lógica a implementar:**

En `djangoApiService.ts`, agregar:
```typescript
export async function getPlayerName(phone: string): Promise<string | null>
// Llama GET /api/bot/conversations/?phone=PHONE
// Si hay resultado y player_name no vacío → devuelve el nombre
// Si no hay resultado o Django no responde → devuelve null (silencioso)
```

En `reservationService.ts`, al iniciar una conversación nueva (cuando el estado es `idle` o `greeting`):
1. Llamar a `getPlayerName(phone)`
2. Si devuelve un nombre: pre-cargar en el estado de la conversación y saltar la pregunta del nombre
3. Si devuelve null: flujo normal (preguntar el nombre)

El saludo cuando ya se conoce el nombre debería ser algo como:
`"¡Hola [nombre]! ¿En qué te puedo ayudar hoy?"`
en lugar del saludo genérico.

**Criterios de aceptación:**
- [ ] Si el jugador ya reservó antes, el bot lo saluda por nombre desde el primer mensaje
- [ ] Si es la primera vez, el bot pide el nombre como siempre
- [ ] Si Django no responde, el bot NO se rompe y sigue el flujo normal

---

### Orden de ejecución recomendado

```
T6-01 (backend borrar) → T6-02 (dark mode + botón papelera) → T6-03 (helper teléfono) → T6-04 (bot nombre)
```

T6-01 primero porque T6-02 incluye el botón que llama al endpoint.
T6-03 es independiente, se puede hacer junto con T6-02.
T6-04 es completamente independiente (solo toca el bot Node.js).

### Definition of Done del Sprint 6

- [ ] El visor usa la paleta visual exacta del dark mode de WhatsApp y es legible
- [ ] Hay botón de papelera por conversación; al borrar desaparece de la lista
- [ ] Los teléfonos se muestran en formato argentino (`+54 9 11 XXXX-XXXX`)
- [ ] El bot saluda por nombre a los jugadores que ya reservaron antes
- [ ] Nada se rompe si Django no está disponible (bot) o la API falla (frontend)

---

## Sprint 7 — Fix teléfonos reales en el visor del bot

### Objetivo

Corregir dos bugs en el bot Node.js que impiden que el visor muestre teléfonos reales y nombres de jugadores.

### Diagnóstico (2026-06-14)

La DB tiene 58 registros reales con este patrón:

```
phone='211252378873868@lid'  |  player_name=''
```

- **`@lid`** es el protocolo multi-dispositivo de WhatsApp. `msg.from` devuelve un ID interno en lugar del teléfono real.
- **`player_name` vacío** porque `main.ts` nunca pasa el nombre a `logMessage`.

### Archivos a modificar (todos en el bot Node.js)

```
bot-whatsapp/src/whatsapp/client.ts         ← T7-01: resolver @lid
bot-whatsapp/src/main.ts                    ← T7-01 + T7-02
bot-whatsapp/src/services/reservationService.ts  ← T7-02: retornar playerName
```

**Directorio bot:** `C:\Users\Clerc\Desktop\Analista\2do año\1er cuatrimestre\Programación 3\reserva_canchas info\bot-whatsapp`

### Tareas

---

#### T7-01 — Resolver `@lid` al teléfono real del contacto

**Archivos:** `src/whatsapp/client.ts` + `src/main.ts`

**Problema:** `client.ts` pasa `msg.from` directo al handler. Cuando el contacto usa protocolo multi-dispositivo, `msg.from` es `211252378873868@lid` en lugar de `5491112345678@c.us`.

**Solución:** En `client.ts`, cuando `msg.from` termina en `@lid`, llamar `msg.getContact()` y usar `contact.id._serialized` como teléfono resuelto. Pasarlo como segundo argumento al handler.

```typescript
// client.ts — handler de mensaje
client.on("message", async (msg: Message) => {
    if (msg.from.endsWith("@g.us") || msg.fromMe) return;

    let resolvedPhone = msg.from;
    if (msg.from.endsWith("@lid")) {
        try {
            const contact = await msg.getContact();
            if (contact.id._serialized && !contact.id._serialized.endsWith("@lid")) {
                resolvedPhone = contact.id._serialized;
            }
        } catch {
            // fallo silencioso: usar msg.from como fallback
        }
    }

    if (messageHandler) {
        try {
            await messageHandler(msg, resolvedPhone);
        } catch (err) { ... }
    }
});
```

```typescript
// Firma actualizada de setMessageHandler:
// Antes: (msg: Message) => Promise<void>
// Después: (msg: Message, resolvedPhone: string) => Promise<void>
```

```typescript
// main.ts — usar resolvedPhone en lugar de msg.from
setMessageHandler(async (msg, resolvedPhone) => {
    await logMessage({ phone: resolvedPhone, direction: "inbound", message: msg.body });
    const { reply, bookingId, playerName } = await handleMessage(resolvedPhone, msg.body);
    await msg.reply(reply);
    await logMessage({ phone: resolvedPhone, direction: "outbound", message: reply, booking_id: bookingId ?? null });
});
```

**Criterios de aceptación:**
- [ ] Contactos con `@lid` → phone guardado en Django es `NNNNN@c.us`
- [ ] Si `getContact()` falla → fallback a `msg.from` sin romper el bot
- [ ] Contactos que ya usan `@c.us` → sin cambio (no regresión)

---

#### T7-02 — Retornar y guardar `player_name`

**Archivos:** `src/services/reservationService.ts` + `src/main.ts`

**Problema:** `handleMessage` retorna `{ reply, bookingId }` pero no el nombre del jugador. `main.ts` nunca pasa `player_name` a `logMessage`.

**Solución en `reservationService.ts`:**

```typescript
// Agregar playerName al tipo de retorno
export interface HandleMessageResult {
    reply: string;
    bookingId?: number;
    playerName?: string;   // ← nuevo
}

// Al final de handleMessage, antes del return:
return { reply, bookingId, playerName: state.guestName ?? undefined };
```

**Solución en `main.ts`:**

```typescript
const { reply, bookingId, playerName } = await handleMessage(resolvedPhone, msg.body);

// Pasar player_name en ambos logMessage:
await logMessage({ phone: resolvedPhone, direction: "inbound",  message: msg.body, player_name: playerName });
await logMessage({ phone: resolvedPhone, direction: "outbound", message: reply, booking_id: bookingId ?? null, player_name: playerName });
```

**Criterios de aceptación:**
- [ ] Después de que el jugador da su nombre, los logs siguientes tienen `player_name` relleno
- [ ] El visor muestra el nombre en la lista y en el header del chat
- [ ] Los logs anteriores a la colección del nombre quedan con `player_name=''` (esperado)

---

### Orden de ejecución

```
T7-01 (client.ts) → T7-02 (reservationService + main.ts) → probar en vivo
```

T7-01 primero: sin el teléfono correcto, T7-02 graba el nombre bajo un ID incorrecto.

### Definition of Done del Sprint 7

- [ ] El visor muestra teléfonos en formato `+54 9 11 XXXX-XXXX` para contactos argentinos
- [ ] El visor muestra el nombre del jugador cuando completó el flujo de reserva
- [ ] El bot no se rompe si `getContact()` lanza error (fallo silencioso)
- [ ] Sin regresión en flujo de reserva ni cancelación
- [ ] Los 58 registros históricos con `@lid` permanecen en la DB sin problema

---

## Sprint 8 — Rebranding CanchaYA → CANCHERO!

### Objetivo

Cambiar el nombre comercial del producto de `CanchaYA` a `CANCHERO!` en todos los archivos
del proyecto: documentación, backend, frontend y configuración. Sin cambios de arquitectura,
modelos, migraciones ni lógica de negocio.

### ADR

Ver `docs/adr/ADR-012-rebranding-canchero.md` para la decisión y el razonamiento.

### Rama

`feat/rebranding-canchero` (rama nueva desde `master`)

### Regla de nombres

| Contexto | Nombre a usar |
|---|---|
| UI visible (navbar, login, título, emails) | `CANCHERO!` |
| Identificadores técnicos (package, localStorage, email, alias) | `canchero` |
| Título Swagger | `CANCHERO! API` |

El `!` **no se usa** en identificadores técnicos.

---

### Tareas

---

#### T8-01 — Documentación

**Archivos:**
- `docs/PROJECT_CONTEXT.md`
- `docs/ERS.md`
- `PROGRESS.md` (ya actualizado en este commit)
- `README.md`
- `docs/ARCHITECTURE.md` — agregar ADR-012 a la lista §10

**Cambios:**
- Reemplazar todas las ocurrencias de `CanchaYA` por `CANCHERO!`
- En `README.md`: el link al repo del bot (`github.com/cn-10/CanchaYa_bot`) se deja como
  **pendiente** hasta que se renombre el repositorio remoto de GitHub

**Criterios de aceptación:**
- [ ] `docs/PROJECT_CONTEXT.md` no contiene `CanchaYA`
- [ ] `docs/ERS.md` no contiene `CanchaYA`
- [ ] `docs/ARCHITECTURE.md` lista ADR-012 en §10
- [ ] `README.md` tiene una nota indicando que el repo del bot está pendiente de renombrar

---

#### T8-02 — Backend

**Archivos:**
- `backend/config/settings.py`
- `backend/apps/bookings/notifications.py`
- `backend/apps/agent/management/commands/seed_bot_demo.py`
- `.env.example`

**Cambios exactos:**

`settings.py`:
```python
# Antes:
"TITLE": "CanchaYA API"
# Después:
"TITLE": "CANCHERO! API"

# Antes:
"DEFAULT_FROM_EMAIL", "CanchaYA <noreply@canchaYA.com>"
# Después:
"DEFAULT_FROM_EMAIL", "CANCHERO! <noreply@canchero.com>"
```

`notifications.py` (3 ocurrencias):
```python
# Antes:
f"El equipo de CanchaYA"
# Después:
f"El equipo de CANCHERO!"
```

`seed_bot_demo.py` (2 mensajes con el nombre):
```python
# "soy el bot de *CanchaYA*" → "soy el bot de *CANCHERO!*"
# Alias "CANCHAYA.DEMO" → "CANCHERO.DEMO"
```

`.env.example`:
```bash
# canchaYA.com → canchero.com  (dominio de ejemplo)
# CanchaYA <reservas@canchaYA.com> → CANCHERO! <reservas@canchero.com>
```

**Criterios de aceptación:**
- [ ] `settings.py`: el Swagger sirve con título `CANCHERO! API`
- [ ] `notifications.py`: la firma de emails dice `El equipo de CANCHERO!`
- [ ] `seed_bot_demo.py`: los mensajes de demo usan el nombre nuevo
- [ ] `.env.example`: no quedan referencias a `canchaYA.com`

---

#### T8-03 — Frontend

**Archivos:**
- `frontend/index.html`
- `frontend/src/components/NavBar.tsx`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/lib/axios.ts`
- `frontend/package.json`

**Cambios exactos:**

`index.html`:
```html
<!-- Antes: -->
<title>CanchaYA</title>
<!-- Después: -->
<title>CANCHERO!</title>
```

`NavBar.tsx` (2 ocurrencias del texto de marca):
```tsx
// "CanchaYA" → "CANCHERO!"
```

`LoginPage.tsx`:
```tsx
// "CanchaYA" → "CANCHERO!"
```

`axios.ts`:
```typescript
// Antes:
export const TOKEN_KEY    = 'canchaYA_access'
export const REFRESH_KEY  = 'canchaYA_refresh'
// Después:
export const TOKEN_KEY    = 'canchero_access'
export const REFRESH_KEY  = 'canchero_refresh'
```

`package.json`:
```json
// Antes: "name": "canchaYA-frontend"
// Después: "name": "canchero-frontend"
```

**Post-cambio obligatorio:**
```bash
cd frontend && npm install
# Regenera package-lock.json con el nombre nuevo
```

**Nota sobre localStorage:** El cambio de keys desloguea a los usuarios actuales en dev.
Acción requerida una sola vez: limpiar el localStorage del browser.

**Criterios de aceptación:**
- [ ] La pestaña del browser muestra `CANCHERO!`
- [ ] El navbar y la pantalla de login muestran `CANCHERO!`
- [ ] `package.json` tiene `"name": "canchero-frontend"`
- [ ] `npm install` corre sin errores y `package-lock.json` queda actualizado
- [ ] El login funciona correctamente (las nuevas keys de localStorage funcionan)

---

### Orden de ejecución

```
T8-01 (docs) → T8-02 (backend) → T8-03 (frontend) → npm install → smoke test
```

T8-01 y T8-02 son independientes entre sí (se pueden hacer en paralelo).
T8-03 va al final por el `npm install` posterior.

### Definition of Done del Sprint 8

- [ ] Ningún archivo del proyecto contiene `CanchaYA` (excepto la nota en `README.md` sobre el repo del bot)
- [ ] La UI muestra `CANCHERO!` en todos los puntos de contacto (tab, navbar, login)
- [ ] El Swagger sirve con título `CANCHERO! API`
- [ ] Los emails de notificación firman como `El equipo de CANCHERO!`
- [ ] `npm install` corre sin errores en `frontend/`
- [ ] El proyecto levanta con `docker compose up` sin errores
- [ ] El login funciona con las nuevas keys de localStorage
- [ ] ADR-012 creado y referenciado en `ARCHITECTURE.md` §10

### Deuda técnica post-Sprint 8

- Renombrar el repositorio del bot en GitHub (`cn-10/CanchaYa_bot` → `cn-10/canchero-bot`)
  y actualizar el link en `README.md`
- Al definir el dominio de producción del Cliente Cero, evaluar `canchero.com` / `canchero.com.ar`
