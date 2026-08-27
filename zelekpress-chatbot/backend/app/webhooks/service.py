"""Servicio de webhooks: entrega eventos a las URLs configuradas por cada
empresa, firmados con HMAC-SHA256.

Diseño:
- `dispatch(db, company_id, event, payload)` se llama dentro del request.
  Lee (en la sesión actual) los webhooks activos suscritos al evento y
  dispara la entrega en un hilo aparte, para NO bloquear la respuesta al
  visitante. El hilo abre su propia sesión de base de datos.
- La entrega es best-effort con timeout corto; nunca rompe el flujo del
  request aunque el endpoint del cliente esté caído. Se guarda el estado de
  la última entrega (código HTTP o error) para diagnóstico en el panel.

Para escalar/reintentar de verdad se cambia este hilo por una cola (RQ/
Celery sobre Redis) sin tocar los llamadores.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.webhook import Webhook

TIMEOUT_SECONDS = 6


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _deliver(webhook_id: int, event: str, body: bytes, signature: str) -> None:
    """Corre en un hilo aparte, con su propia sesión de base de datos."""
    try:
        import requests  # import local para no acoplar el arranque
    except Exception:
        return

    db = SessionLocal()
    try:
        wh = db.get(Webhook, webhook_id)
        if not wh or not wh.active:
            return
        status_code: int | None = None
        error: str | None = None
        try:
            resp = requests.post(
                wh.url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Zelekpress-Webhooks/1.0",
                    "X-Zelekpress-Event": event,
                    "X-Zelekpress-Signature": signature,
                },
                timeout=TIMEOUT_SECONDS,
            )
            status_code = resp.status_code
        except Exception as e:  # noqa: BLE001
            error = str(e)[:500]

        wh.last_status = status_code
        wh.last_error = error
        wh.last_delivery_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _envelope(event: str, payload: dict) -> dict:
    return {
        "event": event,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }


def dispatch(db, company_id: int, event: str, payload: dict) -> int:
    """Encola la entrega del evento a todos los webhooks activos de la empresa
    suscritos a ese evento. Devuelve cuántos webhooks se dispararon.

    Nunca lanza excepción hacia el llamador (best-effort)."""
    try:
        rows = db.execute(
            select(Webhook).where(Webhook.company_id == company_id, Webhook.active == True)  # noqa: E712
        ).scalars().all()
    except Exception:
        return 0

    body_dict = _envelope(event, payload)
    body = json.dumps(body_dict, ensure_ascii=False, default=str).encode("utf-8")

    fired = 0
    for wh in rows:
        events = wh.events or []
        if event not in events and "*" not in events:
            continue
        signature = sign(wh.secret, body)
        threading.Thread(
            target=_deliver, args=(wh.id, event, body, signature), daemon=True
        ).start()
        fired += 1
    return fired


def deliver_test(db, webhook_id: int) -> bool:
    """Envía un evento de prueba a un webhook puntual (para el botón 'Probar'
    del panel). Devuelve si se disparó."""
    wh = db.get(Webhook, webhook_id)
    if not wh:
        return False
    body = json.dumps(
        _envelope("ping", {"message": "Webhook de prueba de Zelekpress"}),
        ensure_ascii=False,
    ).encode("utf-8")
    signature = sign(wh.secret, body)
    threading.Thread(
        target=_deliver, args=(wh.id, "ping", body, signature), daemon=True
    ).start()
    return True
