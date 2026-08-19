from __future__ import annotations

import threading
import time

from websockets.sync.client import connect

import scheduler_pb2

from server.gateway.gateway import Gateway, GatewayConfig
from server.protocol.codec import decode_envelope, new_envelope

TEST_PORT = 8401


def _run_fake_phone(port: int, device_id: str, results: dict) -> None:
    with connect(f"ws://127.0.0.1:{port}") as ws:
        hello = new_envelope(device_id=device_id, sequence_number=1)
        hello.hello.device_name = "Sync Test Phone"
        ws.send(hello.SerializeToString())
        welcome = decode_envelope(ws.recv())
        results["session_id"] = welcome.welcome.session_id

        heartbeat = new_envelope(device_id=device_id, session_id=welcome.welcome.session_id, sequence_number=2)
        heartbeat.heartbeat.last_rtt_ms = 6.0
        heartbeat.heartbeat.clock_uncertainty_ms = 1
        ws.send(heartbeat.SerializeToString())
        time.sleep(0.2)

        # The server now replies to every heartbeat with a heartbeat_ack (connection
        # reliability audit §8-9: bidirectional liveness) - skip over it to get to the
        # sched_cmd this test actually cares about.
        command = decode_envelope(ws.recv())
        if command.WhichOneof("payload") == "heartbeat_ack":
            command = decode_envelope(ws.recv())
        results["command_type"] = command.sched_cmd.type
        ack = new_envelope(device_id=device_id, session_id=welcome.welcome.session_id, sequence_number=3)
        ack.ack.command_id = command.sched_cmd.command_id
        ws.send(ack.SerializeToString())
        time.sleep(0.2)


def test_gateway_bridges_dashboard_thread_to_asyncio_core():
    gateway = Gateway(GatewayConfig(ws_host="127.0.0.1", ws_port=TEST_PORT, discovery_port=8491, probe_interval_seconds=1.0))
    gateway.start()
    try:
        results: dict = {}
        phone_thread = threading.Thread(target=_run_fake_phone, args=(TEST_PORT, "dev-sync", results))
        phone_thread.start()
        time.sleep(0.4)

        assert gateway.connected_device_ids() == ["dev-sync"]

        result = gateway.start_recording(camera_name="one")

        phone_thread.join(timeout=5)

        assert result.acked == ["dev-sync"]
        assert results.get("command_type") == scheduler_pb2.ScheduledCommand.START
    finally:
        gateway.stop()
