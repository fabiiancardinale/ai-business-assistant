"""Tracking de consumo y comparación contra los límites del plan.

Escribe directo en Postgres (suficiente por ahora). Si el volumen crece, se
puede mover a contadores en Redis con consolidación periódica, sin cambiar la
interfaz (`track` / `summary`)."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage import Usage
from app.models.company import Company
from app.models.plan import Plan

FIELDS = ("conversations", "messages", "ai_tokens", "leads")


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _get_or_create(db: Session, company_id: int, period: str | None = None) -> Usage:
    period = period or _period()
    row = db.scalar(select(Usage).where(Usage.company_id == company_id, Usage.period == period))
    if not row:
        row = Usage(company_id=company_id, period=period)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def track(db: Session, company_id: int, field: str, n: int = 1) -> None:
    """Incrementa un contador de uso. Nunca rompe el flujo si falla."""
    if field not in FIELDS:
        return
    try:
        row = _get_or_create(db, company_id)
        setattr(row, field, (getattr(row, field) or 0) + n)
        db.commit()
    except Exception:
        db.rollback()


def summary(db: Session, company: Company) -> dict:
    """Uso del período actual vs. los límites del plan."""
    row = _get_or_create(db, company.id)
    limits = {}
    plan_name = None
    if company.plan_id:
        plan = db.get(Plan, company.plan_id)
        if plan:
            plan_name = plan.name
            limits = plan.limits or {}

    out = {"period": row.period, "plan": plan_name, "items": {}}
    for f in FIELDS:
        used = getattr(row, f) or 0
        limit = limits.get(f)
        limit = int(limit) if limit is not None else None
        out["items"][f] = {
            "used": used,
            "limit": limit,
            "remaining": (None if limit is None else max(0, limit - used)),
            "over": (False if limit is None else used >= limit),
        }
    return out


def over_limit(db: Session, company: Company, field: str) -> bool:
    """True si la empresa alcanzó el límite del plan para `field`."""
    if not company.plan_id:
        return False
    plan = db.get(Plan, company.plan_id)
    if not plan or not plan.limits:
        return False
    limit = plan.limits.get(field)
    if limit is None:
        return False
    row = _get_or_create(db, company.id)
    return (getattr(row, field) or 0) >= int(limit)
