"""Chatbots: CRUD + settings + dominios autorizados. Todo scopeado a la
empresa activa (tenant) y protegido por RBAC. Incluye un endpoint público
de configuración para el widget (Fase 4) con validación de dominio."""
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.core.limits import enforce_limit
from app.models.chatbot import Chatbot, ChatbotSettings
from app.models.audit import AuditLog
from app.schemas.chatbot import (
    ChatbotCreate, ChatbotUpdate, ChatbotOut,
    SettingsUpdate, SettingsOut, DomainsUpdate, WidgetConfigOut,
)

router = APIRouter(prefix="/api/v1/chatbots", tags=["chatbots"])
public_router = APIRouter(prefix="/api/v1/public/chatbots", tags=["widget"])


def _get_scoped(db: Session, tenant: TenantContext, chatbot_id: int) -> Chatbot:
    """Trae el chatbot SOLO si pertenece a la empresa activa (aislamiento)."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Chatbot no encontrado")
    return bot


# ---------------------- CRUD (autenticado) ----------------------

@router.get("", response_model=list[ChatbotOut])
def list_chatbots(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Chatbot).where(Chatbot.company_id == tenant.company.id).order_by(Chatbot.id.asc())
    ).scalars().all()
    return [ChatbotOut.model_validate(b) for b in rows]


@router.post("", response_model=ChatbotOut, status_code=201)
def create_chatbot(
    data: ChatbotCreate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    # Respetar el límite de chatbots del plan (Chatbot Básico = 1).
    enforce_limit(db, tenant.company, "chatbots", Chatbot, Chatbot.company_id == tenant.company.id)

    bot = Chatbot(
        company_id=tenant.company.id,
        name_public=data.name_public,
        name_internal=data.name_internal or data.name_public,
        description=data.description,
        language=data.language or "es",
    )
    db.add(bot)
    db.flush()

    # Settings por defecto (1:1) para que el chatbot funcione desde el inicio.
    db.add(ChatbotSettings(
        chatbot_id=bot.id,
        greeting_message="¡Hola! 👋 ¿En qué puedo ayudarte?",
        unknown_message="No tengo esa información. ¿Querés que te contacte con alguien del equipo?",
        temperature=0.4,
        max_tokens=500,
    ))
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id,
                    action="create", entity="chatbots", entity_id=bot.id))
    db.commit()
    db.refresh(bot)
    return ChatbotOut.model_validate(bot)


@router.get("/{chatbot_id}", response_model=ChatbotOut)
def get_chatbot(chatbot_id: int, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    return ChatbotOut.model_validate(_get_scoped(db, tenant, chatbot_id))


@router.patch("/{chatbot_id}", response_model=ChatbotOut)
def update_chatbot(
    chatbot_id: int, data: ChatbotUpdate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _get_scoped(db, tenant, chatbot_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(bot, field, value)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id,
                    action="update", entity="chatbots", entity_id=bot.id))
    db.commit()
    db.refresh(bot)
    return ChatbotOut.model_validate(bot)


@router.delete("/{chatbot_id}", status_code=204)
def delete_chatbot(
    chatbot_id: int,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _get_scoped(db, tenant, chatbot_id)
    db.delete(bot)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id,
                    action="delete", entity="chatbots", entity_id=chatbot_id))
    db.commit()
    return None


# ---------------------- Settings ----------------------

def _get_settings(db: Session, bot: Chatbot) -> ChatbotSettings:
    s = db.scalar(select(ChatbotSettings).where(ChatbotSettings.chatbot_id == bot.id))
    if not s:  # por robustez, si faltara
        s = ChatbotSettings(chatbot_id=bot.id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/{chatbot_id}/settings", response_model=SettingsOut)
def get_settings(chatbot_id: int, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    bot = _get_scoped(db, tenant, chatbot_id)
    return SettingsOut.model_validate(_get_settings(db, bot))


@router.put("/{chatbot_id}/settings", response_model=SettingsOut)
def update_settings(
    chatbot_id: int, data: SettingsUpdate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _get_scoped(db, tenant, chatbot_id)
    s = _get_settings(db, bot)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return SettingsOut.model_validate(s)


# ---------------------- Dominios ----------------------

@router.put("/{chatbot_id}/domains", response_model=ChatbotOut)
def update_domains(
    chatbot_id: int, data: DomainsUpdate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _get_scoped(db, tenant, chatbot_id)
    # Normalizamos: guardamos solo el host (sin esquema ni path).
    domains = []
    for d in data.allowed_domains:
        d = d.strip()
        if not d:
            continue
        host = urlparse(d).netloc or d
        domains.append(host.lower())
    bot.allowed_domains = domains
    db.commit()
    db.refresh(bot)
    return ChatbotOut.model_validate(bot)


# ---------------------- Config pública (widget) ----------------------

@public_router.get("/{chatbot_id}/config", response_model=WidgetConfigOut)
def public_config(
    chatbot_id: int,
    request: Request,
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Config pública que pide el widget. Valida el dominio autorizado y no
    expone ningún dato privado ni API key."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.status != "active":
        raise HTTPException(status_code=404, detail="Chatbot no disponible")

    # Validación de dominio: si hay allowed_domains, el Origin debe coincidir.
    if bot.allowed_domains:
        host = urlparse(origin).netloc.lower() if origin else ""
        allowed = {d.lower() for d in bot.allowed_domains}
        if host not in allowed:
            raise HTTPException(status_code=403, detail="Dominio no autorizado")

    s = db.scalar(select(ChatbotSettings).where(ChatbotSettings.chatbot_id == bot.id))
    from app.core.themes import full_appearance
    return WidgetConfigOut(
        id=bot.id,
        name_public=bot.name_public,
        avatar=bot.avatar,
        logo=bot.logo,
        language=bot.language,
        greeting_message=s.greeting_message if s else None,
        appearance=full_appearance(bot.appearance),
    )
