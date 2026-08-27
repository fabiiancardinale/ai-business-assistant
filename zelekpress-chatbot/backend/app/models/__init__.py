"""Registro central de modelos (importar todos para que SQLAlchemy los
conozca al crear las tablas)."""
from app.models.user import User
from app.models.company import Company, CompanyMember
from app.models.plan import Plan, Subscription
from app.models.chatbot import Chatbot, ChatbotSettings, ChatbotTheme
from app.models.conversation import Conversation, Message
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.audit import AuditLog

__all__ = [
    "User", "Company", "CompanyMember", "Plan", "Subscription",
    "Chatbot", "ChatbotSettings", "ChatbotTheme",
    "Conversation", "Message",
    "KnowledgeSource", "KnowledgeChunk", "AuditLog",
]
