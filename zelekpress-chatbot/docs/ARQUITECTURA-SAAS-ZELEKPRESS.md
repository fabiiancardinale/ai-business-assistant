# Arquitectura — Plataforma SaaS de Chatbots de Zelekpress

Documento de arquitectura (paso previo a la implementación, según el punto
58 del brief). Define **cómo** se construye la plataforma antes de escribir
código. Aprovecha lo que ya existe hoy en `api.zelekpress.com` (FastAPI +
widget + Groq) y lo evoluciona a un SaaS multi-tenant real.

> Estado actual (v1, en producción): FastAPI + SQLite, tabla `companies`
> con `api_key`, panel `/admin` (HTTP Basic), portal `/portal`, widget
> `widget.js`, IA vía Groq (`ai_service.py`). Esta arquitectura (v2)
> reusa esos aprendizajes: el `ai_service` se convierte en un *AIProvider*,
> el widget se reescribe con Shadow DOM, y SQLite pasa a PostgreSQL.

---

## 1. Arquitectura general

Flujo completo: **Frontend ↔ Backend ↔ PostgreSQL ↔ Redis ↔ IA ↔ Widget**.

```
                 ┌───────────────────────────────────────────────┐
                 │                  NAVEGADOR                     │
                 │                                                │
   Sitio del     │   ┌─────────────┐        ┌──────────────────┐ │
   cliente ──────┼──▶│ widget.js   │        │ app.zelekpress   │ │
   (WordPress,   │   │ (Shadow DOM)│        │  React SPA       │ │
   Shopify, PHP) │   └──────┬──────┘        │  /admin /dashboard│ │
                 │          │               └────────┬─────────┘ │
                 └──────────┼────────────────────────┼───────────┘
                            │ REST (config pública)   │ REST + WS (JWT)
                            │ + WebSocket (chat)       │
                 ┌──────────▼─────────────────────────▼───────────┐
                 │              BACKEND — FastAPI                  │
                 │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
                 │  │  REST    │ │ WebSocket│ │  Workers (RQ/    │ │
                 │  │  API     │ │  Gateway │ │  Celery): RAG,   │ │
                 │  │          │ │          │ │  webhooks, jobs  │ │
                 │  └────┬─────┘ └────┬─────┘ └────────┬────────┘ │
                 │       │            │                │          │
                 │  ┌────▼────────────▼────────────────▼────────┐ │
                 │  │  Services  ·  AIProvider  ·  BillingProvider│ │
                 │  └────┬───────────────┬───────────────┬──────┘ │
                 └───────┼───────────────┼───────────────┼────────┘
                         │               │               │
                 ┌───────▼──────┐ ┌──────▼──────┐ ┌───────▼────────┐
                 │ PostgreSQL   │ │   Redis     │ │  Proveedores   │
                 │ (datos)      │ │ cache/cola/ │ │  IA (Groq,     │
                 │ + pgvector   │ │ ws-state/   │ │  OpenAI, etc.) │
                 │ (embeddings) │ │ rate-limit  │ │                │
                 └──────────────┘ └─────────────┘ └────────────────┘
```

Principios: cada funcionalidad se implementa **vertical** (UI → API →
validación → multi-tenant → DB → respuesta), nunca UI falsa primero. Todo
permiso se valida en backend. Nada de secretos en el navegador.

---

## 2. Diagrama de componentes

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| **Widget** | TS + Shadow DOM, build a JS único | Se instala en sitios externos. Solo lee config pública y chatea. |
| **Frontend SPA** | React + TypeScript + Tailwind | Dos apps con layouts/permisos separados: `/admin` (Zelekpress) y `/dashboard` (cliente). |
| **API REST** | FastAPI | CRUD, auth, multi-tenant, billing, KB, analytics. OpenAPI/Swagger. |
| **WebSocket Gateway** | FastAPI WS + Redis pub/sub | Chat en vivo, respuestas IA en streaming, modo humano, notificaciones. |
| **Workers** | RQ o Celery + Redis | Procesar KB (embeddings/RAG), enviar webhooks con reintentos, jobs pesados. |
| **PostgreSQL** | Postgres 15 + extensión `pgvector` | Datos relacionales + almacenamiento de embeddings. |
| **Redis** | Redis 7 | Cache, sesiones temporales, rate limiting, estado WS, colas. |
| **AIProvider** | Capa Python desacoplada | Adaptadores Groq/OpenAI/Anthropic/Gemini/Ollama. |
| **BillingProvider** | Capa Python desacoplada | Adaptadores Stripe/MercadoPago (a futuro). |

