"""Autenticación: registro, login, refresh, /me, logout.
El registro crea el usuario + su primera empresa (owner) en una sola
operación (implementación vertical real: API → validación → DB)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.slug import unique_slug
from app.models.user import User
from app.models.company import Company, CompanyMember
from app.models.plan import Plan
from app.models.audit import AuditLog
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenPair, RefreshRequest,
    MeOut, UserOut, MembershipOut,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.email == data.email.lower()))
    if exists:
        raise HTTPException(status_code=409, detail="Ese email ya está registrado")

    user = User(
        name=data.name,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()  # obtener user.id

    # Empresa inicial, asignada al plan por defecto si existe.
    default_plan = db.scalar(select(Plan).where(Plan.active == True).order_by(Plan.position.asc()))  # noqa: E712
    company = Company(
        name=data.company_name,
        slug=unique_slug(db, Company, data.company_name),
        plan_id=default_plan.id if default_plan else None,
        created_by=user.id,
    )
    db.add(company)
    db.flush()

    db.add(CompanyMember(company_id=company.id, user_id=user.id, role="owner"))
    db.add(AuditLog(company_id=company.id, user_id=user.id, action="register", entity="companies", entity_id=company.id))
    db.commit()

    return _tokens(user)


@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(AuditLog(user_id=user.id, action="login", entity="users", entity_id=user.id))
    db.commit()
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    return _tokens(user)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user)):
    # Con JWT stateless el logout real lo hace el cliente descartando los
    # tokens. (Fase posterior: lista de revocación en Redis.)
    return None


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(CompanyMember, Company)
        .join(Company, Company.id == CompanyMember.company_id)
        .where(CompanyMember.user_id == user.id)
    ).all()
    companies = [
        MembershipOut(company_id=c.id, company_name=c.name, role=m.role)
        for (m, c) in rows
    ]
    return MeOut(user=UserOut.model_validate(user), companies=companies)
