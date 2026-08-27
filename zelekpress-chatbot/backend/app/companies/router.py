"""Empresas del usuario (tenant) + miembros. Todo scopeado a la membresía
del usuario autenticado."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant, require_role, TenantContext
from app.core.slug import unique_slug
from app.models.user import User
from app.models.company import Company, CompanyMember, ROLES
from app.models.plan import Plan
from app.models.audit import AuditLog
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut, MemberInvite, MemberOut

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
def my_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Company).join(CompanyMember, CompanyMember.company_id == Company.id)
        .where(CompanyMember.user_id == user.id)
    ).scalars().all()
    return [CompanyOut.model_validate(c) for c in rows]


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(data: CompanyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    default_plan = db.scalar(select(Plan).where(Plan.active == True).order_by(Plan.position.asc()))  # noqa: E712
    company = Company(
        name=data.name,
        slug=unique_slug(db, Company, data.name),
        plan_id=default_plan.id if default_plan else None,
        created_by=user.id,
    )
    db.add(company)
    db.flush()
    db.add(CompanyMember(company_id=company.id, user_id=user.id, role="owner"))
    db.add(AuditLog(company_id=company.id, user_id=user.id, action="create", entity="companies", entity_id=company.id))
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, tenant: TenantContext = Depends(get_tenant)):
    # get_tenant ya validó que company_id (via header) sea del usuario; acá
    # exigimos coincidencia con el de la URL para evitar confusiones.
    if tenant.company.id != company_id:
        raise HTTPException(status_code=403, detail="Empresa no coincide con el contexto")
    return CompanyOut.model_validate(tenant.company)


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int, data: CompanyUpdate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if tenant.company.id != company_id:
        raise HTTPException(status_code=403, detail="Empresa no coincide con el contexto")
    c = tenant.company
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.add(AuditLog(company_id=c.id, user_id=tenant.user.id, action="update", entity="companies", entity_id=c.id))
    db.commit()
    db.refresh(c)
    return CompanyOut.model_validate(c)


@router.get("/{company_id}/members", response_model=list[MemberOut])
def list_members(
    company_id: int,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(CompanyMember, User).join(User, User.id == CompanyMember.user_id)
        .where(CompanyMember.company_id == tenant.company.id)
    ).all()
    return [
        MemberOut(id=m.id, user_id=u.id, name=u.name, email=u.email, role=m.role)
        for (m, u) in rows
    ]


@router.post("/{company_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    company_id: int, data: MemberInvite,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if data.role not in ROLES:
        raise HTTPException(status_code=400, detail="Rol inválido")
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese email (debe registrarse primero)")
    existing = db.scalar(select(CompanyMember).where(
        CompanyMember.company_id == tenant.company.id, CompanyMember.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Ese usuario ya es miembro")
    member = CompanyMember(company_id=tenant.company.id, user_id=user.id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberOut(id=member.id, user_id=user.id, name=user.name, email=user.email, role=member.role)