---

## 3. Estructura de carpetas (monorepo)

```
zelekpress-chatbot/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/             # config, seguridad, db, deps, errores
│   │   ├── auth/             # registro, login, JWT, RBAC
│   │   ├── companies/        # empresas (tenants) + members
│   │   ├── users/
│   │   ├── chatbots/         # chatbots + settings + themes
│   │   ├── knowledge/        # fuentes, documentos, RAG
│   │   ├── conversations/    # conversaciones + mensajes + agentes
│   │   ├── leads/
│   │   ├── analytics/
│   │   ├── billing/          # planes, suscripciones, usage, límites
│   │   ├── webhooks/
│   │   ├── integrations/     # adapters (WhatsApp, Zapier, n8n…)
│   │   ├── ai/               # AIProvider + adapters
│   │   ├── realtime/         # WebSocket gateway
│   │   └── notifications/
│   ├── migrations/           # Alembic
│   ├── tests/
│   └── requirements.txt
│
├── frontend/                 # React + TS + Tailwind
│   └── src/
│       ├── admin/            # Super Admin de Zelekpress
│       ├── dashboard/        # panel del cliente
│       ├── auth/
│       ├── components/  layouts/  services/  hooks/  stores/  types/  utils/
│
├── widget/                   # widget JS independiente (Shadow DOM)
│   └── src/  api/ components/ config/ session/ websocket/ theme/ storage/ main.ts
│
├── docs/                     # este documento, OpenAPI, diagramas
├── docker/                   # Dockerfiles
├── docker-compose.yml        # frontend, backend, postgres, redis, worker
└── README.md
```

Regla: nada de archivos gigantes. Separar routes / services / models /
schemas / repositories / middleware / providers / utils.

---

## 4. Modelo de datos (PostgreSQL)

Entidades y columnas clave (todas con `id`, `created_at`, `updated_at`;
soft-delete `deleted_at` donde aplique). El aislamiento multi-tenant se
apoya en `company_id` en toda entidad de negocio.

```
users
  id, email (unique), password_hash, name, is_platform_admin (bool),
  email_verified_at, last_login_at

companies (tenant)
  id, name, slug (unique), logo, email, phone, website,
  status (active|suspended), plan_id (fk), settings (jsonb),
  created_by (fk users)

company_members            # relación usuario↔empresa con rol
  id, company_id (fk), user_id (fk), role (owner|admin|agent|viewer)
  UNIQUE(company_id, user_id)

plans
  id, name, slug, price, currency, period (monthly|yearly|one_time),
  limits (jsonb: chatbots, conversations, messages, users, ai_tokens,
          storage_mb, knowledge_sources), features (jsonb), active

subscriptions
  id, company_id (fk), plan_id (fk), status (active|past_due|canceled),
  provider (stripe|mercadopago|manual), external_ref, current_period_end

chatbots
  id, company_id (fk), name_internal, name_public, avatar, logo,
  description, status (active|paused), language, allowed_domains (jsonb),
  ai_config_id (fk), theme_id (fk)

chatbot_settings
  id, chatbot_id (fk), system_prompt, personality, greeting_message,
  unknown_message, farewell_message, temperature, max_tokens, model,
  behavior (jsonb: auto_open, delay, schedule, sound, max_messages, ...)

chatbot_themes
  id, company_id (fk), name, base_theme, tokens (jsonb: colores, layout,
  launcher, header, mensajes, tipografía), is_shared

knowledge_sources
  id, chatbot_id (fk), company_id (fk), type (text|faq|pdf|txt|csv|url),
  name, status (pending|processing|ready|error), size, meta (jsonb)

knowledge_documents        # chunks + embeddings
  id, source_id (fk), chatbot_id (fk), company_id (fk),
  content (text), embedding vector(1536), tokens

conversations
  id, chatbot_id (fk), company_id (fk), visitor_id, status
  (open|pending|closed|human|ai), url, page, browser, device, country,
  assigned_agent_id (fk users, null), human_requested (bool)

messages
  id, conversation_id (fk), company_id (fk), role (visitor|bot|agent|system),
  content, tokens, meta (jsonb)

leads
  id, company_id (fk), chatbot_id (fk), conversation_id (fk), name, email,
  phone, whatsapp, company_name, message, source

api_keys
  id, company_id (fk), name, key_hash, prefix, last_used_at, revoked_at

webhooks
  id, company_id (fk), url, event, secret, active

usage                      # consumo agregado por período
  id, company_id (fk), period (YYYY-MM), conversations, messages,
  ai_tokens, ai_requests, leads, storage_mb, chatbots

notifications
  id, company_id (fk), user_id (fk, null), type, payload (jsonb), read_at

audit_logs
  id, company_id (fk, null), user_id (fk, null), action, entity, entity_id,
  details (jsonb), ip_address
```

