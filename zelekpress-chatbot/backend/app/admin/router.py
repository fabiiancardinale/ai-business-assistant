"""Super Admin de Zelekpress: visión global de la plataforma y gestión de
empresas (tenants). Todo protegido por require_platform_admin."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_platform_admin
from app.models.user import User
from app.models.company import Company
from app.models.plan import Plan
from app.models.audit import AuditLog
from app.schemas.company import CompanyOut

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/overview")
def overview(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    def count(model, *where):
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return db.scalar(stmt) or 0

    return {
        "companies_total": count(Company),
        "companies_active": count(Company, Company.status == "active"),
        "companies_suspended": count(Company, Company.status == "suspended"),
        "users_total": count(User),
        "plans_total": count(Plan),
    }


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Company).order_by(Company.created_at.desc())).scalars().all()
    return [CompanyOut.model_validate(c) for c in rows]


@router.post("/companies/{company_id}/suspend", response_model=CompanyOut)
def suspend_company(company_id: int, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    c.status = "suspended"
    db.add(AuditLog(company_id=c.id, user_id=admin.id, action="suspend", entity="companies", entity_id=c.id))
    db.commit()
    db.refresh(c)
    return CompanyOut.model_validate(c)


@router.post("/companies/{company_id}/activate", response_model=CompanyOut)
def activate_company(company_id: int, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    c.status = "active"
    db.add(AuditLog(company_id=c.id, user_id=admin.id, action="activate", entity="companies", entity_id=c.id))
    db.commit()
    db.refresh(c)
    return CompanyOut.model_validate(c)
