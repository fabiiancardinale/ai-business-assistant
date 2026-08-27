"""API Keys por empresa: credenciales para consumir la API pública de la
plataforma desde sistemas de terceros. Guardamos SOLO el hash de la key
(nunca el valor en claro); el valor completo se muestra una única vez al
crearla."""
from datetime import datetime

from sqlalchemy import String, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Prefijo público visible (ej. "zk_live_ab12cd34"): sirve para identificar
    # la key sin exponer el secreto, y para buscarla rápido al autenticar.
    prefix: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # ["read","write"]
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
