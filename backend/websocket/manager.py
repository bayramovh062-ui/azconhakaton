"""WebSocket connection manager for fleet broadcasts."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send JSON to every connected client; prune dead sockets."""
        payload = json.dumps(message, default=str)
        async with self._lock:
            sockets = list(self.active_connections)

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)


# Module-level singleton — imported by main.py and the broadcaster task.
manager = ConnectionManager()
