"""Clock synchronization (clock_synchronization.md).

Two responsibilities live here, matching who actually observes each timestamp:

- `respond_to_request`: the server's half of the NTP-style exchange - stateless, just
  timestamps its own receipt/send of a ClockSyncReply. The *node* computes t3 and the
  resulting offset locally (it's the only side that has all four timestamps).
- `ClockOffsetStore`: the server-side record of each node's self-reported offset/
  uncertainty (carried on every Heartbeat, see protocol/heartbeat.proto), which is what
  the Scheduler (scheduler.md) reads when computing lead time.

`compute_offset` is the same NTP formula the node applies; kept here too so the formula
is unit-tested against the docs in one place and reusable if the server ever needs to
run the identical calculation (e.g. a future server-initiated sync mode).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import scheduler_pb2  # noqa: F401
import server.protocol  # noqa: F401 - ensures generated/ is on sys.path first


def server_now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class OffsetSample:
    offset_ms: float
    rtt_ms: float


def compute_offset(t0_ms: int, t1_ms: int, t2_ms: int, t3_ms: int) -> OffsetSample:
    """NTP-style 4-timestamp exchange (clock_synchronization.md §Exchange algorithm).

    t0: node's local send time. t1: server receive time. t2: server send time.
    t3: node's local receive time.
    """

    rtt_ms = (t3_ms - t0_ms) - (t2_ms - t1_ms)
    offset_ms = ((t1_ms - t0_ms) + (t2_ms - t3_ms)) / 2
    return OffsetSample(offset_ms=offset_ms, rtt_ms=rtt_ms)


def reject_outliers(samples: list[OffsetSample]) -> list[OffsetSample]:
    """Drops samples whose RTT exceeds 1.5x the median RTT of the batch
    (clock_synchronization.md §Sampling strategy)."""

    if not samples:
        return []
    rtts = sorted(sample.rtt_ms for sample in samples)
    median_rtt = rtts[len(rtts) // 2]
    threshold = median_rtt * 1.5
    return [sample for sample in samples if sample.rtt_ms <= threshold]


def average_offset(samples: list[OffsetSample]) -> float:
    if not samples:
        return 0.0
    return sum(sample.offset_ms for sample in samples) / len(samples)


def offset_uncertainty(samples: list[OffsetSample]) -> float:
    """Half the spread between max/min offset in the retained sample set."""

    if not samples:
        return 0.0
    offsets = [sample.offset_ms for sample in samples]
    return (max(offsets) - min(offsets)) / 2


def respond_to_request(request: "scheduler_pb2.ClockSyncRequest") -> "scheduler_pb2.ClockSyncReply":
    t1_ms = server_now_ms()
    t2_ms = server_now_ms()
    return scheduler_pb2.ClockSyncReply(t0_ms=request.t0_ms, t1_ms=t1_ms, t2_ms=t2_ms)


@dataclass
class NodeOffsetState:
    offset_ms: float = 0.0
    uncertainty_ms: float = float("inf")
    updated_at_ms: int = 0


class ClockOffsetStore:
    """Server-side record of each node's self-reported offset/uncertainty, fed by
    Heartbeat payloads (see HeartbeatManager). `uncertainty_ms` defaults to +inf for an
    unmeasured node so the Scheduler treats it as "exclude, data missing" rather than
    silently trusting an offset of 0 (scheduler.md §Algorithm step 3)."""

    def __init__(self) -> None:
        self._state: dict[str, NodeOffsetState] = {}

    def record(self, device_id: str, *, offset_ms: float, uncertainty_ms: float) -> None:
        self._state[device_id] = NodeOffsetState(
            offset_ms=offset_ms,
            uncertainty_ms=uncertainty_ms,
            updated_at_ms=server_now_ms(),
        )

    def get(self, device_id: str) -> NodeOffsetState | None:
        return self._state.get(device_id)

    def is_stale(self, device_id: str, *, max_age_ms: int = 10_000) -> bool:
        state = self._state.get(device_id)
        if state is None:
            return True
        return server_now_ms() - state.updated_at_ms > max_age_ms
