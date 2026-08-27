"""Planes: lectura pública (para la landing/onboarding) y CRUD solo para el
Super Admin de Zelekpress."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_platform_admin
from app.core.slug import unique_slug
from app.models.plan import Plan
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanUpdate, PlanOut

public_router = APIRouter(prefix="/api/v1/plans", tags=["plans"])
admin_router = APIRouter(prefix="/api/v1/admin/plans", tags=["admin:plans"])


@public_router.get("", response_model=list[PlanOut])
def list_public_plans(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Plan).where(Plan.active == True).order_by(Plan.position.asc())  # noqa: E712
    ).scalars().all()
    return [PlanOut.model_validate(p) for p in rows]


@admin_router.get("", response_model=list[PlanOut])
def list_all_plans(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Plan).order_by(Plan.position.asc())).scalars().all()
    return [PlanOut.model_validate(p) for p in rows]


@admin_router.post("", response_model=PlanOut, status_code=201)
def create_plan(data: PlanCreate, _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    plan = Plan(
        name=data.name,
        slug=data.slug or unique_slug(db, Plan, data.name),
        price=data.price, currency=data.currency, period=data.period,
        limits=data.limits, features=data.features,
        active=data.active, position=data.position,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@admin_router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, data: PlanUpdate, _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@admin_router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, _: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    db.delete(plan)
    db.commit()
    return None