Restricciones: FKs con `ON DELETE` coherente, índices en todos los
`company_id` y en claves de búsqueda (`conversations.status`,
`messages.conversation_id`, `knowledge_documents` índice vectorial IVFFlat),
`UNIQUE` en `users.email`, `companies.slug`, `plans.slug`.

---

## 5. Relaciones (resumen)

```
users ──< company_members >── companies ──< chatbots ──< chatbot_settings
                                   │              │
                                   │              ├──< knowledge_sources ──< knowledge_documents
                                   │              ├──< conversations ──< messages
                                   │              └──< chatbot_themes
                                   ├──< subscriptions >── plans
                                   ├──< leads   ├──< api_keys   ├──< webhooks
                                   ├──< usage   └──< audit_logs
```

Un `user` puede pertenecer a varias `companies` (vía `company_members`) con
un rol distinto en cada una. Todo lo demás cuelga de `company_id`.

---

## 6. Estrategia multi-tenant

Modelo elegido: **base de datos compartida, esquema compartido, aislamiento
por `company_id`** (row-level). Es el que mejor escala para muchos clientes
chicos como el Chatbot Básico de $9.990.

Cómo se garantiza el aislamiento (siempre en backend):

1. El JWT del usuario incluye `user_id`, y en cada request se resuelve el
   `company_id` activo (desde la URL/tenant header) y se valida contra
   `company_members`. Si el usuario no es miembro de esa empresa → 403.
2. Todo query de negocio pasa por un **repositorio con scope de tenant**:
   una capa que inyecta `WHERE company_id = :current_company` de forma
   obligatoria. No se hacen queries "crudos" en las rutas.
3. Defensa en profundidad: además del scope en el repo, se puede activar
   **Postgres Row-Level Security (RLS)** con `SET app.current_company` por
   conexión, de modo que aunque un query se filtre, la DB niega filas de
   otro tenant.
4. El `company_id`, el `role` y el `chatbot_id` **nunca** se confían desde
   el frontend ni desde el widget: se derivan del token/API key en backend.
5. El Super Admin de Zelekpress (`users.is_platform_admin = true`) es el
   único que puede cruzar tenants, y solo por rutas `/admin/*` protegidas.

---

## 7. Autenticación

- **Registro / login / logout** con email + contraseña (`password_hash` con
  bcrypt/argon2). Verificación de email por token. Recuperación y cambio de
  contraseña.
- **JWT** de acceso corto (15 min) + **refresh token** rotatorio guardado
  en cookie `HttpOnly` `Secure` `SameSite`. El access token lleva `user_id`
  y `is_platform_admin`; el `company_id`/`role` se resuelven por request.
- **Rate limiting** en login y endpoints sensibles (Redis).
- **API Keys** (para la API pública y el widget-config) se validan aparte,
  con hash almacenado y prefijo visible.
- Todos los endpoints protegidos por dependencia `get_current_user` +
  `require_company_role(...)`.

---

## 8. Roles y permisos (RBAC real)

Roles por empresa: `OWNER`, `ADMIN`, `AGENT`, `VIEWER`. Además el flag global
`is_platform_admin` (Super Admin de Zelekpress).

