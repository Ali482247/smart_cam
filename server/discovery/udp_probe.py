"""UdpProbeDiscovery: the current, already-working mechanism (PC broadcasts
THREE_CAM_DISCOVER, phones reply unicast with a JSON status blob), ported as-is behind
the DiscoveryProvider interface - kept for Phase 1 per network_architecture.md
§Discovery Layer (mDNS is additive, Phase 3, not a replacement).

Wire format is unchanged from dashboard/three_cam_controller.py's discover_phones() /
mobile/three_cam_mobile/lib/main.dart's UDP responder, so existing phones need no update
for the server side of discovery to be re-implemented here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket

from server.discovery.base import NodeFoundCallback, NodeInfo

logger = logging.getLogger(__name__)

DISCOVERY_MESSAGE = "THREE_CAM_DISCOVER"
DEFAULT_DISCOVERY_PORT = 8089
DEFAULT_CONTROL_PORT = 8088
DEFAULT_PROBE_INTERVAL_SECONDS = 5.0


def local_broadcast_addresses() -> list[str]:
    addresses = {"255.255.255.255"}
    hostname = socket.gethostname()
    try:
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = item[4][0]
            if ip.startswith("127."):
                continue
            parts = ip.split(".")
            if len(parts) == 4:
                addresses.add(".".join(parts[:3] + ["255"]))
    except socket.gaierror:
        pass
    return sorted(addresses)


class _ReplyProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler) -> None:
        self._handler = handler

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._handler(data, addr)

    def error_received(self, exc: Exception) -> None:
        logger.debug("UDP discovery socket error: %s", exc)


class UdpProbeDiscovery:
    def __init__(
        self,
        *,
        discovery_port: int = DEFAULT_DISCOVERY_PORT,
        control_port: int = DEFAULT_CONTROL_PORT,
        probe_interval: float = DEFAULT_PROBE_INTERVAL_SECONDS,
    ) -> None:
        self._discovery_port = discovery_port
        self._control_port = control_port
        self._probe_interval = probe_interval
        self._callbacks: list[NodeFoundCallback] = []
        self._transport: asyncio.DatagramTransport | None = None
        self._probe_task: asyncio.Task | None = None

    def on_node_found(self, callback: NodeFoundCallback) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _ReplyProtocol(self._handle_reply),
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        self._probe_task = asyncio.create_task(self._probe_loop())
        logger.info(
            "UdpProbeDiscovery started (broadcast port %s, control port %s)",
            self._discovery_port, self._control_port,
        )

    async def stop(self) -> None:
        if self._probe_task is not None:
            self._probe_task.cancel()
            try:
                await self._probe_task
            except asyncio.CancelledError:
                pass
            self._probe_task = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def _probe_loop(self) -> None:
        while True:
            self._send_probe()
            await asyncio.sleep(self._probe_interval)

    def _send_probe(self) -> None:
        if self._transport is None:
            return
        message = DISCOVERY_MESSAGE.encode("utf-8")
        for address in local_broadcast_addresses():
            try:
                self._transport.sendto(message, (address, self._discovery_port))
            except OSError as error:
                logger.debug("broadcast to %s failed: %s", address, error)

    def _handle_reply(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            payload = json.loads(data.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return
        if payload.get("app") != "three_cam":
            return

        ip = str(payload.get("ip") or addr[0])
        port = int(payload.get("port") or self._control_port)
        device_id = str(payload.get("deviceId") or payload.get("device_id") or f"{ip}:{port}")
        name = str(payload.get("name") or device_id)
        node = NodeInfo(device_id=device_id, name=name, ip=ip, port=port, raw=payload)

        for callback in self._callbacks:
            callback(node)
