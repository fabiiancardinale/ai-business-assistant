"""Bandeja de leads del panel del cliente."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.models.lead import Lead

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


class LeadOut(BaseModel):
    id: int
    chatbot_id: int | None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    company_name: str | None = None
    message: str | None = None
    source: str
    status: str
    created_at: str | None = None

    model_config = {"from_attributes": True}


class StatusIn(BaseModel):
    status: str


@router.get("")
def list_leads(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Lead).where(Lead.company_id == tenant.company.id).order_by(desc(Lead.id))
    ).scalars().all()
    return [
        {
            "id": l.id, "chatbot_id": l.chatbot_id, "name": l.name, "email": l.email,
            "phone": l.phone, "whatsapp": l.whatsapp, "company_name": l.company_name,
            "message": l.message, "source": l.source, "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]


@router.patch("/{lead_id}")
def update_lead_status(lead_id: int, data: StatusIn, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead or lead.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    lead.status = data.status
    db.commit()
    return {"ok": True, "status": lead.status}
