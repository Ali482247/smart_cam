"""Scheduler: computes synchronized executeAt timestamps, broadcasts ScheduledCommand,
tracks ACKs, retries (scheduler.md §Algorithm).

Depends on ConnectionManager (send/broadcast + RTT metrics) and ClockOffsetStore
(per-node offset/uncertainty), both injected - never touches the WebSocket transport or
the camera plugin directly (strict layering rule, network_architecture.md).

Implementation note on the must-ack-by deadline: scheduler.md's worked example (leadTime
~74ms) and its "must-ack-by = executeAt - 200ms" rule are only consistent if the ack
deadline gets the FULL must_ack_lead_ms budget for the retry protocol, with lead_time_ms
added on top purely to absorb network jitter/clock uncertainty between the ack deadline
and execution itself - not the other way around. This implementation makes that
explicit: `must_ack_by_ms = now + must_ack_lead_ms` and `execute_at_ms = must_ack_by_ms +
lead_time_ms`. This is a numeric clarification of the documented formula, not a change
to the algorithm's intent (same inputs, same retry/abort policy, same parallel-broadcast
requirement). Retry cadence (DEFAULT_RETRY_DELAYS_MS) is sized to fit inside
must_ack_lead_ms - see that constant's comment for why it differs from
failure_recovery.md's generic command-ack-retry table.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field

import scheduler_pb2

from server.connection.connection_manager import ConnectionManager
from server.protocol.codec import new_envelope
from server.synchronization.clock_sync import ClockOffsetStore, server_now_ms

logger = logging.getLogger(__name__)

DEFAULT_SAFETY_MARGIN_MS = 50
DEFAULT_MUST_ACK_LEAD_MS = 200
# Deliberately much shorter than failure_recovery.md's generic command-ack-retry table
# (300/600/1200ms) - that table is sized for non-time-critical commands. The Scheduler's
# retry budget is bounded by must_ack_lead_ms (200ms default), so its retry cadence has
# to fit multiple attempts inside that window, not the ~2.1s a generic retry policy uses.
DEFAULT_RETRY_DELAYS_MS = (50, 100)
DEFAULT_STALE_DATA_MAX_AGE_MS = 10_000


@dataclass
class SchedulerResult:
    command_id: str
    execute_at_ms: int
    included: list[str]
    excluded_missing_data: list[str]
    acked: list[str] = field(default_factory=list)
    missing_ack: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.included) and not self.missing_ack


class Scheduler:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        clock_offset_store: ClockOffsetStore,
        *,
        safety_margin_ms: int = DEFAULT_SAFETY_MARGIN_MS,
        must_ack_lead_ms: int = DEFAULT_MUST_ACK_LEAD_MS,
        retry_delays_ms: tuple[int, ...] = DEFAULT_RETRY_DELAYS_MS,
    ) -> None:
        self._connection_manager = connection_manager
        self._clock_offset_store = clock_offset_store
        self._safety_margin_ms = safety_margin_ms
        self._must_ack_lead_ms = must_ack_lead_ms
        self._retry_delays_ms = retry_delays_ms
        self._pending_acks: dict[str, dict[str, asyncio.Future]] = {}
        self._send_times: dict[tuple[str, str], int] = {}

    def on_ack(self, device_id: str, ack: scheduler_pb2.Ack) -> None:
        futures = self._pending_acks.get(ack.command_id)
        if not futures:
            return
        future = futures.get(device_id)
        if future is None or future.done():
            return

        send_time = self._send_times.pop((ack.command_id, device_id), None)
        if send_time is not None:
            self._connection_manager.record_rtt(device_id, server_now_ms() - send_time)

        future.set_result(ack.result)

    async def schedule_command(
        self,
        command_type: "scheduler_pb2.ScheduledCommand.Type",
        *,
        camera_name: str = "",
        session_label: str = "",
        record_index: int = 0,
        targets: list[str] | None = None,
    ) -> SchedulerResult:
        candidates = targets if targets is not None else self._connection_manager.connected_device_ids()
        included, excluded = self._select_targets(candidates)
        command_id = str(uuid.uuid4())

        if not included:
            logger.warning("schedule_command: no eligible targets (excluded=%s)", excluded)
            return SchedulerResult(command_id, 0, included, excluded)

        lead_time_ms = self._compute_lead_time(included)
        now_ms = server_now_ms()
        # must_ack_lead_ms is the budget reserved for the ack/retry protocol to finish;
        # lead_time_ms is then added on top purely to absorb network jitter/clock
        # uncertainty between the ack deadline and the actual execution instant. Acks
        # must complete inside [now, now + must_ack_lead_ms] - see the module docstring
        # for why this must be additive to, not carved out of, lead_time_ms.
        must_ack_by_ms = now_ms + self._must_ack_lead_ms
        execute_at_ms = must_ack_by_ms + lead_time_ms

        acked, missing = await self._broadcast_and_wait(
            command_id, command_type, execute_at_ms, camera_name, session_label,
            record_index, included, must_ack_by_ms,
        )
        if missing:
            logger.warning("schedule_command %s: nodes missing ack: %s", command_id, missing)
        return SchedulerResult(command_id, execute_at_ms, included, excluded, acked, missing)

    def _select_targets(self, candidates: list[str]) -> tuple[list[str], list[str]]:
        included: list[str] = []
        excluded: list[str] = []
        for device_id in candidates:
            rtt = self._connection_manager.rtt_p99(device_id)
            stale = self._clock_offset_store.is_stale(device_id, max_age_ms=DEFAULT_STALE_DATA_MAX_AGE_MS)
            if rtt is None or stale or not self._connection_manager.is_connected(device_id):
                excluded.append(device_id)
            else:
                included.append(device_id)
        return included, excluded

    def _compute_lead_time(self, included: list[str]) -> int:
        margins = []
        for device_id in included:
            rtt_p99 = self._connection_manager.rtt_p99(device_id) or 0.0
            state = self._clock_offset_store.get(device_id)
            uncertainty_ms = state.uncertainty_ms if state else 0.0
            margins.append(rtt_p99 / 2 + uncertainty_ms)
        return int(max(margins) + self._safety_margin_ms)

    async def _broadcast_and_wait(
        self, command_id: str, command_type, execute_at_ms: int, camera_name: str,
        session_label: str, record_index: int, included: list[str], must_ack_by_ms: int,
    ) -> tuple[list[str], list[str]]:
        loop = asyncio.get_running_loop()
        futures = {device_id: loop.create_future() for device_id in included}
        self._pending_acks[command_id] = futures

        try:
            pending = set(included)
            for retry_delay_ms in (0, *self._retry_delays_ms):
                if retry_delay_ms:
                    await asyncio.sleep(retry_delay_ms / 1000)
                pending = {d for d in pending if not futures[d].done()}
                if not pending:
                    break
                if server_now_ms() >= must_ack_by_ms:
                    break
                await self._send_to(
                    pending, command_id, command_type, execute_at_ms, camera_name,
                    session_label, record_index,
                )

            remaining_wait_s = max(0.0, (must_ack_by_ms - server_now_ms()) / 1000)
            still_pending = [futures[d] for d in included if not futures[d].done()]
            if still_pending and remaining_wait_s > 0:
                await asyncio.wait(still_pending, timeout=remaining_wait_s)

            acked = [d for d in included if futures[d].done()]
            missing = [d for d in included if not futures[d].done()]
            return acked, missing
        finally:
            del self._pending_acks[command_id]
            for device_id in included:
                self._send_times.pop((command_id, device_id), None)

    async def _send_to(
        self, targets: set[str], command_id: str, command_type, execute_at_ms: int,
        camera_name: str, session_label: str, record_index: int,
    ) -> None:
        envelope = new_envelope()
        envelope.sched_cmd.type = command_type
        envelope.sched_cmd.execute_at_ms = execute_at_ms
        envelope.sched_cmd.command_id = command_id
        envelope.sched_cmd.camera_name = camera_name
        envelope.sched_cmd.session_label = session_label
        envelope.sched_cmd.record_index = record_index

        now_ms = server_now_ms()
        for device_id in targets:
            self._send_times[(command_id, device_id)] = now_ms
        await self._connection_manager.broadcast(envelope, list(targets))
