import json
from typing import Dict, Set, Optional
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections grouped by bus_id for live GPS tracking."""

    def __init__(self):
        # bus_id → set of WebSocket connections watching that bus
        self._bus_connections: Dict[str, Set[WebSocket]] = {}
        # Connections subscribed to ALL buses (no filter)
        self._all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, bus_id: Optional[str] = None):
        await websocket.accept()
        if bus_id:
            if bus_id not in self._bus_connections:
                self._bus_connections[bus_id] = set()
            self._bus_connections[bus_id].add(websocket)
        else:
            self._all_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, bus_id: Optional[str] = None):
        if bus_id and bus_id in self._bus_connections:
            self._bus_connections[bus_id].discard(websocket)
        else:
            self._all_connections.discard(websocket)

    async def broadcast_to_bus(self, bus_id: str, data: dict):
        """Send a JSON payload to all clients watching the given bus."""
        message = json.dumps(data)
        dead: Set[WebSocket] = set()

        for ws in self._bus_connections.get(bus_id, set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in self._all_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            self._bus_connections.get(bus_id, set()).discard(ws)
            self._all_connections.discard(ws)

    async def broadcast_all(self, data: dict):
        """Send a JSON payload to every connected client."""
        message = json.dumps(data)
        dead: Set[WebSocket] = set()

        all_ws = set()
        for connections in self._bus_connections.values():
            all_ws.update(connections)
        all_ws.update(self._all_connections)

        for ws in all_ws:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            for connections in self._bus_connections.values():
                connections.discard(ws)
            self._all_connections.discard(ws)


connection_manager = ConnectionManager()
