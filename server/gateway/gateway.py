"""Gateway: the single Python interface the Dashboard calls into
(network_architecture.md §Threading Model - no gRPC, no networking code inside
Dashboard).

Owns the asyncio core's event loop on a dedicated background thread. Every public
method here is a plain, synchronous Python call safe to invoke from Tk's thread; each
one bridges to the event loop via `asyncio.run_coroutine_threadsafe` and blocks on the
result, mirroring the pattern `dashboard/three_cam_controller.py` already uses for its
background worker threads (`ControllerApp.run_background` + `root.after`) - Dashboard
code should still dispatch Gateway calls from its own worker threads and marshal
results back to Tk via `root.after`, exactly as it does today for HTTP calls.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any

import scheduler_pb2

from server.connection.connection_manager import ConnectionManager
from server.connection.models import Session
from server.connection.session_manager import SessionManager
from server.discovery.base import NodeInfo
from server.discovery.udp_probe import UdpProbeDiscovery
from server.events import EventBus
from server.heartbeat.heartbeat_manager import HeartbeatManager
from server.network.ws_server import WebSocketServer
from server.scheduler.scheduler import Scheduler, SchedulerResult
from server.synchronization.clock_sync import ClockOffsetStore

logger = logging.getLogger(__name__)

DEFAULT_CALL_TIMEOUT_SECONDS = 5.0


@dataclass
class GatewayConfig:
    ws_host: str = "0.0.0.0"
    ws_port: int = 8088
    discovery_port: int = 8089
    control_port: int = 8088
    probe_interval_seconds: float = 5.0


class Gateway:
    def __init__(self, config: GatewayConfig | None = None) -> None:
        self._config = config or GatewayConfig()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

        self.event_bus = EventBus()
        self._session_manager: SessionManager | None = None
        self._connection_manager: ConnectionManager | None = None
        self._clock_offset_store: ClockOffsetStore | None = None
        self._heartbeat_manager: HeartbeatManager | None = None
        self._scheduler: Scheduler | None = None
        self._discovery: UdpProbeDiscovery | None = None
        self._ws_server: WebSocketServer | None = None
        self._discovered: dict[str, NodeInfo] = {}

    # -- lifecycle -----------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_loop, name="asyncio-core", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=DEFAULT_CALL_TIMEOUT_SECONDS):
            raise RuntimeError("asyncio core failed to start in time")

    def stop(self) -> None:
        if self._loop is None or self._thread is None:
            return

        async def _shutdown() -> None:
            if self._heartbeat_manager is not None:
                await self._heartbeat_manager.stop()
            if self._ws_server is not None:
                await self._ws_server.stop()
            if self._discovery is not None:
                await self._discovery.stop()

        future = asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
        future.result(timeout=DEFAULT_CALL_TIMEOUT_SECONDS)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=DEFAULT_CALL_TIMEOUT_SECONDS)
        self._thread = None
        self._loop = None
        self._ready.clear()

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        loop.run_until_complete(self._async_init())
        self._ready.set()
        loop.run_forever()

    async def _async_init(self) -> None:
        self._session_manager = SessionManager()
        self._connection_manager = ConnectionManager(self._session_manager, self.event_bus)
        self._clock_offset_store = ClockOffsetStore()
        self._heartbeat_manager = HeartbeatManager(
            self._connection_manager, self._session_manager, self.event_bus, self._clock_offset_store
        )
        self._scheduler = Scheduler(self._connection_manager, self._clock_offset_store)
        self._discovery = UdpProbeDiscovery(
            discovery_port=self._config.discovery_port,
            control_port=self._config.control_port,
            probe_interval=self._config.probe_interval_seconds,
        )
        self._discovery.on_node_found(self._on_node_found)
        self._ws_server = WebSocketServer(
            self._connection_manager, self._heartbeat_manager, self._scheduler, self.event_bus,
            host=self._config.ws_host, port=self._config.ws_port,
        )

        self._heartbeat_manager.start()
        await self._ws_server.start()
        await self._discovery.start()

    def _on_node_found(self, node: NodeInfo) -> None:
        self._discovered[node.device_id] = node

    # -- synchronous Dashboard-facing API -------------------------------------------

    def _call(self, coroutine_factory, *, timeout: float = DEFAULT_CALL_TIMEOUT_SECONDS) -> Any:
        if self._loop is None:
            raise RuntimeError("Gateway.start() must be called first")
        future = asyncio.run_coroutine_threadsafe(coroutine_factory(), self._loop)
        return future.result(timeout=timeout)

    def start_recording(
        self, *, camera_name: str = "", session_label: str = "", record_index: int = 0,
        targets: list[str] | None = None,
    ) -> SchedulerResult:
        async def action() -> SchedulerResult:
            return await self._scheduler.schedule_command(
                scheduler_pb2.ScheduledCommand.START, camera_name=camera_name,
                session_label=session_label, record_index=record_index, targets=targets,
            )

        return self._call(action)

    def stop_recording(
        self, *, camera_name: str = "", targets: list[str] | None = None,
    ) -> SchedulerResult:
        async def action() -> SchedulerResult:
            return await self._scheduler.schedule_command(
                scheduler_pb2.ScheduledCommand.STOP, camera_name=camera_name, targets=targets,
            )

        return self._call(action)

    def list_sessions(self) -> list[Session]:
        async def action() -> list[Session]:
            return self._session_manager.all()

        return self._call(action)

    def connected_device_ids(self) -> list[str]:
        async def action() -> list[str]:
            return self._connection_manager.connected_device_ids()

        return self._call(action)

    def list_discovered_devices(self) -> list[NodeInfo]:
        async def action() -> list[NodeInfo]:
            return list(self._discovered.values())

        return self._call(action)
