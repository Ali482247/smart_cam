# Scheduler

See [clock_synchronization.md](clock_synchronization.md) for `offset`/`offsetUncertaintyMs`
and [protocol_specification.md](protocol_specification.md) for the `ScheduledCommand`/`Ack`
messages this layer sends/awaits. Failure handling for missed ACKs is detailed in
[failure_recovery.md](failure_recovery.md).

## Goal

Deliver a `ScheduledCommand` to every target node with an `execute_at_ms` far enough in
the future that network jitter and per-node clock-offset uncertainty are fully absorbed
before the deadline — this is the mechanism that actually buys the <10ms cross-node
execution skew target; without it, "send and hope" (today's HTTP model) has no
compensation for RTT variance across devices on a shared, possibly congested Wi-Fi
network.

## Algorithm

1. Dashboard/operator issues a "start recording" intent to the Scheduler Service
   through the Gateway (in-process call in Phase 1, see `network_architecture.md`
   §Threading Model — not gRPC).
2. Scheduler queries `ConnectionManager` for the current clock-offset estimate and
   **p99** (not average — the tail matters more than the typical case here) RTT for
   every target node.
3. Compute the lead time:
   ```
   leadTimeMs = max(over all target nodes: RTT_p99/2 + offsetUncertaintyMs) + safetyMarginMs
   ```
   `safetyMarginMs` defaults to **50ms**, configurable. If any target node's offset/RTT
   data is stale (older than 10s) or missing entirely, that node is **excluded** from
   this batch and a warning is surfaced — never silently degrade the whole batch's
   timing accuracy to accommodate one unmeasured node.
4. `mustAckByMs = serverNow() + mustAckLeadMs` (default **200ms** — the budget reserved
   for the ack/retry round trip to complete), then `executeAtServerMs = mustAckByMs +
   leadTimeMs` (leadTimeMs is added *on top*, purely to absorb network jitter/clock
   uncertainty between the ack deadline and the actual execution instant — it is not
   carved out of the 200ms ack budget, since leadTimeMs alone (tens of ms in the worked
   example below) would leave far too little time for even one retry). Retry delays
   (see `failure_recovery.md`'s general Ack-retry table, 300/600/1200ms) are too slow for
   this specific 200ms window — the Scheduler uses its own faster cadence (tens of ms)
   sized to fit multiple attempts inside `mustAckLeadMs`, since this is a much
   more time-critical path than a generic command retry.
5. Broadcast one `ScheduledCommand{execute_at_ms = executeAtServerMs}` to every target
   node **concurrently** (fired in parallel, never serialized one-by-one — serializing
   would reintroduce exactly the fan-out latency variance this design exists to remove).
6. Each node, on receipt, converts `execute_at_ms` to local time via its current offset
   (`clock_synchronization.md`), schedules a local timer for that instant, and
   immediately sends an `Ack`.
7. Scheduler waits for `Ack` from all target nodes until `mustAckByMs`. If any node's
   `Ack` is missing or late by that point, the Scheduler either retries delivery to that
   node or aborts/reports it as failed-to-schedule — the exact policy (abort-all vs.
   proceed-with-partial) is an operator choice, not hardcoded (see the partial-batch
   scenario in
   [sequence_diagrams.md](sequence_diagrams.md) and the recommendation in
   [failure_recovery.md](failure_recovery.md)). The Scheduler must never silently proceed
   with a node that never confirmed receipt — an un-acked node might start recording
   late, or not at all, with no visibility into which.

## Worked numeric example

Three nodes with different network conditions:

| Node | RTT_p99 | offsetUncertaintyMs | RTT_p99/2 + uncertainty |
|---|---|---|---|
| A (good Wi-Fi) | 5ms | 1ms | 3.5ms |
| B (typical) | 12ms | 2ms | 8ms |
| C (weak signal) | 40ms | 4ms | 24ms |

`leadTimeMs = max(3.5, 8, 24) + 50 = 74ms`. All three nodes receive
`executeAtServerMs = serverNow() + 74ms` and independently schedule a local timer for
that same instant (adjusted by their own offset). Even though node C's *absolute* delay
from "now" it perceives is different from A's, all three target the same server-clock
instant — that shared target, not the individual delivery time, is what makes them land
within the <10ms window of each other, as long as each node's actual offset error stays
inside its `offsetUncertaintyMs` budget.

## Stop / Toggle commands

Use the identical mechanism and the identical Ack-before-deadline guarantee. Stop is
arguably less latency-critical than Start (a few mismatched trailing frames across nodes
matters less than a few mismatched leading frames for later sync in post), but the
Scheduler treats them symmetrically — one algorithm, no special-casing, less to get
wrong.

## Relationship to failure handling

What happens when a node never Acks, or Acks late, or disconnects mid-countdown is
specified in [failure_recovery.md](failure_recovery.md) — this doc defines the
mechanism and the deadline math, that doc defines the policy for when the mechanism
doesn't get a clean answer in time.
