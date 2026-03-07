import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from starlette.websockets import WebSocket


@dataclass(frozen=True)
class ConnectionInfo:
    user_id: int
    role: str
    connected_at: float


class RealtimeManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: dict[WebSocket, ConnectionInfo] = {}

    async def connect(self, websocket: WebSocket, info: ConnectionInfo) -> None:
        async with self._lock:
            self._connections[websocket] = info

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, event: dict[str, Any]) -> None:
        """
        Broadcast an event to all connected clients.

        This is intentionally broad for Phase 1 ("invalidate_all").
        We can add role/entity scoping later without changing callers.
        """
        payload = json.dumps(event, default=str)
        async with self._lock:
            items = list(self._connections.items())

        if not items:
            return

        entity = str(event.get("entity") or "").lower()
        public_allowlist = {
            "tournaments",
            "competitions",
            "teams",
            "players",
            "matches",
            "standings",
            "news",
        }

        async def _send(ws: WebSocket) -> None:
            try:
                await ws.send_text(payload)
            except Exception:
                await self.disconnect(ws)

        tasks: list[asyncio.Task[None]] = []
        for ws, info in items:
            if info.role.upper() == "PUBLIC":
                # Never leak admin/private streams to unauthenticated clients.
                if entity and entity not in public_allowlist:
                    continue
            tasks.append(asyncio.create_task(_send(ws)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def ping_all(self) -> None:
        await self.broadcast({"type": "ping", "ts": int(time.time())})

    def connection_count(self) -> int:
        return len(self._connections)


realtime_manager = RealtimeManager()

