# Zelekpress Chatbots — Plataforma SaaS

Plataforma SaaS multi-tenant para crear, administrar y desplegar chatbots
con IA. Producto propio de Zelekpress.

> **Estado: Fases 1 a 4 — completas y verificadas.**
> - **Fase 1 (Fundación):** FastAPI + PostgreSQL, auth JWT, multi-tenant
>   real, RBAC, Super Admin, planes con el **Chatbot Básico ($9.990 CLP)**.
> - **Fase 2 (Chatbots):** CRUD + settings + dominios autorizados, con
>   límite por plan.
> - **Fase 3 (Personalización):** tokens de diseño, 7 temas predefinidos,
>   biblioteca de temas por empresa, subida de imagen para el launcher/logo,
>   y **preview en tiempo real** (`widget/preview.html`).
> - **Fase 4 (Widget):** `widget/widget.js` real con **Shadow DOM**
>   (aislado del sitio anfitrión), que lee la config remota y se instala con
>   un `<script>`. Demo en `widget/demo.html`.
> - **Fase 5 (Conversaciones):** persistencia de conversaciones/mensajes,
>   **WebSockets** (push en vivo al visitante y a los agentes), **modo
>   humano** (el visitante pide una persona, la IA se pausa, un agente toma
>   la conversación, responde y la devuelve a la IA), y bandeja de agente en
>   el backend. El widget escucha el WS y trae un botón "hablar con una
>   persona".
>
> La arquitectura completa está en `docs/ARQUITECTURA-SAAS-ZELEKPRESS.md`.
>
> Nota: el tiempo real corre en un solo proceso (in-memory). Para escalar a
> varios workers se cambia el bus a Redis, sin tocar la lógica.

## Instalar el widget en un sitio

```html
<script
  src="https://app.zelekpress.com/widget/widget.js"
  data-chatbot-id="1"
  data-api="https://api.zelekpress.com"></script>
```

Para probar en local: levantá el backend, abrí `widget/demo.html` (o
serví el widget desde `http://localhost:8000/widget/widget.js`) y apuntá
`data-api` a `http://localhost:8000`.

> Nota: en la Fase 4 la respuesta del bot es un placeholder. La respuesta
> con IA real llega en la Fase 6, y el chat en vivo (WebSocket + modo
> humano + persistencia) en la Fase 5 — sin cambiar la instalación.

## Qué ya funciona (Fase 1)

- **Auth**: registro (crea usuario + su empresa como `owner`), login,
  refresh, `/me`, logout — con JWT.
- **Multi-tenant real**: cada empresa (`company`) está aislada; el backend
  valida la membresía en cada request (nunca confía en el `company_id` del
  cliente). Un usuario no puede ver empresas de las que no es miembro.
- **RBAC**: roles `owner / admin / agent / viewer` por empresa + Super Admin
  de plataforma, validados en backend.
- **Empresas**: crear, listar las propias, editar, gestionar miembros.
- **Planes**: lectura pública + CRUD solo para Super Admin. Plan inicial
  **Chatbot Básico $9.990 CLP** con límites configurables (no hardcodeados).
- **Super Admin**: overview de la plataforma, listar/suspender/activar
  empresas.
- **Auditoría**: `audit_logs` de acciones sensibles.

Verificado con un smoke test real (registro → login → crear empresa →
aislamiento multi-tenant → RBAC → super admin → suspender/activar).

## Estructura

```
zelekpress-chatbot/
├── backend/            # FastAPI (Fase 1 lista)
│   └── app/
│       ├── core/       # config, db, security, deps (auth+tenant+RBAC), slug
│       ├── models/     # users, companies, members, plans, subscriptions, audit
│       ├── schemas/    # Pydantic
│       ├── auth/  companies/  plans/  admin/    # routers
│       ├── seed.py     # plan Chatbot Básico $9.990 + super admin
│       └── main.py
├── frontend/           # React + TS (Fase siguiente)
├── widget/             # widget JS con Shadow DOM (Fase 4)
├── docs/               # arquitectura
└── docker-compose.yml  # backend + postgres(pgvector) + redis
```

## Cómo correrlo

### Opción A — Docker (recomendado)

```bash
cp backend/.env.example backend/.env      # y editá JWT_SECRET
docker compose up --build
```

Levanta Postgres (con pgvector), Redis y el backend. El backend corre el
seed automáticamente. API en http://localhost:8000, docs en
http://localhost:8000/docs.

### Opción B — Local sin Docker (para probar rápido con SQLite)

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="sqlite:///./dev.db"   # SQLite local, sin Postgres
python -m app.seed                          # crea tablas + plan + super admin
uvicorn app.main:app --reload
```

## Acceso inicial

- **Super Admin**: `admin@zelekpress.com` / `Zelekpress2026!`
  (definido en `.env`, se crea con el seed). Cambialo en producción.

## Documentación de la API

FastAPI genera Swagger automático en **`/docs`** y OpenAPI en
`/openapi.json`.

## Próximas fases (según `docs/ARQUITECTURA-SAAS-ZELEKPRESS.md`)

6. IA (AIProvider + adapters, Groq primero)
7. Knowledge Base (RAG con pgvector)
8. Leads y Analytics
9. Planes/límites/usage + billing abstraction
10. API pública + integraciones
11. Producción (seguridad, tests, CI/CD)

Se avanza fase por fase; no se pasa a la siguiente sin base funcional.
