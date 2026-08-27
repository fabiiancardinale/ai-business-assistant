"""API pública de la plataforma (Fase 10).

Autenticada por **API key** (no por JWT de usuario). Cada request queda
automáticamente scopeada a la empresa dueña de la key — nunca puede ver ni
tocar datos de otra empresa. Los endpoints de lectura requieren scope
`read`; los que escriben (enviar mensaje) requieren `write`.

Instalación típica del lado del cliente:

    curl https://api.zelekpress.com/api/v1/pub/chatbots \
      -H "Authorization: Bearer zk_live_xxxxx"
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
import secrets

from app.core.db import get_db
from app.core.api_key import get_api_context, require_scope, ApiContext
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.realtime.service import handle_visitor_message
from app.billing.usage_service import summary as usage_summary

router = APIRouter(prefix="/api/v1/pub", tags=["api-publica"])


@router.get("/me")
def me(ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db)):
    c = ctx.company
    return {
        "company": {"id": c.id, "name": c.name, "slug": c.slug, "status": c.status},
        "api_key": {"name": ctx.api_key.name, "prefix": ctx.api_key.prefix, "scopes": ctx.api_key.scopes},
        "usage": usage_summary(db, c),
    }


@router.get("/usage")
def usage(ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db)):
    return usage_summary(db, ctx.company)


@router.get("/chatbots")
def list_chatbots(ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Chatbot).where(Chatbot.company_id == ctx.company.id).order_by(Chatbot.id)
    ).scalars().all()
    return [
        {"id": b.id, "name": b.name_public, "internal_name": b.name_internal,
         "status": b.status, "language": b.language}
        for b in rows
    ]


@router.get("/leads")
def list_leads(
    limit: int = 50, offset: int = 0,
    ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    rows = db.execute(
        select(Lead).where(Lead.company_id == ctx.company.id)
        .order_by(desc(Lead.id)).limit(limit).offset(max(0, offset))
    ).scalars().all()
    return [
        {"id": l.id, "chatbot_id": l.chatbot_id, "name": l.name, "email": l.email,
         "phone": l.phone, "whatsapp": l.whatsapp, "company_name": l.company_name,
         "message": l.message, "source": l.source, "status": l.status,
         "created_at": l.created_at.isoformat() if l.created_at else None}
        for l in rows
    ]


@router.get("/conversations")
def list_conversations(
    limit: int = 50, offset: int = 0,
    ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    rows = db.execute(
        select(Conversation).where(Conversation.company_id == ctx.company.id)
        .order_by(desc(Conversation.id)).limit(limit).offset(max(0, offset))
    ).scalars().all()
    return [
        {"id": cv.id, "token": cv.token, "chatbot_id": cv.chatbot_id,
         "status": cv.status, "human_requested": cv.human_requested,
         "created_at": cv.created_at.isoformat() if cv.created_at else None}
        for cv in rows
    ]


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: int,
    ctx: ApiContext = Depends(require_scope("read")), db: Session = Depends(get_db),
):
    cv = db.get(Conversation, conversation_id)
    if not cv or cv.company_id != ctx.company.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    msgs = db.execute(
        select(Message).where(Message.conversation_id == cv.id, Message.role != "note")
        .order_by(Message.id)
    ).scalars().all()
    return [
        {"id": m.id, "role": m.role, "content": m.content,
         "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in msgs
    ]


class MessageIn(BaseModel):
    message: str
    conversation_token: str | None = None


@router.post("/chatbots/{chatbot_id}/message")
def send_message(
    chatbot_id: int, data: MessageIn,
    ctx: ApiContext = Depends(require_scope("write")), db: Session = Depends(get_db),
):
    """Envía un mensaje a un chatbot desde un sistema del cliente (server a
    server) y devuelve la respuesta del bot. Si no se pasa
    `conversation_token`, se crea una conversación nueva."""
    from fastapi import HTTPException
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Chatbot no encontrado")

    conv = None
    if data.conversation_token:
        conv = db.scalar(select(Conversation).where(Conversation.token == data.conversation_token))
        if conv and (conv.company_id != ctx.company.id or conv.chatbot_id != bot.id):
            conv = None
    if not conv:
        conv = Conversation(
            company_id=bot.company_id, chatbot_id=bot.id,
            token=secrets.token_urlsafe(24), status="ai", url="api",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    bot_msg = handle_visitor_message(db, conv, data.message)
    return {
        "conversation_token": conv.token,
        "conversation_id": conv.id,
        "reply": bot_msg.content if bot_msg else None,
    }
