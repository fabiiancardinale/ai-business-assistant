"""Punto de entrada de la API — Plataforma SaaS de Chatbots de Zelekpress.
FASE 1 (Fundación): auth, empresas multi-tenant, RBAC, planes, super admin."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import Base, engine
import app.models  # noqa: F401  (registra los modelos)

from app.auth.router import router as auth_router
from app.companies.router import router as companies_router
from app.plans.router import public_router as plans_public_router, admin_router as plans_admin_router
from app.admin.router import router as admin_router
from app.chatbots.router import router as chatbots_router, public_router as chatbots_public_router
from app.chatbots.appearance_router import router as appearance_router
from app.conversations.router import router as conversations_router
from app.knowledge.router import router as knowledge_router
from app.leads.router import router as leads_router
from app.analytics.router import router as analytics_router
from app.integrations.router import router as integrations_router
from app.public_api.router import router as public_api_router
from app.realtime.ws_router import router as ws_router

app = FastAPI(
    title="Zelekpress Chatbots API",
    version="0.1.0 (Fase 1)",
    description="Plataforma SaaS multi-tenant de chatbots de Zelekpress.",
)

# El widget se incrusta en sitios de terceros, así que la API acepta
# cualquier origen. No usamos cookies (auth por Bearer token en el header),
# por eso allow_credentials=False es seguro y compatible con "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # En dev creamos las tablas si no existen. En producción se usa Alembic.
    if settings.APP_ENV != "production":
        Base.metadata.create_all(bind=engine)


# Servir imágenes subidas (launcher, logo, avatar) en /uploads.
_uploads_path = Path(settings.UPLOADS_DIR)
_uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_path)), name="uploads")

# Servir el widget (widget.js, demo.html) en /widget. Buscamos la carpeta
# en varias ubicaciones para que funcione tanto en el layout del repo como
# dentro de Docker (donde /app es el backend). Se puede fijar con WIDGET_DIR.
import os as _os
_candidates = [
    _os.environ.get("WIDGET_DIR", ""),
    str(Path(__file__).resolve().parent.parent.parent / "widget"),  # repo: .../zelekpress-chatbot/widget
    str(Path(__file__).resolve().parent.parent / "widget"),          # docker: /app/widget (montado)
    "/widget",
]
for _cand in _candidates:
    if _cand and Path(_cand).is_dir():
        app.mount("/widget", StaticFiles(directory=_cand), name="widget")
        break


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(plans_public_router)
app.include_router(plans_admin_router)
app.include_router(admin_router)
app.include_router(chatbots_router)
app.include_router(chatbots_public_router)
app.include_router(appearance_router)
app.include_router(conversations_router)
app.include_router(knowledge_router)
app.include_router(leads_router)
app.include_router(analytics_router)
app.include_router(integrations_router)
app.include_router(public_api_router)
app.include_router(ws_router)
