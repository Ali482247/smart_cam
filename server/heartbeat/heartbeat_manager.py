"""HeartbeatManager: 5s heartbeat expectation, 15s SUSPECT / 30s OFFLINE thresholds
(connection_lifecycle.md §Heartbeat/keepalive, §Reconnect policy).

Depends only on ConnectionManager + SessionManager + EventBus (all injected), never on
the WebSocket transport - it reacts to already-decoded Heartbeat payloads handed to it
by whatever transport is in use.
"""

from __future__ import annotations

import asyncio
import logging

import heartbeat_pb2  # noqa: F401

from server.connection.connection_manager import ConnectionManager
from server.connection.models import utcnow
from server.connection.session_manager import SessionManager
from server.events import EventBus
from server.synchronization.clock_sync import ClockOffsetStore

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 5.0
SUSPECT_AFTER_SECONDS = 15.0
OFFLINE_AFTER_SECONDS = 30.0


class HeartbeatManager:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        session_manager: SessionManager,
        event_bus: EventBus,
        clock_offset_store: ClockOffsetStore,
        *,
        check_interval: float = CHECK_INTERVAL_SECONDS,
        suspect_after: float = SUSPECT_AFTER_SECONDS,
        offline_after: float = OFFLINE_AFTER_SECONDS,
    ) -> None:
        self._connection_manager = connection_manager
        self._session_manager = session_manager
        self._event_bus = event_bus
        self._clock_offset_store = clock_offset_store
        self._check_interval = check_interval
        self._suspect_after = suspect_after
        self._offline_after = offline_after
        self._task: asyncio.Task | None = None

    def record_heartbeat(self, device_id: str, heartbeat: heartbeat_pb2.Heartbeat) -> None:
        self._session_manager.update_heartbeat(
            device_id,
            battery_pct=heartbeat.battery_pct,
            free_storage_bytes=heartbeat.free_storage_bytes,
            total_storage_bytes=heartbeat.total_storage_bytes,
            temperature_c=heartbeat.temperature_c,
            recording=heartbeat.recording,
        )
        self._clock_offset_store.record(
            device_id,
            offset_ms=heartbeat.clock_offset_ms,
            uncertainty_ms=heartbeat.clock_uncertainty_ms,
        )
        if heartbeat.last_rtt_ms > 0:
            self._connection_manager.record_rtt(device_id, heartbeat.last_rtt_ms)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._check_interval)
            await self._check_all()

    async def _check_all(self) -> None:
        now = utcnow()
        for device_id in list(self._connection_manager.connected_device_ids()):
            session = self._session_manager.get(device_id)
            if session is None:
                continue
            age = (now - session.last_seen_at).total_seconds()

            if age >= self._offline_after:
                logger.warning(
                    "device_id=%s missed heartbeats for %.0fs -> OFFLINE", device_id, age
                )
                await self._connection_manager.unregister(
                    device_id, lost=False, detail=f"heartbeat timeout {age:.0f}s"
                )
            elif age >= self._suspect_after and not session.heartbeat_suspect:
                session.heartbeat_suspect = True
                logger.info(
                    "device_id=%s missed heartbeats for %.0fs -> SUSPECT", device_id, age
                )

        self._session_manager.sweep_expired()
