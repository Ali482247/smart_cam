"""DiscoveryProvider interface (network_architecture.md §Discovery Layer: interface,
not a fixed mechanism). UdpProbeDiscovery (udp_probe.py) is the only implementation in
Phase 1; a future MdnsDiscovery can run alongside it without ConnectionManager/Gateway
changing at all - they only ever see `NodeInfo` events through this interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass(frozen=True)
class NodeInfo:
    device_id: str
    name: str
    ip: str
    port: int
    raw: dict = field(default_factory=dict)


NodeFoundCallback = Callable[[NodeInfo], None]


class DiscoveryProvider(Protocol):
    def on_node_found(self, callback: NodeFoundCallback) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...
