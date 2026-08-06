from __future__ import annotations

import asyncio
import json
import socket

import pytest

from server.discovery.udp_probe import DISCOVERY_MESSAGE, UdpProbeDiscovery


class _FakePhone:
    """Replies to a UDP discovery probe exactly like the Flutter app's UDP responder."""

    def __init__(self, port: int, device_id: str) -> None:
        self._port = port
        self._device_id = device_id
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", port))
        self._sock.setblocking(False)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._sock.close()

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            data, addr = await loop.sock_recvfrom(self._sock, 1024)
            if data.decode("utf-8") == DISCOVERY_MESSAGE:
                reply = json.dumps(
                    {"app": "three_cam", "name": "one", "deviceId": self._device_id, "ip": "127.0.0.1", "port": 8088}
                ).encode("utf-8")
                self._sock.sendto(reply, addr)


@pytest.mark.asyncio
async def test_udp_probe_discovers_fake_phone():
    port = 8291
    phone = _FakePhone(port, "phone-abc")
    phone.start()

    found = []
    discovery = UdpProbeDiscovery(discovery_port=port, probe_interval=0.1)
    discovery.on_node_found(found.append)

    try:
        await discovery.start()
        await asyncio.sleep(0.3)
    finally:
        await discovery.stop()
        await phone.stop()

    device_ids = {node.device_id for node in found}
    assert "phone-abc" in device_ids
    match = next(node for node in found if node.device_id == "phone-abc")
    assert match.ip == "127.0.0.1"
    assert match.port == 8088
