"""WebSockets de tiempo real.

- Visitante: /api/v1/public/ws/{token}  -> recibe en vivo las respuestas del
  bot y de los agentes (canal de push; el visitante envía por REST).
- Agente:    /api/v1/ws/agent?token=JWT&company_id=X -> recibe notificaciones
  de mensajes de visitantes y pedidos de humano.

Cada socket lee de su cola (manager) y reenvía al cliente. Un task paralelo
detecta la desconexión."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import decode_token
from app.models.conversation import Conversation
from app.models.company import CompanyMember
from app.models.user import User
from app.realtime.manager import manager

router = APIRouter()


async def _pump(ws: WebSocket, queue: asyncio.Queue) -> None:
    """Envía al cliente todo lo que llega a su cola."""
    while True:
        payload = await queue.get()
        await ws.send_json(payload)


async def _drain(ws: WebSocket) -> None:
    """Lee (y descarta) lo que mande el cliente; sirve para detectar cierre."""
    while True:
        await ws.receive_text()


@router.websocket("/api/v1/public/ws/{token}")
async def visitor_ws(ws: WebSocket, token: str):
    # Resolver conversación por token (consulta corta y sincrónica).
    db = SessionLocal()
    try:
        conv = db.scalar(select(Conversation).where(Conversation.token == token))
        conv_id = conv.id if conv else None
    finally:
        db.close()

    if not conv_id:
        await ws.close(code=4404)
        return

    await ws.accept()
    queue = manager.register_visitor(conv_id)
    try:
        await asyncio.wait(
            {asyncio.create_task(_pump(ws, queue)), asyncio.create_task(_drain(ws))},
            return_when=asyncio.FIRST_COMPLETED,
        )
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister_visitor(conv_id, queue)


@router.websocket("/api/v1/ws/agent")
async def agent_ws(ws: WebSocket, token: str = "", company_id: int = 0):
    # Autenticación por query param (?token=JWT&company_id=X).
    payload = decode_token(token, expected_type="access")
    if not payload:
        await ws.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            await ws.close(code=4401)
            return
        if not user.is_platform_admin:
            member = db.scalar(select(CompanyMember).where(
                CompanyMember.company_id == company_id, CompanyMember.user_id == user.id))
            if not member:
                await ws.close(code=4403)
                return
    finally:
        db.close()

    await ws.accept()
    queue = manager.register_agent(company_id)
    try:
        await asyncio.wait(
            {asyncio.create_task(_pump(ws, queue)), asyncio.create_task(_drain(ws))},
            return_when=asyncio.FIRST_COMPLETED,
        )
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister_agent(company_id, queue)
