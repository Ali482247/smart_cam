from __future__ import annotations

import device_pb2


class FakeConnection:
    """A minimal in-memory `NodeConnection` (server/connection/models.py) for tests
    that don't need a real socket."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.remote_address = "fake://" + device_id
        self.sent: list = []
        self.closed = False

    async def send_envelope(self, envelope) -> None:
        self.sent.append(envelope)

    async def close(self) -> None:
        self.closed = True


def make_hello(
    device_name: str = "Test Phone",
    device_slot: int = 1,
    app_instance_id: str = "",
    connection_generation: int = 0,
) -> device_pb2.Hello:
    return device_pb2.Hello(
        device_name=device_name,
        device_slot=device_slot,
        app_instance_id=app_instance_id,
        connection_generation=connection_generation,
    )
