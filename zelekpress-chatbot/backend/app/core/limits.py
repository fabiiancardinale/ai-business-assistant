"""Control de límites según el plan de la empresa. Enforcement centralizado
(base de la Fase 9). En la Fase 2 lo usamos para el límite de chatbots."""
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.plan import Plan


def plan_limit(db: Session, company: Company, key: str) -> int | None:
    """Devuelve el límite del plan para `key` (o None = sin límite)."""
    if not company.plan_id:
        return None
    plan = db.get(Plan, company.plan_id)
    if not plan or not plan.limits:
        return None
    value = plan.limits.get(key)
    return int(value) if value is not None else None


def enforce_limit(db: Session, company: Company, key: str, model, count_filter) -> None:
    """Lanza 402/403 si crear un recurso `key` superaría el límite del plan."""
    limit = plan_limit(db, company, key)
    if limit is None:
        return  # sin límite definido
    current = db.scalar(
        select(func.count()).select_from(model).where(count_filter)
    ) or 0
    if current >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Alcanzaste el límite de tu plan para '{key}' ({limit}). "
                   f"Mejorá de plan para agregar más.",
        )
