"""Seed idempotente: crea las tablas, el plan inicial (Chatbot Básico
$9.990 CLP) y el Super Admin de Zelekpress. Se puede correr varias veces.

Uso:  python -m app.seed
"""
from sqlalchemy import select

from app.core.db import Base, engine, SessionLocal
from app.core.config import settings
from app.core.security import hash_password
import app.models  # noqa: F401  (registra todos los modelos)
from app.models.user import User
from app.models.plan import Plan


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Plan inicial real: Chatbot Básico — $9.990 CLP.
        basic = db.scalar(select(Plan).where(Plan.slug == "chatbot-basico"))
        if not basic:
            db.add(Plan(
                name="Chatbot Básico",
                slug="chatbot-basico",
                price=9990,
                currency="CLP",
                period="monthly",
                position=1,
                active=True,
                limits={
                    "chatbots": 1,
                    "conversations": 500,
                    "messages": 5000,
                    "users": 2,
                    "ai_tokens": 200000,
                    "storage_mb": 50,
                    "knowledge_sources": 10,
                },
                features={
                    "custom_appearance": True,
                    "knowledge_base": True,
                    "widget": True,
                    "analytics": "basic",
                    "integrations": False,
                    "webhooks": False,
                    "api": False,
                },
            ))
            print("✓ Plan 'Chatbot Básico' ($9.990 CLP) creado.")
        else:
            print("• Plan 'Chatbot Básico' ya existe.")

        # Super Admin de la plataforma.
        admin = db.scalar(select(User).where(User.email == settings.SUPERADMIN_EMAIL.lower()))
        if not admin:
            db.add(User(
                name=settings.SUPERADMIN_NAME,
                email=settings.SUPERADMIN_EMAIL.lower(),
                password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                is_platform_admin=True,
                is_active=True,
            ))
            print(f"✓ Super Admin creado: {settings.SUPERADMIN_EMAIL}")
        else:
            print("• Super Admin ya existe.")

        db.commit()
        print("✓ Seed completo.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
