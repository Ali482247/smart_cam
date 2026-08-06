from __future__ import annotations

from server.protocol.codec import (
    SequenceOutcome,
    SequenceTracker,
    decode_envelope,
    encode_envelope,
    new_envelope,
)


def test_envelope_roundtrip():
    envelope = new_envelope(device_id="dev-1", session_id="sess-1", sequence_number=7, timestamp_ms=42)
    envelope.heartbeat.battery_pct = 91.5

    decoded = decode_envelope(encode_envelope(envelope))

    assert decoded.device_id == "dev-1"
    assert decoded.session_id == "sess-1"
    assert decoded.sequence_number == 7
    assert decoded.WhichOneof("payload") == "heartbeat"
    assert decoded.heartbeat.battery_pct == 91.5


def test_sequence_tracker_new_and_duplicate():
    tracker = SequenceTracker()

    assert tracker.observe(1) == SequenceOutcome.NEW
    assert tracker.observe(2) == SequenceOutcome.NEW
    assert tracker.observe(2) == SequenceOutcome.DUPLICATE


def test_sequence_tracker_out_of_order_then_stale():
    tracker = SequenceTracker()
    tracker.observe(10)

    assert tracker.observe(8) == SequenceOutcome.OUT_OF_ORDER_NEW
    assert tracker.observe(8) == SequenceOutcome.DUPLICATE

    tracker.watermark = 500
    assert tracker.observe(1) == SequenceOutcome.STALE
