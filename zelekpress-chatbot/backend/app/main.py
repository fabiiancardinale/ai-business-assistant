"""Punto de entrada de la API — Plataforma SaaS de Chatbots de Zelekpress.
FASE 1 (Fundación): auth, empresas multi-tenant, RBAC, planes, super admin."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import Base, engine
import app.models  # noqa: F401  (registra los modelos)

from app.auth.router import router as auth_router
from app.companies.router import router as companies_router
from app.plans.router import public_router as plans_public_router, admin_router as plans_admin_router
from app.admin.router import router as admin_router

app = FastAPI(
    title="Zelekpress Chatbots API",
    version="0.1.0 (Fase 1)",
    description="Plataforma SaaS multi-tenant de chatbots de Zelekpress.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # En dev creamos las tablas si no existen. En producción se usa Alembic.
    if settings.APP_ENV != "production":
        Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(plans_public_router)
app.include_router(plans_admin_router)
app.include_router(admin_router)
