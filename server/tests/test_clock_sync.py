from __future__ import annotations

import scheduler_pb2

from server.synchronization.clock_sync import (
    ClockOffsetStore,
    average_offset,
    compute_offset,
    offset_uncertainty,
    reject_outliers,
    respond_to_request,
)


def test_compute_offset_recovers_known_skew():
    # Node clock is 100ms ahead of server; symmetric 20ms one-way network delay.
    t0 = 1_000_000
    t1 = t0 - 100 + 20
    t2 = t1 + 5
    t3 = t0 + 20 + 5 + 20

    sample = compute_offset(t0, t1, t2, t3)

    assert sample.offset_ms == -100.0
    assert sample.rtt_ms == 40


def test_reject_outliers_drops_high_rtt_sample():
    good = compute_offset(1000, 900, 905, 1040)
    bad = compute_offset(1000, 900, 905, 1540)  # inflated RTT

    kept = reject_outliers([good, good, good, bad])

    assert bad not in kept
    assert kept.count(good) == 3


def test_average_and_uncertainty():
    samples = [compute_offset(1000, 900, 905, 1040) for _ in range(3)]

    assert average_offset(samples) == samples[0].offset_ms
    assert offset_uncertainty(samples) == 0.0

    assert average_offset([]) == 0.0
    assert offset_uncertainty([]) == 0.0


def test_respond_to_request_echoes_t0_and_orders_timestamps():
    request = scheduler_pb2.ClockSyncRequest(t0_ms=123456)

    reply = respond_to_request(request)

    assert reply.t0_ms == 123456
    assert reply.t1_ms <= reply.t2_ms


def test_clock_offset_store_staleness():
    store = ClockOffsetStore()

    assert store.is_stale("dev-1") is True

    store.record("dev-1", offset_ms=-5.0, uncertainty_ms=2.0)

    assert store.is_stale("dev-1") is False
    assert store.get("dev-1").offset_ms == -5.0
