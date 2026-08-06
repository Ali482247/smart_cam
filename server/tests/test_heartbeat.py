from __future__ import annotations

import asyncio

import pytest

import heartbeat_pb2

from server.connection.connection_manager import ConnectionManager
from server.connection.session_manager import SessionManager
from server.events import EventBus, EventType
from server.heartbeat.heartbeat_manager import HeartbeatManager
from server.synchronization.clock_sync import ClockOffsetStore
from server.tests.conftest import FakeConnection, make_hello


@pytest.mark.asyncio
async def test_record_heartbeat_updates_session_and_offset_store():
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)
    offset_store = ClockOffsetStore()
    heartbeat_manager = HeartbeatManager(connection_manager, session_manager, bus, offset_store)

    connection = FakeConnection("dev-1")
    await connection_manager.register(connection, make_hello())

    heartbeat_manager.record_heartbeat(
        "dev-1",
        heartbeat_pb2.Heartbeat(
            battery_pct=77.0, recording=True, clock_offset_ms=-12, clock_uncertainty_ms=3, last_rtt_ms=9.0,
        ),
    )

    session = session_manager.get("dev-1")
    assert session.battery_pct == 77.0
    assert session.recording is True
    assert session.heartbeat_suspect is False

    offset_state = offset_store.get("dev-1")
    assert offset_state.offset_ms == -12
    assert offset_state.uncertainty_ms == 3
    assert connection_manager.rtt_p99("dev-1") == 9.0


@pytest.mark.asyncio
async def test_missed_heartbeats_go_suspect_then_offline():
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)
    offset_store = ClockOffsetStore()
    heartbeat_manager = HeartbeatManager(
        connection_manager, session_manager, bus, offset_store,
        check_interval=0.05, suspect_after=0.1, offline_after=0.2,
    )

    connection = FakeConnection("dev-1")
    await connection_manager.register(connection, make_hello())
    heartbeat_manager.record_heartbeat("dev-1", heartbeat_pb2.Heartbeat())

    heartbeat_manager.start()
    try:
        await asyncio.sleep(0.16)
        assert session_manager.get("dev-1").heartbeat_suspect is True
        assert connection_manager.is_connected("dev-1")

        await asyncio.sleep(0.15)
        assert not connection_manager.is_connected("dev-1")
        assert EventType.DEVICE_DISCONNECTED in [event.type for event in events]
    finally:
        await heartbeat_manager.stop()
