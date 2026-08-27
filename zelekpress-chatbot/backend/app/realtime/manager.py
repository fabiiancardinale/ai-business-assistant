"""Bus de tiempo real en memoria (un solo proceso).

Mantiene colas por conversación (para empujar mensajes al visitante) y por
empresa (para notificar a los agentes conectados). Cuando escalemos a varios
workers, esto se reemplaza por Redis pub/sub SIN cambiar la lógica de negocio
(el servicio solo llama a `to_visitor` / `to_agents`)."""
import asyncio


class ConnectionManager:
    def __init__(self) -> None:
        self._visitor: dict[int, list[asyncio.Queue]] = {}
        self._agents: dict[int, list[asyncio.Queue]] = {}

    # ---- registro / baja ----
    def register_visitor(self, conversation_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._visitor.setdefault(conversation_id, []).append(q)
        return q

    def unregister_visitor(self, conversation_id: int, q: asyncio.Queue) -> None:
        lst = self._visitor.get(conversation_id)
        if lst and q in lst:
            lst.remove(q)
            if not lst:
                self._visitor.pop(conversation_id, None)

    def register_agent(self, company_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._agents.setdefault(company_id, []).append(q)
        return q

    def unregister_agent(self, company_id: int, q: asyncio.Queue) -> None:
        lst = self._agents.get(company_id)
        if lst and q in lst:
            lst.remove(q)
            if not lst:
                self._agents.pop(company_id, None)

    # ---- envío ----
    def to_visitor(self, conversation_id: int, payload: dict) -> None:
        for q in list(self._visitor.get(conversation_id, [])):
            q.put_nowait(payload)

    def to_agents(self, company_id: int, payload: dict) -> None:
        for q in list(self._agents.get(company_id, [])):
            q.put_nowait(payload)


manager = ConnectionManager()
