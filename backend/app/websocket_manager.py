import json
import asyncio
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
