"""Shared types for the Connection layer (connection_lifecycle.md).

`NodeConnection` is the interface that decouples ConnectionManager/SessionManager from
the transport implementation (network_architecture.md's strict layering rule: transport
must be replaceable without touching connection/session logic). server/network provides
the concrete WebSocket-backed implementation; tests can provide a fake one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable

import server.protocol  # noqa: F401 - ensures generated/ is on sys.path first
import envelope_pb2  # noqa: F401 - see server/protocol/__init__.py for why this resolves


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConnectionState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    HANDSHAKING = "HANDSHAKING"
    CONNECTED_IDLE = "CONNECTED_IDLE"
    CONNECTED_ACTIVE = "CONNECTED_ACTIVE"
    RECONNECTING = "RECONNECTING"
    SESSION_RECOVERY = "SESSION_RECOVERY"


@runtime_checkable
class NodeConnection(Protocol):
    """What ConnectionManager needs from a transport-level connection object."""

    device_id: str
    remote_address: str

    async def send_envelope(self, envelope: envelope_pb2.Envelope) -> None: ...

    async def close(self) -> None: ...


@dataclass
class Capabilities:
    device_name: str = ""
    manufacturer: str = ""
    os_version: str = ""
    device_slot: int = 0
    device_label: str = ""
    android_id: str = ""
    app_version: str = ""
    # Connection reliability audit §7: app_instance_id is generated fresh per process
    # start (never persisted), so comparing it across Hello messages for the same
    # device_id tells "the same running app reconnecting" apart from "the process was
    # killed and relaunched" - useful diagnostics even though the transport layer's
    # "newest WS connection wins" rule (ConnectionManager.register) already provides the
    # actual safety property regardless of whether the instance changed.
    app_instance_id: str = ""
    connection_generation: int = 0


@dataclass
class Session:
    """Session Layer object (protocol_specification.md §Session Layer fields)."""

    device_id: str
    session_id: str
    capabilities: Capabilities
    state: ConnectionState = ConnectionState.CONNECTED_IDLE
    created_at: datetime = field(default_factory=utcnow)
    last_seen_at: datetime = field(default_factory=utcnow)
    disconnected_at: datetime | None = None
    recording: bool = False
    heartbeat_suspect: bool = False
    battery_pct: float = 0.0
    free_storage_bytes: int = 0
    total_storage_bytes: int = 0
    temperature_c: float = 0.0