| Capacidad | OWNER | ADMIN | AGENT | VIEWER |
|---|:--:|:--:|:--:|:--:|
| Empresa / billing | ✓ | — | — | — |
| Usuarios e invitaciones | ✓ | ✓ | — | — |
| Chatbots (CRUD, config, temas) | ✓ | ✓ | — | ver |
| Knowledge base | ✓ | ✓ | — | ver |
| Conversaciones (responder, cerrar) | ✓ | ✓ | ✓ | ver |
| Asignarse conversaciones | ✓ | ✓ | ✓ | — |
| Leads | ✓ | ✓ | ver | ver |
| Analytics | ✓ | ✓ | ver | ver |
| API keys / webhooks / integraciones | ✓ | ✓ | — | — |

Implementación: decorador/dependencia `require(permission)` que consulta el
rol del usuario en la empresa activa. Los permisos se validan en backend
aunque el frontend ya oculte botones (nunca solo ocultar en UI).

---

## 9. Endpoints API (REST, versionados `/api/v1`)

```
POST   /auth/register            POST /auth/login          POST /auth/logout
POST   /auth/refresh             POST /auth/verify-email   POST /auth/forgot
POST   /auth/reset

# scope empresa activa (multi-tenant)
GET/POST/PATCH/DELETE  /companies            /companies/{id}
GET/POST/PATCH/DELETE  /companies/{id}/members
GET/POST/PATCH/DELETE  /chatbots             /chatbots/{id}
GET/PUT                /chatbots/{id}/settings
GET/PUT                /chatbots/{id}/ai
GET/POST/DELETE        /chatbots/{id}/themes
GET/POST/DELETE        /chatbots/{id}/knowledge          # fuentes
POST                   /chatbots/{id}/knowledge/{sid}/reprocess
GET                    /conversations        /conversations/{id}
POST                   /conversations/{id}/reply | close | reopen | assign | note
GET                    /messages?conversation_id=
GET                    /leads
GET                    /analytics/*          # overview, timeseries, unanswered
GET/POST/DELETE        /api-keys
GET/POST/PATCH/DELETE  /webhooks
GET                    /usage                # current_usage, plan_limit, remaining

# público (para el widget) — sin secretos
GET    /public/chatbots/{id}/config          # config visual + flags, valida dominio
POST   /public/chatbots/{id}/session         # crea sesión de visitante
WS     /public/ws/{session_token}            # chat en vivo

# super admin de Zelekpress (is_platform_admin)
GET    /admin/overview
GET/POST/PATCH/DELETE  /admin/companies      /admin/companies/{id}
POST   /admin/companies/{id}/suspend | activate
GET/POST/PATCH/DELETE  /admin/plans
GET    /admin/usage  /admin/logs  /admin/settings
```

Documentado con **OpenAPI/Swagger** (FastAPI lo genera nativo en `/docs`).

---

## 10. Arquitectura del widget

- Proyecto TS independiente; el build produce un único `widget.js` servido
  desde `app.zelekpress.com/widget.js`.
- Instalación en el sitio del cliente:
  ```html
  <script src="https://app.zelekpress.com/widget.js" data-chatbot-id="CHATBOT_ID"></script>
  ```
- **Aislamiento con Shadow DOM**: todo el CSS/JS/DOM del widget vive dentro
  de un `shadowRoot`, así no choca con Bootstrap, Tailwind, jQuery,
  WordPress, etc. del sitio anfitrión.
- Ciclo de vida del widget: identificar chatbot → pedir
  `/public/chatbots/{id}/config` → validar dominio autorizado → cargar tema
  → crear sesión → construir UI → abrir WebSocket → chatear.
- **Sin secretos**: el widget solo usa el `chatbot_id` público y el token de
  sesión temporal. Las API keys privadas jamás llegan al navegador.

---

## 11. Comunicación Widget ↔ Backend

```
Widget                         Backend
  │  GET /public/chatbots/{id}/config      (Origin validado vs allowed_domains)
  │─────────────────────────────────────▶ │  devuelve config pública + tema
  │  POST /public/chatbots/{id}/session    │
  │─────────────────────────────────────▶ │  crea conversation, devuelve session_token
  │  WS  /public/ws/{session_token}        │
  │═════════════════════════════════════▶ │  abre canal
  │  → { type:"user_message", text }       │
  │═════════════════════════════════════▶ │  guarda msg, dispara IA
  │  ◀ { type:"bot_token", delta }  (stream)│  respuesta IA en streaming (vía Redis pub/sub)
  │  ◀ { type:"bot_done" }                 │
  │  ◀ { type:"human_joined", agent }      │  si un agente toma la conversación
```

