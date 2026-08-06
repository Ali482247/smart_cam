from __future__ import annotations

import pytest

from server.connection.connection_manager import ConnectionManager
from server.connection.session_manager import GRACE_WINDOW, SessionManager
from server.events import EventBus, EventType
from server.tests.conftest import FakeConnection, make_hello


@pytest.mark.asyncio
async def test_register_creates_session_and_emits_connected_event():
    events = []
    bus = EventBus()
    bus.subscribe(events.append)
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)

    connection = FakeConnection("dev-1")
    session, resumed = await connection_manager.register(connection, make_hello())

    assert resumed is False
    assert session.device_id == "dev-1"
    assert connection_manager.is_connected("dev-1")
    assert [event.type for event in events] == [EventType.DEVICE_CONNECTED]


@pytest.mark.asyncio
async def test_newer_connection_replaces_older_for_same_device_id():
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)

    old_connection = FakeConnection("dev-1")
    await connection_manager.register(old_connection, make_hello())
    new_connection = FakeConnection("dev-1")
    await connection_manager.register(new_connection, make_hello())

    assert old_connection.closed is True
    assert connection_manager.connected_device_ids() == ["dev-1"]


@pytest.mark.asyncio
async def test_session_resumes_within_grace_window():
    session_manager = SessionManager()
    hello = make_hello()

    first_session, first_resumed = session_manager.create_or_resume("dev-1", hello)
    session_manager.mark_disconnected("dev-1")
    second_session, second_resumed = session_manager.create_or_resume("dev-1", hello)

    assert first_resumed is False
    assert second_resumed is True
    assert second_session.session_id == first_session.session_id


@pytest.mark.asyncio
async def test_session_does_not_resume_after_grace_window_expires():
    session_manager = SessionManager()
    hello = make_hello()

    first_session, _ = session_manager.create_or_resume("dev-1", hello)
    session_manager.mark_disconnected("dev-1")
    # Simulate grace window expiry without sleeping in real time.
    session_manager.get("dev-1").disconnected_at -= GRACE_WINDOW * 2

    second_session, resumed = session_manager.create_or_resume("dev-1", hello)

    assert resumed is False
    assert second_session.session_id != first_session.session_id


@pytest.mark.asyncio
async def test_recording_session_resumes_after_grace_window_expires():
    session_manager = SessionManager()
    hello = make_hello()

    first_session, _ = session_manager.create_or_resume("dev-1", hello)
    first_session.recording = True
    session_manager.mark_disconnected("dev-1")
    session_manager.get("dev-1").disconnected_at -= GRACE_WINDOW * 2

    expired = session_manager.sweep_expired()
    second_session, resumed = session_manager.create_or_resume("dev-1", hello)

    assert expired == []
    assert resumed is True
    assert second_session.session_id == first_session.session_id


@pytest.mark.asyncio
async def test_send_and_broadcast():
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)

    conn_a = FakeConnection("A")
    conn_b = FakeConnection("B")
    await connection_manager.register(conn_a, make_hello())
    await connection_manager.register(conn_b, make_hello())

    from server.protocol.codec import new_envelope

    results = await connection_manager.broadcast(new_envelope())

    assert results == {"A": True, "B": True}
    assert len(conn_a.sent) == 1
    assert len(conn_b.sent) == 1


def test_rtt_p99_tracks_samples():
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)

    assert connection_manager.rtt_p99("dev-1") is None

    for rtt in (5.0, 10.0, 15.0, 20.0):
        connection_manager.record_rtt("dev-1", rtt)

    assert connection_manager.rtt_p99("dev-1") == 20.0
