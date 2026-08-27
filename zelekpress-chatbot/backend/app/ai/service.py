"""Servicio de IA: arma el prompt (system prompt del negocio + historial) y
genera la respuesta usando el AIProvider configurado."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.provider import get_provider
from app.models.chatbot import Chatbot, ChatbotSettings
from app.models.conversation import Conversation, Message

# Cuántos mensajes previos se mandan como contexto.
HISTORY_LIMIT = 12

# Reglas base que se agregan siempre al system prompt del cliente, para que
# el bot no se vaya de tema ni invente.
BASE_RULES = (
    "Respondé en español, de forma amable, clara y breve. "
    "Usá únicamente la información del negocio provista. "
    "Si no tenés la información, decilo con honestidad y ofrecé contactar al equipo. "
    "No inventes precios, plazos ni datos que no te hayan dado."
)


def _system_prompt(bot: Chatbot, s: ChatbotSettings | None) -> str:
    parts = []
    if s and s.system_prompt:
        parts.append(s.system_prompt.strip())
    else:
        parts.append(f"Sos el asistente virtual de {bot.name_public}.")
    if s and s.personality:
        parts.append("Personalidad: " + s.personality.strip())
    parts.append(BASE_RULES)
    return "\n\n".join(parts)


def _history(db: Session, conv: Conversation) -> list[dict]:
    rows = db.execute(
        select(Message).where(Message.conversation_id == conv.id)
        .order_by(Message.id.desc()).limit(HISTORY_LIMIT)
    ).scalars().all()
    rows = list(reversed(rows))
    out = []
    for m in rows:
        if m.role == "visitor":
            out.append({"role": "user", "content": m.content})
        elif m.role in ("bot", "agent"):
            out.append({"role": "assistant", "content": m.content})
        # system/note no se mandan al modelo
    return out


def build_messages(db: Session, bot: Chatbot, s: ChatbotSettings | None, conv: Conversation) -> list[dict]:
    messages = [{"role": "system", "content": _system_prompt(bot, s)}]
    messages.extend(_history(db, conv))
    return messages


def generate_reply(db: Session, conv: Conversation) -> str:
    """Genera la respuesta del bot para el último mensaje de la conversación."""
    bot = db.get(Chatbot, conv.chatbot_id)
    s = db.scalar(select(ChatbotSettings).where(ChatbotSettings.chatbot_id == conv.chatbot_id))

    messages = build_messages(db, bot, s, conv)
    model = (s.model if s and s.model else settings.DEFAULT_AI_MODEL)
    temperature = (s.temperature if s and s.temperature is not None else 0.4)
    max_tokens = (s.max_tokens if s and s.max_tokens else 500)

    provider = get_provider()
    return provider.generate(messages, model=model, temperature=temperature, max_tokens=max_tokens)