Reconexión automática del WS con backoff. El estado de las conexiones se
coordina en Redis (para escalar a múltiples procesos del backend).

---

## 12. Arquitectura de IA (AIProvider)

Capa desacoplada: **`AIService → AIProvider → ProviderAdapter`**. El chatbot
nunca habla directo con un proveedor.

```python
class AIProvider(Protocol):
    def complete(self, messages, *, model, temperature, max_tokens) -> str: ...
    def stream(self, messages, *, model, temperature, max_tokens) -> Iterator[str]: ...

# adapters: GroqAdapter (ya existe hoy), OpenAIAdapter, AnthropicAdapter,
# GeminiAdapter, DeepSeekAdapter, OllamaAdapter
```

- La selección de proveedor/modelo es configuración (por chatbot y/o global
  del Super Admin), no está hardcodeada.
- El `ai_service.py` actual (Groq) se refactoriza como `GroqAdapter` —
  cero reescritura de lógica, solo se mueve detrás de la interfaz.
- El **contexto** se arma con: system prompt + personalidad + reglas + los
  chunks relevantes del RAG + historial de la conversación.
- `usage tracking` registra tokens/requests por empresa en cada llamada.

---

## 13. Sistema de Knowledge Base (RAG)

- Fuentes: texto, FAQ, PDF, TXT, CSV, URLs, info de negocio.
- Pipeline (en **workers**, asíncrono; el estado de la fuente pasa
  `pending → processing → ready|error`):
  1. Extraer texto (parser por tipo de archivo/URL).
  2. Chunking (fragmentos con solapamiento).
  3. Generar embeddings (vía un `EmbeddingProvider`, también desacoplado).
  4. Guardar en `knowledge_documents.embedding` (**pgvector**).
- En cada consulta del chatbot: embeddings de la pregunta → búsqueda de
  similitud (kNN con pgvector) filtrada por `chatbot_id`/`company_id` → los
  top-k chunks se inyectan en el prompt.
- La implementación de embeddings y vector store está **desacoplada**: se
  arranca con pgvector (simple, sin infra extra) y se puede cambiar a un
  vector DB dedicado sin tocar el resto.

---

## 14. Sistema de WebSockets

- Gateway WS en FastAPI. Autenticación: token de sesión (widget) o JWT
  (agentes en el dashboard).
- **Redis pub/sub** como bus: cada mensaje/estado se publica en un canal
  `conv:{id}` y todos los procesos suscritos lo reenvían a sus conexiones.
  Esto permite escalar horizontalmente el backend.
- Eventos: `user_message`, `bot_token`/`bot_done` (streaming IA),
  `agent_message`, `conversation_status`, `human_requested`,
  `human_joined`, `notification`.
- **Modo humano**: al pedir una persona, se marca `human_requested`, la IA
  se pausa, se notifica a los agentes; un agente puede *tomar*, responder,
  cerrar o *devolver a IA*. Queda registrado quién tomó el control.

---

## 15. Planes y límites

- Los planes viven en la tabla `plans` (no hardcodeados). El Super Admin
  crea/edita planes y sus `limits`/`features` desde `/admin/plans`.
- **Plan inicial real**: *Chatbot Básico — $9.990 CLP* sembrado en `plans`
  con límites configurables (1 chatbot, X conversaciones, KB, widget,
  analytics básicos). PRO/BUSINESS se agregan después sin tocar código.
- Enforcement centralizado: un servicio `LimitGuard` compara
  `current_usage` (tabla `usage`) contra `plan_limit` antes de permitir una
  acción (crear chatbot, iniciar conversación, etc.). Al alcanzar el límite:
  avisar claramente, registrar el evento y bloquear la función — nunca
  fallar en silencio.

---

## 16. Usage tracking

- Servicio central `UsageTracker` que incrementa contadores por empresa y
  período (`usage.period = YYYY-MM`): conversaciones, mensajes, tokens IA,
  requests IA, leads, usuarios, storage, chatbots.
- Escrituras rápidas en Redis (contadores) y consolidación periódica a
  Postgres (job del worker), para no golpear la DB en cada mensaje.
