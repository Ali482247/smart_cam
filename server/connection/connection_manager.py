"""ConnectionManager: connection pool, send()/broadcast(), the one-active-session-per-
device invariant, and per-node RTT metrics (connection_lifecycle.md, network_architecture
.md §Layer Catalogue).

Depends only on the NodeConnection interface (models.py) and SessionManager/EventBus,
injected via the constructor - never imports server/network directly, so the transport
implementation stays swappable (strict layering rule).
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

import server.protocol  # noqa: F401 - ensures generated/ is on sys.path first
import device_pb2  # noqa: F401
from envelope_pb2 import Envelope

from server.connection.models import NodeConnection
from server.connection.session_manager import SessionManager
from server.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)

RTT_SAMPLE_WINDOW = 20


class ConnectionManager:
    def __init__(self, session_manager: SessionManager, event_bus: EventBus) -> None:
        self._session_manager = session_manager
        self._event_bus = event_bus
        self._connections: dict[str, NodeConnection] = {}
        self._rtt_samples: dict[str, deque[float]] = {}

    def connected_device_ids(self) -> list[str]:
        return list(self._connections.keys())

    def is_connected(self, device_id: str) -> bool:
        return device_id in self._connections

    async def register(self, connection: NodeConnection, hello: device_pb2.Hello) -> tuple:
        """Enforces "one active session per deviceId" (connection_lifecycle.md): if a
        live connection already exists for this device_id, the OLDER one is closed -
        newest connection wins. Returns (session, resumed).
        """

        existing = self._connections.get(connection.device_id)
        if existing is not None and existing is not connection:
            previous_session = self._session_manager.get(connection.device_id)
            same_instance = bool(
                previous_session
                and previous_session.capabilities.app_instance_id
                and previous_session.capabilities.app_instance_id == hello.app_instance_id
            )
            logger.warning(
                "device_id=%s already had a live connection; closing the older one "
                "(same_app_instance=%s, new_generation=%s)",
                connection.device_id, same_instance, hello.connection_generation,
            )
            await existing.close()

        session, resumed = self._session_manager.create_or_resume(connection.device_id, hello)
        self._connections[connection.device_id] = connection
        self._rtt_samples.setdefault(connection.device_id, deque(maxlen=RTT_SAMPLE_WINDOW))
        self._event_bus.emit(Event(EventType.DEVICE_CONNECTED, connection.device_id))
        return session, resumed

    async def unregister(self, device_id: str, *, lost: bool = False, detail: str = "") -> None:
        connection = self._connections.pop(device_id, None)
        if connection is None:
            return
        self._session_manager.mark_disconnected(device_id)
        self._event_bus.emit(
            Event(
                EventType.CONNECTION_LOST if lost else EventType.DEVICE_DISCONNECTED,
                device_id,
                detail=detail,
            )
        )

    async def send(self, device_id: str, envelope: Envelope) -> bool:
        connection = self._connections.get(device_id)
        if connection is None:
            return False
        try:
            await connection.send_envelope(envelope)
            return True
        except Exception:  # noqa: BLE001 - a send failure means the connection is dead
            logger.exception("send to device_id=%s failed; unregistering", device_id)
            await self.unregister(device_id, lost=True)
            return False

    async def broadcast(
        self, envelope: Envelope, device_ids: list[str] | None = None
    ) -> dict[str, bool]:
        targets = device_ids if device_ids is not None else self.connected_device_ids()
        results = await asyncio.gather(*(self.send(device_id, envelope) for device_id in targets))
        return dict(zip(targets, results))

    def record_rtt(self, device_id: str, rtt_ms: float) -> None:
        self._rtt_samples.setdefault(device_id, deque(maxlen=RTT_SAMPLE_WINDOW)).append(rtt_ms)

    def rtt_p99(self, device_id: str) -> float | None:
        samples = self._rtt_samples.get(device_id)
        if not samples:
            return None
        ordered = sorted(samples)
        index = min(len(ordered) - 1, int(len(ordered) * 0.99))
        return ordered[index]
