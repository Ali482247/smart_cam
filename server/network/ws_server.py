"""WebSocketServer: persistent, binary-frame-only WS transport (network_architecture.md
§Transport Layer). Pure transport + dispatch - decodes Envelope, delegates to
ConnectionManager/HeartbeatManager/Scheduler/EventBus, and never itself decides camera
or scheduling business logic (strict layering rule).
"""

from __future__ import annotations

import logging

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

import device_pb2
import recording_pb2

from server.connection.connection_manager import ConnectionManager
from server.connection.models import Session
from server.events import Event, EventBus, EventType
from server.heartbeat.heartbeat_manager import HeartbeatManager
from server.protocol.codec import (
    DecodeError,
    PROTOCOL_VERSION,
    SequenceOutcome,
    SequenceTracker,
    decode_envelope,
    encode_envelope,
    new_envelope,
)
from server.scheduler.scheduler import Scheduler
from server.synchronization.clock_sync import respond_to_request, server_now_ms

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8088

_RECORDING_EVENT_TYPE_MAP = {
    recording_pb2.Event.DEVICE_CONNECTED: EventType.DEVICE_CONNECTED,
    recording_pb2.Event.DEVICE_DISCONNECTED: EventType.DEVICE_DISCONNECTED,
    recording_pb2.Event.RECORDING_STARTED: EventType.RECORDING_STARTED,
    recording_pb2.Event.RECORDING_STOPPED: EventType.RECORDING_STOPPED,
    recording_pb2.Event.UPLOAD_STARTED: EventType.UPLOAD_STARTED,
    recording_pb2.Event.UPLOAD_COMPLETED: EventType.UPLOAD_COMPLETED,
    recording_pb2.Event.STORAGE_WARNING: EventType.STORAGE_WARNING,
    recording_pb2.Event.BATTERY_WARNING: EventType.BATTERY_WARNING,
    recording_pb2.Event.CONNECTION_LOST: EventType.CONNECTION_LOST,
}


class WebSocketNodeConnection:
    """Concrete `NodeConnection` (models.py) backed by a `websockets` connection."""

    def __init__(self, websocket: ServerConnection, device_id: str, remote_address: str) -> None:
        self.websocket = websocket
        self.device_id = device_id
        self.remote_address = remote_address

    async def send_envelope(self, envelope) -> None:
        await self.websocket.send(encode_envelope(envelope))

    async def close(self) -> None:
        await self.websocket.close()


class WebSocketServer:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        heartbeat_manager: HeartbeatManager,
        scheduler: Scheduler,
        event_bus: EventBus,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._connection_manager = connection_manager
        self._heartbeat_manager = heartbeat_manager
        self._scheduler = scheduler
        self._event_bus = event_bus
        self._host = host
        self._port = port
        self._server: Server | None = None
        self._sequence_trackers: dict[str, SequenceTracker] = {}

    async def start(self) -> None:
        self._server = await serve(self._handle_connection, self._host, self._port)
        logger.info("WebSocketServer listening on %s:%s", self._host, self._port)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        remote_address = str(websocket.remote_address)
        device_id: str | None = None
        try:
            raw = await websocket.recv()
            envelope = decode_envelope(raw)
            if envelope.WhichOneof("payload") != "hello":
                await websocket.close(code=1002, reason="expected Hello as first message")
                return

            if envelope.protocol_version != PROTOCOL_VERSION:
                error_envelope = new_envelope(device_id=envelope.hello.device_id)
                error_envelope.welcome.error = (
                    f"unsupported protocol_version {envelope.protocol_version}, "
                    f"server supports {PROTOCOL_VERSION}"
                )
                await websocket.send(encode_envelope(error_envelope))
                await websocket.close(code=1002, reason="protocol version mismatch")
                return

            hello: device_pb2.Hello = envelope.hello
            # Envelope.device_id (not Hello.device_id) is the canonical identity field -
            # it's the one present on every subsequent message (heartbeats, acks, ...),
            # so using it here too keeps identity resolution consistent across the whole
            # connection rather than special-casing the handshake message.
            device_id = envelope.device_id
            connection = WebSocketNodeConnection(websocket, device_id, remote_address)
            session, resumed = await self._connection_manager.register(connection, hello)
            self._sequence_trackers[device_id] = SequenceTracker()
            logger.info(
                "device_id=%s connected from %s (resumed=%s, session_id=%s)",
                device_id, remote_address, resumed, session.session_id,
            )

            welcome_envelope = new_envelope(device_id=device_id, session_id=session.session_id)
            welcome_envelope.welcome.session_id = session.session_id
            welcome_envelope.welcome.protocol_version = PROTOCOL_VERSION
            welcome_envelope.welcome.server_time_ms = server_now_ms()
            await connection.send_envelope(welcome_envelope)

            async for raw_message in websocket:
                await self._dispatch(device_id, session, raw_message)

        except ConnectionClosed:
            pass
        except DecodeError as error:
            logger.warning("decode error from %s: %s", remote_address, error)
        finally:
            if device_id is not None:
                self._sequence_trackers.pop(device_id, None)
                await self._connection_manager.unregister(device_id, lost=True)

    async def _dispatch(self, device_id: str, session: Session, raw_message: bytes) -> None:
        try:
            envelope = decode_envelope(raw_message)
        except DecodeError as error:
            logger.warning("decode error from device_id=%s: %s", device_id, error)
            return

        tracker = self._sequence_trackers.setdefault(device_id, SequenceTracker())
        outcome = tracker.observe(envelope.sequence_number)
        if outcome == SequenceOutcome.STALE:
            logger.info("dropping stale message from device_id=%s (seq=%s)", device_id, envelope.sequence_number)
            return

        payload = envelope.WhichOneof("payload")

        if payload == "heartbeat":
            self._heartbeat_manager.record_heartbeat(device_id, envelope.heartbeat)

        elif payload == "clock_req":
            reply = respond_to_request(envelope.clock_req)
            reply_envelope = new_envelope(device_id=device_id, session_id=session.session_id)
            reply_envelope.clock_reply.CopyFrom(reply)
            await self._connection_manager.send(device_id, reply_envelope)

        elif payload == "ack":
            self._scheduler.on_ack(device_id, envelope.ack)

        elif payload == "status":
            session.recording = envelope.status.recording

        elif payload == "event":
            event_type = _RECORDING_EVENT_TYPE_MAP.get(envelope.event.type)
            if event_type is not None:
                self._event_bus.emit(Event(event_type, device_id, envelope.event.detail))

        elif payload == "upload_progress":
            logger.debug(
                "device_id=%s upload progress: %s/%s bytes (%s)",
                device_id, envelope.upload_progress.bytes_sent,
                envelope.upload_progress.total_bytes, envelope.upload_progress.video_name,
            )

        else:
            logger.warning("device_id=%s sent unhandled payload type: %s", device_id, payload)