- Expone: `current_usage`, `plan_limit`, `remaining_usage` (usado por el
  dashboard y por `LimitGuard`).

---

## 17. Estrategia de seguridad

- Multi-tenant por `company_id` + (opcional) RLS de Postgres.
- RBAC validado en backend en cada endpoint.
- JWT + refresh en cookie HttpOnly; rate limiting (Redis) en auth y API.
- Validación y sanitización de todo input (Pydantic). Protección XSS; CSRF
  donde haya cookies de sesión. CORS restringido.
- Uploads: validar MIME real + extensión + tamaño; nunca ejecutar archivos
  subidos; almacenamiento fuera del webroot o en storage dedicado.
- API keys hasheadas; se muestran completas una sola vez.
- Webhooks firmados con `secret` (HMAC) y con reintentos.
- Auditoría (`audit_logs`) de acciones sensibles. Logs de errores y
  requests importantes. Backups de la DB.
- Nunca confiar en `company_id`, `role`, `chatbot_id` enviados por el
  cliente ni en el widget para autorizar.

---

## 18. Estrategia de despliegue

- **Desarrollo**: `docker-compose` con `backend`, `frontend`, `postgres`
  (con pgvector), `redis`, `worker`. Variables en `.env` (nunca en código):
  ```env
  DATABASE_URL=  REDIS_URL=  JWT_SECRET=
  GROQ_API_KEY=  OPENAI_API_KEY=  ANTHROPIC_API_KEY=  GEMINI_API_KEY=
  APP_URL=  WIDGET_URL=
  ```
- **Producción (VPS actual `187.127.57.56`)**: contenedores detrás de Nginx.
  - `api.zelekpress.com` → backend FastAPI (Uvicorn/Gunicorn) + WS.
  - `app.zelekpress.com` → frontend React (build estático) + `widget.js`.
  - Postgres y Redis como servicios (contenedor o gestionados).
  - Certbot/SSL como ya se usa hoy. `systemd`/Docker para el ciclo de vida.
  - Worker (RQ/Celery) como proceso/contenedor aparte.
- **Migración desde la v1 (SQLite)**: script de migración de las tablas
  `companies`/knowledge actuales a la nueva estructura Postgres, para no
  perder los clientes/config que ya existan.
- CI/CD, tests de funcionalidades críticas, monitoring y backups antes de
  considerar "producción".

---

## Plan de fases (resumen ejecutable)

Se implementa en el orden del brief; no se pasa de fase sin base funcional:

1. **Fundación** — Docker, Postgres, Alembic, auth+JWT, empresas,
   multi-tenant, RBAC, Super Admin, dashboard cliente (esqueleto real).
2. **Chatbots** — CRUD + settings + dominios.
3. **Personalización** — temas, tokens visuales, **preview en tiempo real**
   con el mismo componente del widget real.
4. **Widget** — JS + Shadow DOM + config remota + sesión + instalación.
5. **Conversaciones** — WebSockets + mensajes + estados + agentes + modo
   humano.
6. **IA** — AIProvider + adapters (Groq primero) + streaming + usage.
7. **Knowledge Base** — fuentes + procesamiento + RAG con pgvector.
8. **Leads y Analytics** — captura + métricas + preguntas sin respuesta.
9. **Planes** — planes/límites/usage + *Chatbot Básico $9.990* real +
   abstracción de billing.
10. **API e integraciones** — API pública + API keys + webhooks + adapters.
11. **Producción** — seguridad, tests, optimización, logs, backups, CI/CD.

---

## Nota de alcance (importante)

Esto es un producto grande: no se construye entero en una sola pasada. La
propuesta es implementarlo **fase por fase, verticalmente y revisando cada
una** antes de seguir, empezando por la Fase 1 (Fundación). Antes de
arrancar el código conviene confirmar dos decisiones de infraestructura que
cambian el arranque:

- **VPS**: ¿instalamos Postgres + Redis + Docker en el VPS actual, o preferís
  usar servicios gestionados (p. ej. una DB Postgres administrada)?
- **v1 vs v2**: ¿la v1 actual (SQLite en `api.zelekpress.com`) sigue viva en
  paralelo mientras se construye la v2, o migramos de una?
