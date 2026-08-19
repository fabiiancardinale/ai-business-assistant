from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from database.database import Base


class Company(Base):

    __tablename__ = "companies"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(150),
        nullable=True
    )

    phone = Column(
        String(50),
        nullable=True
    )

    website = Column(
        String(255),
        nullable=True
    )

    knowledge = Column(
        Text,
        nullable=True
    )

    api_key = Column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    # Color principal del widget (botón, header, burbujas del
    # usuario). Se guarda como código hexadecimal, ej: "#111827".
    primary_color = Column(
        String(20),
        nullable=True,
        default="#111827"
    )

    # Ícono del botón flotante del widget. Por ahora es un emoji
    # simple (ej: "💬", "🤖"), no una imagen.
    icon = Column(
        String(10),
        nullable=True,
        default="💬"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Conversation(Base):

    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    company_id = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Message(Base):

    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    conversation_id = Column(
        Integer,
        nullable=False
    )

    role = Column(
        String(20),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )