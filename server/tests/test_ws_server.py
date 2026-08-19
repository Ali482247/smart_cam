from __future__ import annotations

import asyncio

import pytest
from websockets.asyncio.client import connect

import scheduler_pb2

from server.connection.connection_manager import ConnectionManager
from server.connection.session_manager import SessionManager
from server.events import EventBus
from server.heartbeat.heartbeat_manager import HeartbeatManager
from server.network.ws_server import WebSocketServer
from server.protocol.codec import decode_envelope, new_envelope
from server.scheduler.scheduler import Scheduler
from server.synchronization.clock_sync import ClockOffsetStore

TEST_PORT = 8301


@pytest.fixture
async def running_server():
    bus = EventBus()
    session_manager = SessionManager()
    connection_manager = ConnectionManager(session_manager, bus)
    offset_store = ClockOffsetStore()
    heartbeat_manager = HeartbeatManager(connection_manager, session_manager, bus, offset_store, check_interval=1.0)
    scheduler = Scheduler(connection_manager, offset_store)
    server = WebSocketServer(connection_manager, heartbeat_manager, scheduler, bus, host="127.0.0.1", port=TEST_PORT)
    await server.start()
    heartbeat_manager.start()
    try:
        yield connection_manager, offset_store, scheduler, bus
    finally:
        await heartbeat_manager.stop()
        await server.stop()


@pytest.mark.asyncio
async def test_handshake_over_real_socket(running_server):
    connection_manager, _, _, _ = running_server

    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-1", sequence_number=1)
        hello.hello.device_name = "Pixel"
        await ws.send(hello.SerializeToString())

        welcome = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))

        assert welcome.WhichOneof("payload") == "welcome"
        assert welcome.welcome.session_id
        assert connection_manager.is_connected("dev-1")


@pytest.mark.asyncio
async def test_clock_sync_request_gets_reply(running_server):
    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-2", sequence_number=1)
        hello.hello.device_name = "Test Phone"
        await ws.send(hello.SerializeToString())
        welcome = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))

        request = new_envelope(device_id="dev-2", session_id=welcome.welcome.session_id, sequence_number=2)
        request.clock_req.t0_ms = 555
        await ws.send(request.SerializeToString())

        reply = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))

        assert reply.WhichOneof("payload") == "clock_reply"
        assert reply.clock_reply.t0_ms == 555


@pytest.mark.asyncio
async def test_heartbeat_seeds_rtt_and_offset(running_server):
    connection_manager, offset_store, _, _ = running_server

    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-3", sequence_number=1)
        hello.hello.device_name = "Test Phone"
        await ws.send(hello.SerializeToString())
        welcome = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))

        heartbeat = new_envelope(device_id="dev-3", session_id=welcome.welcome.session_id, sequence_number=2)
        heartbeat.heartbeat.battery_pct = 50.0
        heartbeat.heartbeat.last_rtt_ms = 7.5
        heartbeat.heartbeat.clock_offset_ms = 3
        heartbeat.heartbeat.clock_uncertainty_ms = 1
        await ws.send(heartbeat.SerializeToString())
        await asyncio.sleep(0.1)

        assert connection_manager.rtt_p99("dev-3") == 7.5
        assert offset_store.get("dev-3").offset_ms == 3


@pytest.mark.asyncio
async def test_heartbeat_gets_bidirectional_ack(running_server):
    """Connection reliability audit §8-9: the phone can only detect a half-open
    connection (it thinks it's connected, the Director already dropped it) if the
    server actually acks every heartbeat rather than heartbeats being fire-and-forget."""
    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-hb-ack", sequence_number=1)
        hello.hello.device_name = "Test Phone"
        await ws.send(hello.SerializeToString())
        await asyncio.wait_for(ws.recv(), timeout=2)  # welcome

        heartbeat = new_envelope(device_id="dev-hb-ack", session_id="", sequence_number=42)
        heartbeat.heartbeat.battery_pct = 90.0
        await ws.send(heartbeat.SerializeToString())

        ack = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))

        assert ack.WhichOneof("payload") == "heartbeat_ack"
        assert ack.heartbeat_ack.heartbeat_seq == 42


@pytest.mark.asyncio
async def test_scheduled_command_is_delivered_and_acked(running_server):
    connection_manager, offset_store, scheduler, _ = running_server

    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-4", sequence_number=1)
        hello.hello.device_name = "Test Phone"
        await ws.send(hello.SerializeToString())
        welcome = decode_envelope(await asyncio.wait_for(ws.recv(), timeout=2))
        session_id = welcome.welcome.session_id

        heartbeat = new_envelope(device_id="dev-4", session_id=session_id, sequence_number=2)
        heartbeat.heartbeat.last_rtt_ms = 5.0
        heartbeat.heartbeat.clock_uncertainty_ms = 1
        await ws.send(heartbeat.SerializeToString())
        await asyncio.sleep(0.1)

        async def ack_it():
            # The server now replies to every heartbeat with a heartbeat_ack (connection
            # reliability audit §8-9: bidirectional liveness) - skip over it to get to
            # the sched_cmd this test actually cares about.
            command = None
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                envelope = decode_envelope(raw)
                if envelope.WhichOneof("payload") == "sched_cmd":
                    command = envelope
                    break
            assert command is not None, "did not receive sched_cmd"
            ack = new_envelope(device_id="dev-4", session_id=session_id, sequence_number=3)
            ack.ack.command_id = command.sched_cmd.command_id
            await ws.send(ack.SerializeToString())

        task = asyncio.create_task(ack_it())
        result = await scheduler.schedule_command(scheduler_pb2.ScheduledCommand.START, camera_name="one")
        await task

        assert result.acked == ["dev-4"]
        assert result.missing_ack == []


@pytest.mark.asyncio
async def test_disconnect_unregisters_connection(running_server):
    connection_manager, _, _, _ = running_server

    async with connect(f"ws://127.0.0.1:{TEST_PORT}") as ws:
        hello = new_envelope(device_id="dev-5", sequence_number=1)
        hello.hello.device_name = "Test Phone"
        await ws.send(hello.SerializeToString())
        await asyncio.wait_for(ws.recv(), timeout=2)
        assert connection_manager.is_connected("dev-5")

    await asyncio.sleep(0.2)
    assert not connection_manager.is_connected("dev-5")
