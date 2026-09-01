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
from app.models.conversation import Conversation
from app.models.audit import AuditLog
from app.realtime.service import add_message, handle_visitor_message, request_human
from app.billing.usage_service import track
from app.webhooks.service import dispatch as dispatch_webhook
from app.schemas.chatbot import (
    ChatbotCreate, ChatbotUpdate, ChatbotOut,
    SettingsUpdate, SettingsOut, DomainsUpdate, WidgetConfigOut,
    SessionOut, PublicMessageIn, PublicMessageOut, SessionRef,
)
import secrets

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
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    # La creación de chatbots es exclusiva del Super Admin de Zelekpress:
    # el cliente registra su cuenta, pero el bot lo da de alta el equipo
    # (típicamente después de confirmar el pago). El cliente sí puede
    # configurar/administrar el bot una vez creado.
    if not tenant.user.is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail="La creación de chatbots la realiza el equipo de Zelekpress. Escribinos para activar tu bot.",
        )

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


def _origin_allowed(bot: Chatbot, origin: str | None) -> bool:
    if not bot.allowed_domains:
        return True
    host = urlparse(origin).netloc.lower() if origin else ""
    return host in {d.lower() for d in bot.allowed_domains}


@public_router.post("/{chatbot_id}/session", response_model=SessionOut)
def create_session(
    chatbot_id: int,
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Inicia una sesión de visitante: crea la conversación persistente y
    devuelve su token público + el saludo inicial."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.status != "active":
        raise HTTPException(status_code=404, detail="Chatbot no disponible")
    if not _origin_allowed(bot, origin):
        raise HTTPException(status_code=403, detail="Dominio no autorizado")

    conv = Conversation(
        company_id=bot.company_id, chatbot_id=bot.id,
        token=secrets.token_urlsafe(24), status="ai",
        url=origin,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    track(db, bot.company_id, "conversations")
    dispatch_webhook(db, bot.company_id, "conversation.created", {
        "conversation_id": conv.id, "conversation_token": conv.token,
        "chatbot_id": bot.id, "url": origin,
    })

    s = db.scalar(select(ChatbotSettings).where(ChatbotSettings.chatbot_id == bot.id))
    greeting = s.greeting_message if s else None
    if greeting:
        add_message(db, conv, "bot", greeting)

    return SessionOut(session_id=conv.token, greeting=greeting)


@public_router.post("/{chatbot_id}/message", response_model=PublicMessageOut)
def public_message(
    chatbot_id: int,
    data: PublicMessageIn,
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Recibe un mensaje del visitante, lo persiste, avisa a los agentes y
    (si no está en modo humano) responde. La respuesta con IA real llega en
    la Fase 6 — la firma no cambia."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.status != "active":
        raise HTTPException(status_code=404, detail="Chatbot no disponible")
    if not _origin_allowed(bot, origin):
        raise HTTPException(status_code=403, detail="Dominio no autorizado")

    conv = _conv_by_token(db, data.session_id, bot)
    bot_msg = handle_visitor_message(db, conv, data.message)
    return PublicMessageOut(reply=bot_msg.content if bot_msg else None, session_id=conv.token)


@public_router.post("/{chatbot_id}/request-human", response_model=PublicMessageOut)
def public_request_human(
    chatbot_id: int,
    data: SessionRef,
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """El visitante pide hablar con una persona: la IA se pausa y se avisa a
    los agentes."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.status != "active":
        raise HTTPException(status_code=404, detail="Chatbot no disponible")
    if not _origin_allowed(bot, origin):
        raise HTTPException(status_code=403, detail="Dominio no autorizado")

    conv = _conv_by_token(db, data.session_id, bot)
    request_human(db, conv)
    return PublicMessageOut(
        reply="Te estamos conectando con una persona del equipo. Escribí tu consulta y te respondemos por acá.",
        session_id=conv.token,
    )


@public_router.post("/{chatbot_id}/lead")
def public_lead(
    chatbot_id: int,
    data: dict,
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """El visitante deja sus datos de contacto desde el widget."""
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.status != "active":
        raise HTTPException(status_code=404, detail="Chatbot no disponible")
    if not _origin_allowed(bot, origin):
        raise HTTPException(status_code=403, detail="Dominio no autorizado")

    from app.models.lead import Lead
    conv = None
    if data.get("session_id"):
        conv = db.scalar(select(Conversation).where(Conversation.token == data["session_id"]))

    lead = Lead(
        company_id=bot.company_id, chatbot_id=bot.id,
        conversation_id=conv.id if conv else None,
        name=(data.get("name") or None),
        email=(data.get("email") or None),
        phone=(data.get("phone") or None),
        whatsapp=(data.get("whatsapp") or None),
        company_name=(data.get("company") or None),
        message=(data.get("message") or None),
        source="chat",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    track(db, bot.company_id, "leads")
    dispatch_webhook(db, bot.company_id, "lead.created", {
        "lead_id": lead.id, "chatbot_id": bot.id,
        "name": lead.name, "email": lead.email, "phone": lead.phone,
        "whatsapp": lead.whatsapp, "company_name": lead.company_name,
        "message": lead.message, "conversation_id": lead.conversation_id,
    })
    return {"ok": True, "lead_id": lead.id}


def _conv_by_token(db: Session, token: str | None, bot: Chatbot) -> Conversation:
    conv = db.scalar(select(Conversation).where(Conversation.token == token)) if token else None
    if not conv or conv.chatbot_id != bot.id:
        # Si el token no existe (sesión perdida), creamos una nueva.
        conv = Conversation(
            company_id=bot.company_id, chatbot_id=bot.id,
            token=secrets.token_urlsafe(24), status="ai",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv
