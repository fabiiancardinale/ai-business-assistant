"""Autenticación por API Key para la API pública de la plataforma.

Formato de la key:  zk_live_<prefix8>_<secret32>
- Guardamos en la base SOLO el sha256 de la key completa y el `prefix`
  (para poder buscarla sin exponer el secreto).
- El valor completo se muestra UNA sola vez al crearla.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.api_key import ApiKey
from app.models.company import Company

KEY_PREFIX = "zk_live_"


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_key() -> tuple[str, str]:
    """Devuelve (key_completa, prefix_publico). El prefix es lo único que se
    guarda legible; el resto solo como hash."""
    pub = secrets.token_hex(4)               # 8 chars visibles
    sec = secrets.token_urlsafe(24)          # secreto
    raw = f"{KEY_PREFIX}{pub}_{sec}"
    prefix = f"{KEY_PREFIX}{pub}"
    return raw, prefix


class ApiContext:
    """Contexto de una request autenticada por API key."""
    def __init__(self, company: Company, api_key: ApiKey):
        self.company = company
        self.api_key = api_key

    def has_scope(self, scope: str) -> bool:
        scopes = self.api_key.scopes or []
        return scope in scopes


def _extract_key(authorization: str | None, x_api_key: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    return None


def get_api_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    db: Session = Depends(get_db),
) -> ApiContext:
    raw = _extract_key(authorization, x_api_key)
    if not raw or not raw.startswith(KEY_PREFIX):
        raise HTTPException(status_code=401, detail="Falta la API key (header Authorization: Bearer zk_live_... o X-Api-Key)")

    # El prefix es zk_live_<8 chars> => primeros 16 chars del total.
    prefix = raw.split("_")[0:3]
    prefix = "_".join(prefix)  # "zk_live_xxxxxxxx"
    row = db.scalar(select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.revoked == False))  # noqa: E712
    if not row or row.key_hash != hash_key(raw):
        raise HTTPException(status_code=401, detail="API key inválida o revocada")

    company = db.get(Company, row.company_id)
    if not company or company.status != "active":
        raise HTTPException(status_code=403, detail="Empresa no disponible")

    # Marcar uso (best-effort, no rompe si falla).
    try:
        row.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    return ApiContext(company=company, api_key=row)


def require_scope(scope: str):
    """Dependencia factory: exige un scope en la API key."""
    def _dep(ctx: ApiContext = Depends(get_api_context)) -> ApiContext:
        if not ctx.has_scope(scope):
            raise HTTPException(status_code=403, detail=f"La API key no tiene el permiso '{scope}'")
        return ctx
    return _dep
