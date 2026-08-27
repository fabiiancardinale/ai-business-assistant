"""Analytics del panel del cliente: métricas agregadas, serie temporal y
preguntas sin respuesta (con acción para sumarlas a la Knowledge Base)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.models.analytics import UnansweredQuestion
from app.models.knowledge import KnowledgeSource
from app.knowledge.service import process_source
from app.billing.usage_service import summary as usage_summary

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/usage")
def get_usage(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    """Uso del período actual vs. los límites del plan de la empresa."""
    return usage_summary(db, tenant.company)


def _count(db, model, *where):
    stmt = select(func.count()).select_from(model)
    for w in where:
        stmt = stmt.where(w)
    return db.scalar(stmt) or 0


@router.get("/overview")
def overview(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    cid = tenant.company.id
    return {
        "conversations": _count(db, Conversation, Conversation.company_id == cid),
        "conversations_open": _count(db, Conversation, Conversation.company_id == cid, Conversation.status.in_(["ai", "human", "pending", "open"])),
        "conversations_closed": _count(db, Conversation, Conversation.company_id == cid, Conversation.status == "closed"),
        "human_requests": _count(db, Conversation, Conversation.company_id == cid, Conversation.human_requested == True),  # noqa: E712
        "messages": _count(db, Message, Message.company_id == cid),
        "leads": _count(db, Lead, Lead.company_id == cid),
        "unanswered": _count(db, UnansweredQuestion, UnansweredQuestion.company_id == cid, UnansweredQuestion.resolved == False),  # noqa: E712
    }


@router.get("/timeseries")
def timeseries(days: int = 14, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    """Conversaciones y leads por día en los últimos `days` días."""
    cid = tenant.company.id
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))

    def by_day(model):
        rows = db.execute(
            select(func.date(model.created_at).label("d"), func.count().label("n"))
            .where(model.company_id == cid, model.created_at >= since)
            .group_by(func.date(model.created_at))
        ).all()
        return {str(r.d): r.n for r in rows}

    conv = by_day(Conversation)
    leads = by_day(Lead)
    # armar serie continua de fechas
    out = []
    for i in range(max(1, min(days, 90)), -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
        out.append({"date": d, "conversations": conv.get(d, 0), "leads": leads.get(d, 0)})
    return out


@router.get("/unanswered")
def unanswered(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(UnansweredQuestion)
        .where(UnansweredQuestion.company_id == tenant.company.id, UnansweredQuestion.resolved == False)  # noqa: E712
        .order_by(desc(UnansweredQuestion.count), desc(UnansweredQuestion.updated_at))
    ).scalars().all()
    return [
        {"id": u.id, "chatbot_id": u.chatbot_id, "question": u.question, "count": u.count,
         "last_seen": u.updated_at.isoformat() if u.updated_at else None}
        for u in rows
    ]


@router.post("/unanswered/{uq_id}/add-to-knowledge")
def add_to_knowledge(uq_id: int, data: dict, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Convierte una pregunta sin respuesta en una fuente de conocimiento
    (con la respuesta que provee el cliente) y la marca como resuelta."""
    uq = db.get(UnansweredQuestion, uq_id)
    if not uq or uq.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="No encontrada")
    answer = (data.get("answer") or "").strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Falta la respuesta")

    content = f"Pregunta: {uq.question}\nRespuesta: {answer}"
    src = KnowledgeSource(company_id=uq.company_id, chatbot_id=uq.chatbot_id,
                          type="faq", name=f"FAQ: {uq.question[:60]}", content=content)
    db.add(src)
    db.commit()
    db.refresh(src)
    process_source(db, src)

    uq.resolved = True
    db.commit()
    return {"ok": True, "source_id": src.id}


@router.post("/unanswered/{uq_id}/dismiss")
def dismiss(uq_id: int, tenant: TenantContext = Depends(require_role("agent")), db: Session = Depends(get_db)):
    uq = db.get(UnansweredQuestion, uq_id)
    if not uq or uq.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="No encontrada")
    uq.resolved = True
    db.commit()
    return {"ok": True}
