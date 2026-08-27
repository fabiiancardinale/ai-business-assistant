"""Lógica compartida de conversaciones. La usan tanto los endpoints REST
públicos como (a futuro) los WebSockets. Persiste en la base y transmite en
vivo por el manager."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.realtime.manager import manager


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
    return m


# Respuesta placeholder hasta la Fase 6 (IA real). No cambia la interfaz.
PLACEHOLDER_REPLY = ("¡Gracias por tu mensaje! 🙌 En breve te respondemos. "
                     "Si preferís, podés pedir hablar con una persona.")


def handle_visitor_message(db: Session, conv: Conversation, text: str) -> Message | None:
    """Guarda el mensaje del visitante, avisa a los agentes y —si NO está en
    modo humano— genera la respuesta del bot. Devuelve el mensaje del bot (o
    None si está en modo humano, donde responde un agente)."""
    visitor_msg = add_message(db, conv, "visitor", text)
    manager.to_agents(conv.company_id, {
        "type": "visitor_message",
        "conversation_id": conv.id,
        "content": text,
        "message": _msg_payload(visitor_msg),
    })

    if conv.status == "human" or conv.human_requested:
        return None  # el agente responde

    # La respuesta del bot vuelve por el propio REST (no la empujamos también
    # por WS para no duplicarla). El WS del visitante se usa para los mensajes
    # de los agentes humanos.
    bot_msg = add_message(db, conv, "bot", PLACEHOLDER_REPLY)
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
