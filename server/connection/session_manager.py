"""SessionManager: session lifecycle, device_id -> Session mapping, grace-window
resume logic (connection_lifecycle.md §Session recovery).
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import server.protocol  # noqa: F401 - ensures generated/ is on sys.path first
import device_pb2  # noqa: F401

from server.connection.models import Capabilities, ConnectionState, Session, utcnow

GRACE_WINDOW = timedelta(seconds=60)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, device_id: str) -> Session | None:
        return self._sessions.get(device_id)

    def all(self) -> list[Session]:
        return list(self._sessions.values())

    def create_or_resume(self, device_id: str, hello: device_pb2.Hello) -> tuple[Session, bool]:
        """Returns (session, resumed). `resumed` is True iff an existing session within
        the grace window was reused (connection_lifecycle.md §Session recovery); if the
        grace window expired or no prior session exists, a fresh Session/session_id is
        created and `resumed` is False.

        `device_id` is passed explicitly (the caller's resolved identity, i.e.
        Envelope.device_id - see ws_server.py) rather than read from `hello.device_id`,
        so SessionManager's keys always agree with ConnectionManager's regardless of
        whether a client happens to also (redundantly) set Hello.device_id.
        """

        capabilities = Capabilities(
            device_name=hello.device_name,
            manufacturer=hello.manufacturer,
            os_version=hello.os_version,
            device_slot=hello.device_slot,
            device_label=hello.device_label,
            android_id=hello.android_id,
            app_version=hello.app_version,
            app_instance_id=hello.app_instance_id,
            connection_generation=hello.connection_generation,
        )

        existing = self._sessions.get(device_id)
        now = utcnow()
        if existing is not None and existing.disconnected_at is not None:
            if existing.recording or now - existing.disconnected_at <= GRACE_WINDOW:
                existing.capabilities = capabilities
                existing.state = ConnectionState.CONNECTED_IDLE
                existing.disconnected_at = None
                existing.last_seen_at = now
                return existing, True
            # Grace window expired: fall through to a fresh session below.

        session = Session(
            device_id=device_id,
            session_id=str(uuid.uuid4()),
            capabilities=capabilities,
            state=ConnectionState.CONNECTED_IDLE,
        )
        self._sessions[device_id] = session
        return session, False

    def mark_disconnected(self, device_id: str) -> None:
        session = self._sessions.get(device_id)
        if session is None:
            return
        session.disconnected_at = utcnow()
        session.state = ConnectionState.RECONNECTING

    def sweep_expired(self) -> list[str]:
        """Removes sessions whose grace window has expired. Returns the removed
        device_ids (connection_lifecycle.md: an expiry here does NOT delete the node's
        already-recorded footage - see failure_recovery.md's data-loss-prevention
        principle; this only forgets server-side session bookkeeping)."""

        now = utcnow()
        expired = [
            device_id
            for device_id, session in self._sessions.items()
            if (
                session.disconnected_at is not None
                and not session.recording
                and now - session.disconnected_at > GRACE_WINDOW
            )
        ]
        for device_id in expired:
            del self._sessions[device_id]
        return expired

    def update_heartbeat(
        self, device_id: str, *, battery_pct: float, free_storage_bytes: int,
        total_storage_bytes: int, temperature_c: float, recording: bool,
    ) -> None:
        session = self._sessions.get(device_id)
        if session is None:
            return
        session.last_seen_at = utcnow()
        session.heartbeat_suspect = False
        session.battery_pct = battery_pct
        session.free_storage_bytes = free_storage_bytes
        session.total_storage_bytes = total_storage_bytes
        session.temperature_c = temperature_c
        session.recording = recording
