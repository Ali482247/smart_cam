from __future__ import annotations

import asyncio

import pytest

import common_pb2
import scheduler_pb2

from server.connection.connection_manager import ConnectionManager
from server.connection.session_manager import SessionManager
from server.events import EventBus
from server.scheduler.scheduler import Scheduler
from server.synchronization.clock_sync import ClockOffsetStore
from server.tests.conftest import make_hello


class AckingConnection:
    """Like FakeConnection, but auto-acks any ScheduledCommand it receives, after an
    optional delay, so Scheduler's broadcast/ack-wait loop can be exercised for real."""

    def __init__(self, device_id: str, scheduler: Scheduler, *, ack_delay: float = 0.0, should_ack: bool = True) -> None:
        self.device_id = device_id
        self.remote_address = "fake://" + device_id
        self._scheduler = scheduler
        self._ack_delay = ack_delay
        self._should_ack = should_ack
        self.closed = False

    async def send_envelope(self, envelope) -> None:
        if envelope.WhichOneof("payload") != "sched_cmd" or not self._should_ack:
            return
        command_id = envelope.sched_cmd.command_id

        async def reply() -> None:
            await asyncio.sleep(self._ack_delay)
            self._scheduler.on_ack(
                self.device_id, scheduler_pb2.Ack(command_id=command_id, result=common_pb2.RESULT_OK)
            )

        asyncio.get_running_loop().create_task(reply())

    async def close(self) -> None:
        self.closed = True


async def _setup(*, safety_margin_ms: int = 10, must_ack_lead_ms: int = 20):
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)
    offset_store = ClockOffsetStore()
    scheduler = Scheduler(
        connection_manager, offset_store,
        safety_margin_ms=safety_margin_ms, must_ack_lead_ms=must_ack_lead_ms,
        retry_delays_ms=(20, 40, 80),
    )
    return connection_manager, offset_store, scheduler


async def _add_node(connection_manager, offset_store, scheduler, device_id, *, rtt_ms, uncertainty_ms, ack_delay=0.0, should_ack=True):
    connection = AckingConnection(device_id, scheduler, ack_delay=ack_delay, should_ack=should_ack)
    await connection_manager.register(connection, make_hello())
    connection_manager.record_rtt(device_id, rtt_ms)
    offset_store.record(device_id, offset_ms=0.0, uncertainty_ms=uncertainty_ms)
    return connection


@pytest.mark.asyncio
async def test_all_nodes_ack_in_time():
    connection_manager, offset_store, scheduler = await _setup()
    await _add_node(connection_manager, offset_store, scheduler, "A", rtt_ms=5, uncertainty_ms=1)
    await _add_node(connection_manager, offset_store, scheduler, "B", rtt_ms=12, uncertainty_ms=2)
    await _add_node(connection_manager, offset_store, scheduler, "C", rtt_ms=40, uncertainty_ms=4)

    result = await scheduler.schedule_command(scheduler_pb2.ScheduledCommand.START, camera_name="one")

    assert sorted(result.acked) == ["A", "B", "C"]
    assert result.missing_ack == []
    assert result.ok is True


@pytest.mark.asyncio
async def test_node_without_rtt_data_is_excluded():
    connection_manager, offset_store, scheduler = await _setup()
    await _add_node(connection_manager, offset_store, scheduler, "A", rtt_ms=5, uncertainty_ms=1)
    # B has no recorded RTT/offset at all.
    connection = AckingConnection("B", scheduler)
    await connection_manager.register(connection, make_hello())

    result = await scheduler.schedule_command(scheduler_pb2.ScheduledCommand.START)

    assert result.included == ["A"]
    assert result.excluded_missing_data == ["B"]


@pytest.mark.asyncio
async def test_partial_batch_missing_ack_is_reported_not_silently_dropped():
    connection_manager, offset_store, scheduler = await _setup(safety_margin_ms=10, must_ack_lead_ms=20)
    await _add_node(connection_manager, offset_store, scheduler, "A", rtt_ms=5, uncertainty_ms=1)
    await _add_node(
        connection_manager, offset_store, scheduler, "C", rtt_ms=5, uncertainty_ms=1, should_ack=False,
    )

    result = await scheduler.schedule_command(scheduler_pb2.ScheduledCommand.STOP)

    assert result.acked == ["A"]
    assert result.missing_ack == ["C"]
    assert result.ok is False


@pytest.mark.asyncio
async def test_retry_resends_to_still_pending_nodes_only():
    connection_manager, offset_store, scheduler = await _setup(safety_margin_ms=10, must_ack_lead_ms=200)
    send_counts = {"A": 0, "B": 0}

    class CountingConnection(AckingConnection):
        async def send_envelope(self, envelope):
            if envelope.WhichOneof("payload") == "sched_cmd":
                send_counts[self.device_id] += 1
            await super().send_envelope(envelope)

    conn_a = CountingConnection("A", scheduler, ack_delay=0.0)
    await connection_manager.register(conn_a, make_hello())
    connection_manager.record_rtt("A", 5)
    offset_store.record("A", offset_ms=0.0, uncertainty_ms=1)

    # B never acks in this test's short window, so it should be retried multiple times.
    conn_b = CountingConnection("B", scheduler, ack_delay=999.0)
    await connection_manager.register(conn_b, make_hello())
    connection_manager.record_rtt("B", 5)
    offset_store.record("B", offset_ms=0.0, uncertainty_ms=1)

    result = await scheduler.schedule_command(scheduler_pb2.ScheduledCommand.START)

    assert "A" in result.acked
    assert send_counts["A"] == 1  # A acked immediately, so it should not be retried
    assert send_counts["B"] > 1  # B never acked, so it should have been retried
