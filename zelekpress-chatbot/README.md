# Zelekpress Chatbots — Plataforma SaaS

Plataforma SaaS multi-tenant para crear, administrar y desplegar chatbots
con IA. Producto propio de Zelekpress.

> **Estado: Fase 1 (Fundación) — completa y verificada.**
> Backend FastAPI + PostgreSQL, autenticación JWT, multi-tenant real, RBAC,
> Super Admin, y planes con el **Chatbot Básico ($9.990 CLP)** como plan
> inicial real. La arquitectura completa está en
> `docs/ARQUITECTURA-SAAS-ZELEKPRESS.md`.

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

2. Chatbots (CRUD + settings + dominios)
3. Personalización + preview en tiempo real
4. Widget (JS + Shadow DOM)
5. Conversaciones (WebSockets + modo humano)
6. IA (AIProvider + adapters, Groq primero)
7. Knowledge Base (RAG con pgvector)
8. Leads y Analytics
9. Planes/límites/usage + billing abstraction
10. API pública + integraciones
11. Producción (seguridad, tests, CI/CD)

Se avanza fase por fase; no se pasa a la siguiente sin base funcional.
