"""Knowledge Base: fuentes de conocimiento por chatbot. Scopeado a la
empresa activa + RBAC (admin para escribir, agent+ para ver)."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.core.limits import enforce_limit
from app.models.chatbot import Chatbot
from app.models.knowledge import KnowledgeSource
from app.knowledge.service import process_source, extract_file

router = APIRouter(prefix="/api/v1/chatbots/{chatbot_id}/knowledge", tags=["knowledge"])

ALLOWED_FILE_EXT = (".txt", ".csv", ".md", ".pdf")
MAX_FILE = 5 * 1024 * 1024  # 5 MB


class SourceTextIn(BaseModel):
    type: str = "text"            # text | faq
    name: str
    content: str


class SourceUrlIn(BaseModel):
    name: str
    url: str


class SourceOut(BaseModel):
    id: int
    type: str
    name: str
    url: str | None = None
    status: str
    error: str | None = None
    chunk_count: int
    size: int

    model_config = {"from_attributes": True}


def _bot(db: Session, tenant: TenantContext, chatbot_id: int) -> Chatbot:
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Chatbot no encontrado")
    return bot


def _source(db: Session, tenant: TenantContext, chatbot_id: int, source_id: int) -> KnowledgeSource:
    src = db.get(KnowledgeSource, source_id)
    if not src or src.chatbot_id != chatbot_id or src.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    return src


@router.get("", response_model=list[SourceOut])
def list_sources(chatbot_id: int, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    _bot(db, tenant, chatbot_id)
    rows = db.execute(
        select(KnowledgeSource).where(KnowledgeSource.chatbot_id == chatbot_id).order_by(KnowledgeSource.id.desc())
    ).scalars().all()
    return [SourceOut.model_validate(s) for s in rows]


def _create_and_process(db, tenant, bot, **kwargs) -> KnowledgeSource:
    if not tenant.user.is_platform_admin:
        enforce_limit(db, tenant.company, "knowledge_sources", KnowledgeSource,
                      KnowledgeSource.company_id == tenant.company.id)
    src = KnowledgeSource(company_id=tenant.company.id, chatbot_id=bot.id, **kwargs)
    db.add(src)
    db.commit()
    db.refresh(src)
    process_source(db, src)   # síncrono
    db.refresh(src)
    return src


@router.post("/text", response_model=SourceOut, status_code=201)
def add_text(chatbot_id: int, data: SourceTextIn, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    bot = _bot(db, tenant, chatbot_id)
    if data.type not in ("text", "faq"):
        raise HTTPException(status_code=400, detail="type debe ser text o faq")
    src = _create_and_process(db, tenant, bot, type=data.type, name=data.name, content=data.content)
    return SourceOut.model_validate(src)


@router.post("/url", response_model=SourceOut, status_code=201)
def add_url(chatbot_id: int, data: SourceUrlIn, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    bot = _bot(db, tenant, chatbot_id)
    src = _create_and_process(db, tenant, bot, type="url", name=data.name, url=data.url)
    return SourceOut.model_validate(src)


@router.post("/file", response_model=SourceOut, status_code=201)
def add_file(
    chatbot_id: int,
    name: str = Form(...),
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _bot(db, tenant, chatbot_id)
    fname = (file.filename or "").lower()
    if not fname.endswith(ALLOWED_FILE_EXT):
        raise HTTPException(status_code=400, detail="Formato no permitido (TXT, CSV, MD o PDF)")
    data = file.file.read()
    if len(data) > MAX_FILE:
        raise HTTPException(status_code=413, detail="El archivo supera los 5 MB")
    try:
        text = extract_file(file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ext = fname.rsplit(".", 1)[-1]
    src = _create_and_process(db, tenant, bot, type=(ext if ext in ("csv", "pdf") else "txt"),
                              name=name, content=text)
    return SourceOut.model_validate(src)


@router.post("/{source_id}/reprocess", response_model=SourceOut)
def reprocess(chatbot_id: int, source_id: int, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    src = _source(db, tenant, chatbot_id, source_id)
    process_source(db, src)
    db.refresh(src)
    return SourceOut.model_validate(src)


@router.delete("/{source_id}", status_code=204)
def delete_source(chatbot_id: int, source_id: int, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    src = _source(db, tenant, chatbot_id, source_id)
    db.delete(src)
    db.commit()
    return None
