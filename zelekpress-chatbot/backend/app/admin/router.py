"""Super Admin de Zelekpress: visión global de la plataforma y gestión de
empresas (tenants). Todo protegido por require_platform_admin."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_platform_admin
from app.core.slug import unique_slug
from app.models.user import User
from app.models.company import Company
from app.models.chatbot import Chatbot
from app.models.plan import Plan
from app.models.audit import AuditLog
from app.schemas.company import CompanyOut, CompanyCreate

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


@router.get("/companies")
def list_companies(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Company).order_by(Company.created_at.desc())).scalars().all()
    # Incluimos la cantidad de chatbots de cada empresa (útil en el panel).
    out = []
    for c in rows:
        n = db.scalar(select(func.count()).select_from(Chatbot).where(Chatbot.company_id == c.id)) or 0
        out.append({
            "id": c.id, "name": c.name, "slug": c.slug, "status": c.status,
            "plan_id": c.plan_id, "email": c.email, "chatbots": n,
        })
    return out


@router.post("/companies", response_model=CompanyOut, status_code=201)
def admin_create_company(data: CompanyCreate, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    """El admin crea una empresa (cliente) desde el panel."""
    default_plan = db.scalar(select(Plan).where(Plan.active == True).order_by(Plan.position.asc()))  # noqa: E712
    company = Company(
        name=data.name, slug=unique_slug(db, Company, data.name),
        plan_id=default_plan.id if default_plan else None, created_by=admin.id,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    db.add(AuditLog(company_id=company.id, user_id=admin.id, action="create", entity="companies", entity_id=company.id))
    db.commit()
    return CompanyOut.model_validate(company)


@router.delete("/companies/{company_id}", status_code=204)
def admin_delete_company(company_id: int, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(c)  # cascada: chatbots, conversaciones, knowledge, leads, etc.
    db.commit()
    return None


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
