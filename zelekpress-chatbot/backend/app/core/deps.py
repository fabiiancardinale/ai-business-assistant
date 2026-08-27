"""Dependencias de FastAPI: usuario actual, empresa activa (tenant) y RBAC.
Toda autorización se resuelve acá, en backend — nunca se confía en el
frontend ni en headers arbitrarios para permisos."""
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.company import Company, CompanyMember

bearer = HTTPBearer(auto_error=False)

# Jerarquía de roles para comparaciones "rol mínimo requerido".
ROLE_RANK = {"viewer": 0, "agent": 1, "admin": 2, "owner": 3}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    payload = decode_token(creds.credentials, expected_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    return user


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Solo el Super Admin de Zelekpress."""
    if not user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Requiere Super Admin de la plataforma")
    return user


class TenantContext:
    """Empresa activa + rol del usuario en ella."""
    def __init__(self, user: User, company: Company, role: str):
        self.user = user
        self.company = company
        self.role = role

    def can(self, min_role: str) -> bool:
        return ROLE_RANK.get(self.role, -1) >= ROLE_RANK.get(min_role, 99)


def get_tenant(
    x_company_id: int | None = Header(default=None, alias="X-Company-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Resuelve la empresa activa desde el header X-Company-Id y valida que
    el usuario sea miembro. El company_id se VALIDA contra la membresía —
    nunca se confía en el valor a ciegas."""
    if x_company_id is None:
        raise HTTPException(status_code=400, detail="Falta X-Company-Id")

    company = db.get(Company, x_company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # El Super Admin puede entrar a cualquier empresa; el resto debe ser miembro.
    if user.is_platform_admin:
        role = "owner"
    else:
        member = db.scalar(
            select(CompanyMember).where(
                CompanyMember.company_id == company.id,
                CompanyMember.user_id == user.id,
            )
        )
        if not member:
            raise HTTPException(status_code=403, detail="No pertenecés a esta empresa")
        role = member.role

    if company.status != "active" and not user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Empresa suspendida")

    return TenantContext(user=user, company=company, role=role)


def require_role(min_role: str):
    """Dependencia factory: exige un rol mínimo en la empresa activa."""
    def _dep(tenant: TenantContext = Depends(get_tenant)) -> TenantContext:
        if not tenant.can(min_role):
            raise HTTPException(status_code=403, detail=f"Requiere rol {min_role} o superior")
        return tenant
    return _dep
