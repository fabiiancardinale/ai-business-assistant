"""REST de conversaciones para el panel del cliente (agentes). Todo scopeado
a la empresa activa y con RBAC (agent o superior)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.models.conversation import Conversation, Message
from app.realtime.service import agent_reply, return_to_ai, add_message
from app.webhooks.service import dispatch as dispatch_webhook

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ReplyIn(BaseModel):
    content: str


class ConversationOut(BaseModel):
    id: int
    chatbot_id: int
    status: str
    human_requested: bool
    assigned_agent_id: int | None
    url: str | None = None
    last_message_at: str | None = None

    model_config = {"from_attributes": True}


def _conv(db: Session, tenant: TenantContext, conv_id: int) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if not conv or conv.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conv


@router.get("")
def list_conversations(
    status: str | None = None,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.company_id == tenant.company.id)
    if status:
        stmt = stmt.where(Conversation.status == status)
    stmt = stmt.order_by(desc(Conversation.last_message_at), desc(Conversation.id))
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": c.id, "chatbot_id": c.chatbot_id, "status": c.status,
            "human_requested": c.human_requested, "assigned_agent_id": c.assigned_agent_id,
            "url": c.url,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        }
        for c in rows
    ]


@router.get("/{conv_id}")
def get_conversation(conv_id: int, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    conv = _conv(db, tenant, conv_id)
    msgs = db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
    ).scalars().all()
    return {
        "id": conv.id, "status": conv.status, "human_requested": conv.human_requested,
        "assigned_agent_id": conv.assigned_agent_id, "url": conv.url,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in msgs
        ],
    }


@router.post("/{conv_id}/take")
def take_conversation(conv_id: int, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    conv = _conv(db, tenant, conv_id)
    conv.assigned_agent_id = tenant.user.id
    conv.status = "human"
    db.commit()
    return {"ok": True, "assigned_agent_id": conv.assigned_agent_id, "status": conv.status}


@router.post("/{conv_id}/reply")
def reply_conversation(conv_id: int, data: ReplyIn, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    conv = _conv(db, tenant, conv_id)
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacío")
    m = agent_reply(db, conv, data.content.strip(), tenant.user.id)
    return {"id": m.id, "role": m.role, "content": m.content}


@router.post("/{conv_id}/return-ai")
def return_ai(conv_id: int, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    conv = _conv(db, tenant, conv_id)
    return_to_ai(db, conv)
    return {"ok": True, "status": conv.status}


@router.post("/{conv_id}/close")
def close_conversation(conv_id: int, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    conv = _conv(db, tenant, conv_id)
    conv.status = "closed"
    db.commit()
    dispatch_webhook(db, conv.company_id, "conversation.closed", {
        "conversation_id": conv.id, "conversation_token": conv.token,
        "chatbot_id": conv.chatbot_id,
    })
    return {"ok": True, "status": conv.status}


@router.post("/{conv_id}/note")
def add_note(conv_id: int, data: ReplyIn, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    """Nota interna (no se muestra al visitante)."""
    conv = _conv(db, tenant, conv_id)
    m = add_message(db, conv, "note", data.content.strip(), author_id=tenant.user.id)
    return {"id": m.id, "role": m.role}
