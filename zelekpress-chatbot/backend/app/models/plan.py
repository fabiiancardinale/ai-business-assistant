from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Plan(Base, TimestampMixin):
    """Planes comerciales. NO están hardcodeados: el Super Admin los crea
    y edita. El plan inicial (Chatbot Básico $9.990 CLP) se carga en el seed."""
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    period: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)  # monthly|yearly|one_time
    # límites y features son configurables (jsonb) — no columnas rígidas.
    limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active|past_due|canceled
    provider: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)  # manual|stripe|mercadopago
    external_ref: Mapped[str | None] = mapped_column(String(190), nullable=True)
