"""Gestión de integraciones desde el panel del cliente (Fase 10):
API keys y webhooks de la empresa activa. Protegido por RBAC (rol admin
para crear/borrar; lectura para el resto). Todo scopeado al tenant."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.core.api_key import generate_key, hash_key
from app.models.api_key import ApiKey
from app.models.webhook import Webhook
from app.models.audit import AuditLog
from app.webhooks.service import deliver_test

router = APIRouter(prefix="/api/v1/integrations", tags=["integraciones"])

# Eventos que la plataforma sabe emitir (se muestran en el panel).
AVAILABLE_EVENTS = ["lead.created", "conversation.created", "human.requested", "conversation.closed"]
VALID_SCOPES = ["read", "write"]


# ---------------------------------------------------------------- API keys ---
class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["read"]


def _key_public(k: ApiKey) -> dict:
    return {
        "id": k.id, "name": k.name, "prefix": k.prefix, "scopes": k.scopes,
        "revoked": k.revoked,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.get("/api-keys")
def list_api_keys(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ApiKey).where(ApiKey.company_id == tenant.company.id).order_by(desc(ApiKey.id))
    ).scalars().all()
    return [_key_public(k) for k in rows]


@router.post("/api-keys", status_code=201)
def create_api_key(data: ApiKeyCreate, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    scopes = [s for s in data.scopes if s in VALID_SCOPES] or ["read"]
    raw, prefix = generate_key()
    k = ApiKey(
        company_id=tenant.company.id, name=data.name.strip() or "API key",
        prefix=prefix, key_hash=hash_key(raw), scopes=scopes,
        created_by=tenant.user.id,
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id, action="create", entity="api_keys", entity_id=k.id))
    db.commit()
    # El valor completo se devuelve UNA sola vez.
    out = _key_public(k)
    out["key"] = raw
    return out


@router.delete("/api-keys/{key_id}", status_code=200)
def revoke_api_key(key_id: int, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    k = db.get(ApiKey, key_id)
    if not k or k.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="API key no encontrada")
    k.revoked = True
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id, action="revoke", entity="api_keys", entity_id=k.id))
    db.commit()
    return {"ok": True, "revoked": True}


# ---------------------------------------------------------------- Webhooks ---
class WebhookCreate(BaseModel):
    url: str
    events: list[str] = []


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None


def _wh_public(w: Webhook) -> dict:
    return {
        "id": w.id, "url": w.url, "events": w.events, "active": w.active,
        "secret": w.secret,  # el cliente lo necesita para verificar la firma
        "last_status": w.last_status, "last_error": w.last_error,
        "last_delivery_at": w.last_delivery_at.isoformat() if w.last_delivery_at else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.get("/webhooks")
def list_webhooks(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Webhook).where(Webhook.company_id == tenant.company.id).order_by(desc(Webhook.id))
    ).scalars().all()
    return {"available_events": AVAILABLE_EVENTS, "webhooks": [_wh_public(w) for w in rows]}


@router.post("/webhooks", status_code=201)
def create_webhook(data: WebhookCreate, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    url = (data.url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="La URL debe empezar con http:// o https://")
    events = [e for e in data.events if e in AVAILABLE_EVENTS]
    w = Webhook(
        company_id=tenant.company.id, url=url, events=events,
        secret=secrets.token_hex(24), active=True,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id, action="create", entity="webhooks", entity_id=w.id))
    db.commit()
    return _wh_public(w)


@router.patch("/webhooks/{wh_id}")
def update_webhook(wh_id: int, data: WebhookUpdate, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    w = db.get(Webhook, wh_id)
    if not w or w.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    if data.url is not None:
        url = data.url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="La URL debe empezar con http:// o https://")
        w.url = url
    if data.events is not None:
        w.events = [e for e in data.events if e in AVAILABLE_EVENTS]
    if data.active is not None:
        w.active = data.active
    db.commit()
    db.refresh(w)
    return _wh_public(w)


@router.delete("/webhooks/{wh_id}", status_code=200)
def delete_webhook(wh_id: int, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    w = db.get(Webhook, wh_id)
    if not w or w.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.post("/webhooks/{wh_id}/test")
def test_webhook(wh_id: int, tenant: TenantContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    w = db.get(Webhook, wh_id)
    if not w or w.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    ok = deliver_test(db, w.id)
    return {"ok": ok, "detail": "Evento de prueba enviado (revisá el estado en unos segundos)."}
