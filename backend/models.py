from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
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

    # Ícono del botón flotante del widget. Puede ser un emoji
    # (ej: "💬", "🤖") o la URL de una imagen subida desde el
    # admin (ej: "/uploads/icons/company_3.png"), por eso el
    # campo es más largo que un emoji suelto.
    icon = Column(
        String(255),
        nullable=True,
        default="💬"
    )

    # Si es False, el botón flotante no lleva color de fondo
    # detrás del ícono (útil cuando el ícono es una imagen/logo
    # que ya tiene su propio diseño y no necesita el círculo de
    # color detrás). Por defecto True (con fondo de color).
    icon_has_background = Column(
        Boolean,
        nullable=True,
        default=True
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