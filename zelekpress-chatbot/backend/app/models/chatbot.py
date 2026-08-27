from sqlalchemy import String, Integer, Float, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Chatbot(Base, TimestampMixin):
    __tablename__ = "chatbots"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name_internal: Mapped[str] = mapped_column(String(150), nullable=False)
    name_public: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active|paused
    # Dominios autorizados a incrustar el widget. Vacío = cualquiera (dev).
    allowed_domains: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Apariencia: tokens de diseño (colores, layout, launcher, header...).
    # Guarda solo los overrides sobre DEFAULT_APPEARANCE.
    appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    settings: Mapped["ChatbotSettings"] = relationship(
        back_populates="chatbot", uselist=False, cascade="all, delete-orphan"
    )


class ChatbotTheme(Base, TimestampMixin):
    """Biblioteca de temas guardados por empresa (reutilizables)."""
    __tablename__ = "chatbot_themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_theme: Mapped[str | None] = mapped_column(String(60), nullable=True)  # preset del que parte
    tokens: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ChatbotSettings(Base, TimestampMixin):
    """Comportamiento e IA del chatbot (relación 1:1 con Chatbot)."""
    __tablename__ = "chatbot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    chatbot_id: Mapped[int] = mapped_column(
        ForeignKey("chatbots.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    greeting_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    unknown_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    farewell_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuración de IA (los proveedores/modelos se conectan en la Fase 6).
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.4, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=500, nullable=False)

    # Comportamiento del widget (auto_open, delay, horarios, sonido, etc.).
    behavior: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    chatbot: Mapped["Chatbot"] = relationship(back_populates="settings")
