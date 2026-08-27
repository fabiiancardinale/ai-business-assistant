"""Webhooks por empresa: la plataforma hace POST a la URL del cliente cuando
ocurre un evento (lead nuevo, conversación nueva, pedido de humano, etc.).
Cada entrega va firmada con HMAC-SHA256 usando el `secret`, para que el
receptor pueda verificar autenticidad."""
from datetime import datetime

from sqlalchemy import String, ForeignKey, Boolean, DateTime, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Eventos suscritos (ej. ["lead.created","conversation.created"]).
    events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)  # para firmar HMAC
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Diagnóstico de la última entrega (para que el cliente vea si funciona).
    last_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
