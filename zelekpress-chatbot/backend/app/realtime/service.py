"""Lógica compartida de conversaciones. La usan tanto los endpoints REST
públicos como (a futuro) los WebSockets. Persiste en la base y transmite en
vivo por el manager."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.realtime.manager import manager
from app.ai.service import generate_reply
from app.billing.usage_service import track

logger = logging.getLogger("zelekpress.ai")


def _msg_payload(m: Message) -> dict:
    return {
        "type": "message",
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def add_message(db: Session, conv: Conversation, role: str, content: str, author_id: int | None = None) -> Message:
    m = Message(
        conversation_id=conv.id, company_id=conv.company_id,
        role=role, content=content, author_id=author_id,
    )
    db.add(m)
    conv.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    # Uso: contamos los mensajes que "cuestan" (visitante y bot); los de
    # sistema/nota no.
    if role in ("visitor", "bot", "agent"):
        track(db, conv.company_id, "messages")
    return m


# Mensaje de seguridad si la IA falla (API caída, sin key mal configurada, etc.).
FALLBACK_REPLY = ("Perdón, tuve un problema para responder en este momento. "
                  "Probá de nuevo o pedí hablar con una persona.")


def handle_visitor_message(db: Session, conv: Conversation, text: str) -> Message | None:
    """Guarda el mensaje del visitante, avisa a los agentes y —si NO está en
    modo humano— genera la respuesta del bot con IA. Devuelve el mensaje del
    bot (o None si está en modo humano, donde responde un agente)."""
    visitor_msg = add_message(db, conv, "visitor", text)
    manager.to_agents(conv.company_id, {
        "type": "visitor_message",
        "conversation_id": conv.id,
        "content": text,
        "message": _msg_payload(visitor_msg),
    })

    if conv.status == "human" or conv.human_requested:
        return None  # el agente responde

    # Respuesta con IA (Fase 6). Si algo falla, respondemos algo seguro y no
    # rompemos el chat. La respuesta vuelve por REST (no la duplicamos por WS).
    try:
        reply_text = generate_reply(db, conv)
    except Exception as e:  # noqa: BLE001
        logger.warning("Fallo generando respuesta IA: %s", e)
        reply_text = FALLBACK_REPLY

    bot_msg = add_message(db, conv, "bot", reply_text)
    return bot_msg


def request_human(db: Session, conv: Conversation) -> None:
    conv.human_requested = True
    conv.status = "human"
    db.commit()
    sys = add_message(db, conv, "system", "El visitante pidió hablar con una persona.")
    manager.to_agents(conv.company_id, {
        "type": "human_requested",
        "conversation_id": conv.id,
        "message": _msg_payload(sys),
    })


def agent_reply(db: Session, conv: Conversation, text: str, agent_id: int) -> Message:
    """Respuesta de un agente humano: se guarda y se transmite al visitante."""
    if conv.assigned_agent_id is None:
        conv.assigned_agent_id = agent_id
        conv.status = "human"
    m = add_message(db, conv, "agent", text, author_id=agent_id)
    manager.to_visitor(conv.id, _msg_payload(m))
    return m


def return_to_ai(db: Session, conv: Conversation) -> None:
    conv.status = "ai"
    conv.human_requested = False
    db.commit()
    sys = add_message(db, conv, "system", "La conversación volvió al asistente.")
    manager.to_visitor(conv.id, {"type": "system", "content": "Seguís con el asistente virtual."})
    manager.to_agents(conv.company_id, {"type": "returned_ai", "conversation_id": conv.id})
