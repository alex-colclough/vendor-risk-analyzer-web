"""WebSocket connection manager."""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.models.responses import WebSocketEvent, WebSocketEventType


class ConnectionManager:
    """Manages WebSocket connections with session isolation."""

    def __init__(self):
        # session_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}
        # connection_id -> session_id mapping
        self.connection_sessions: dict[int, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            self.active_connections[session_id].append(websocket)
            self.connection_sessions[id(websocket)] = session_id

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            conn_id = id(websocket)
            session_id = self.connection_sessions.pop(conn_id, None)

            if session_id and session_id in self.active_connections:
                try:
                    self.active_connections[session_id].remove(websocket)
                except ValueError:
                    pass  # Already removed

                # Clean up empty session
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]

    async def send_to_session(
        self,
        session_id: str,
        event: WebSocketEvent,
    ) -> None:
        """Send event to all connections in a session."""
        connections = self.active_connections.get(session_id, [])
        if not connections:
            return

        message = event.model_dump_json()
        disconnected = []

        for connection in connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.append(connection)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            await self.disconnect(conn)

    async def send_to_connection(
        self,
        websocket: WebSocket,
        event: WebSocketEvent,
    ) -> None:
        """Send event to a specific connection."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(event.model_dump_json())
        except Exception:
            await self.disconnect(websocket)

    async def broadcast(self, event: WebSocketEvent) -> None:
        """Broadcast event to all connected sessions."""
        for session_id in list(self.active_connections.keys()):
            await self.send_to_session(session_id, event)

    def get_session_connection_count(self, session_id: str) -> int:
        """Get number of active connections for a session."""
        return len(self.active_connections.get(session_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(
            len(conns) for conns in self.active_connections.values()
        )


class ProgressEmitter:
    """Helper class for emitting progress events during analysis."""

    def __init__(
        self,
        manager: ConnectionManager,
        session_id: str,
        total_steps: int = 100,
    ):
        self.manager = manager
        self.session_id = session_id
        self.total_steps = total_steps
        self.current_step = 0

    async def emit(
        self,
        event_type: WebSocketEventType,
        message: str,
        data: Optional[dict[str, Any]] = None,
        progress_override: Optional[float] = None,
    ) -> None:
        """Emit a progress event."""
        progress = progress_override
        if progress is None:
            progress = (self.current_step / self.total_steps) * 100

        event = WebSocketEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data or {},
            progress_percentage=min(progress, 100),
            message=message,
        )

        await self.manager.send_to_session(self.session_id, event)

    async def increment(self, steps: int = 1) -> None:
        """Increment the current step count."""
        self.current_step = min(self.current_step + steps, self.total_steps)

    async def set_progress(self, progress: float) -> None:
        """Set progress directly as percentage."""
        self.current_step = int((progress / 100) * self.total_steps)


# Global connection manager
manager = ConnectionManager()
