"""Envelope encode/decode plus the dedup/ordering rules from protocol_specification.md
§ACK/Retry/Timeout/Dedup/Ordering.

This module has zero knowledge of WebSocket or camera business logic (strict layering
rule, network_architecture.md) - it only understands Envelope bytes and sequence
bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import server.protocol  # noqa: F401 - ensures generated/ is on sys.path first
import envelope_pb2

PROTOCOL_VERSION = 1
DEDUP_WINDOW_SIZE = 256


class SequenceOutcome(Enum):
    NEW = "NEW"
    OUT_OF_ORDER_NEW = "OUT_OF_ORDER_NEW"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"


class DecodeError(ValueError):
    """Raised when raw bytes are not a valid Envelope."""


def encode_envelope(envelope: envelope_pb2.Envelope) -> bytes:
    return envelope.SerializeToString()


def decode_envelope(data: bytes) -> envelope_pb2.Envelope:
    envelope = envelope_pb2.Envelope()
    try:
        envelope.ParseFromString(data)
    except Exception as error:  # noqa: BLE001 - re-raised as a typed decode error
        raise DecodeError(f"invalid envelope bytes: {error}") from error
    return envelope


def new_envelope(
    *, device_id: str = "", session_id: str = "", sequence_number: int = 0,
    timestamp_ms: int = 0, app_version: str = "server",
) -> envelope_pb2.Envelope:
    return envelope_pb2.Envelope(
        protocol_version=PROTOCOL_VERSION,
        app_version=app_version,
        device_id=device_id,
        session_id=session_id,
        sequence_number=sequence_number,
        timestamp_ms=timestamp_ms,
    )


@dataclass
class SequenceTracker:
    """Per-session dedup + ordering, keyed by (device_id, session_id) at the call site.

    Ordering: the current watermark only advances forward; anything older is dropped.
    Dedup: the last DEDUP_WINDOW_SIZE sequence numbers seen are cached so retransmits of
    an already-processed message are recognized (and can be re-acked) rather than
    reprocessed.
    """

    watermark: int = -1
    _seen: set[int] = field(default_factory=set)
    _seen_order: list[int] = field(default_factory=list)

    def observe(self, sequence_number: int) -> SequenceOutcome:
        if sequence_number in self._seen:
            return SequenceOutcome.DUPLICATE
        if sequence_number <= self.watermark - DEDUP_WINDOW_SIZE:
            # Far older than anything we're still tracking - treat as stale/duplicate
            # rather than risk reprocessing something already acted on and evicted.
            return SequenceOutcome.STALE

        self._seen.add(sequence_number)
        self._seen_order.append(sequence_number)
        if len(self._seen_order) > DEDUP_WINDOW_SIZE:
            evicted = self._seen_order.pop(0)
            self._seen.discard(evicted)

        if sequence_number > self.watermark:
            self.watermark = sequence_number
            return SequenceOutcome.NEW
        return SequenceOutcome.OUT_OF_ORDER_NEW
