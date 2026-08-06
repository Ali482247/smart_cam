# Failure Recovery

Depends on the exact thresholds in [connection_lifecycle.md](connection_lifecycle.md)
and the Ack-deadline semantics in [scheduler.md](scheduler.md) — this doc defines
*policy* for what to do when those mechanisms don't get a clean answer in time.

## Failure taxonomy

| Category | Examples | First-noticed by |
|---|---|---|
| Transport | WS drop, partial frame | `server/network`, `server/connection` |
| Timing | Missed Ack, clock-drift spike | `server/scheduler`, `server/synchronization` |
| Device | Battery critical, storage full, thermal throttling | Heartbeat payload (`server/heartbeat`, `server/storage`) |
| Application | Camera plugin exception mid-recording | Node-local, reported via `Event` |
| Server | Scheduler/Gateway process crash | *Phase 2+ concern* — Phase 1 runs as a single asyncio process with no partial-failure story here; noted, not solved this pass |

## Per-failure recovery

### Transport: WS drop
- **Detection:** WS close/error event on either side, or heartbeat silence.
- **Mitigation:** node applies reconnect backoff (`connection_lifecycle.md`); server
  marks node SUSPECT then OFFLINE per the 15s/30s thresholds.
- **Event fired:** `ConnectionLost`, then `DeviceDisconnected` if it escalates to OFFLINE.
- **Dashboard shows:** node row flips to "reconnecting" then "offline" with last-seen time.
- **Recovery:** automatic (reconnect + session recovery), no manual intervention unless
  the grace window expires.

### Timing: missed Ack on a scheduled command
- **Detection:** Scheduler's must-ack-by deadline (`executeAtServerMs - 200ms`) passes
  without an Ack from a target node.
- **Mitigation:** retry delivery to that node (see retry table below); if still no Ack,
  apply the partial-batch policy (see below).
- **Event fired:** none new — this is a Scheduler-internal condition, surfaced directly
  to Dashboard as a warning rather than a generic Event.
- **Recovery:** automatic decision (proceed/abort per policy), operator can manually
  retry the excluded node for the next take.

### Timing: clock-drift spike
- **Detection:** a clock-sync re-sample (every 30-60s) produces an offset far outside
  the previous `offsetUncertaintyMs` band.
- **Mitigation:** widen `offsetUncertaintyMs` for that node immediately (don't wait for
  the next full burst), which flows into a larger Scheduler lead-time margin for that
  node on the next command.
- **Recovery:** automatic; no operator action needed unless drift is persistent (a
  persistently unstable node's clock might indicate a hardware/OS issue worth flagging
  in the UI as a soft warning).

### Device: battery critical / storage full / thermal throttling
- **Detection:** heartbeat payload fields (`battery_pct`, `free_storage_bytes`,
  `temperature_c`) crossing configured thresholds.
- **Mitigation:** none automatic at the network layer — recording is a local decision
  the phone/OS ultimately controls; the network layer's job is purely to surface it.
- **Event fired:** `StorageWarning`, `BatteryWarning`.
- **Dashboard shows:** a visible warning badge on that node's row before/during a take,
  so the operator can react (swap phone, plug in charger) before starting rather than
  after losing a take.
- **Recovery:** manual (operator-driven).

### Application: camera plugin exception mid-recording
- **Detection:** node-local try/catch around the camera plugin call; reported as an
  `Event` (extend the `Event.Type` enum if a dedicated type is warranted, or use
  `detail` free-form for now).
- **Mitigation:** node attempts to save whatever was recorded so far, same as any normal
  stop, rather than discarding it.
- **Recovery:** manual — this is exactly the class of failure the operator needs to see
  and decide whether to retry the shot.

### Server: process crash (Phase 2+ concern)
- Not solved in Phase 1 (single-process asyncio core has no partial-failure story to
  design around yet). Flagged here so it isn't silently forgotten once the gRPC service
  split (Phase 2, see `network_architecture.md`) introduces multiple processes that can
  fail independently.

## Retry / backoff table

| Mechanism | Attempts | Delays |
|---|---|---|
| WS reconnect (mobile client) | Unbounded, capped delay | 1s, 2s, 4s, 8s, then 15s repeating, ±20% jitter |
| Scheduled-command Ack retry | 3 | 300ms, 600ms, 1200ms |
| Upload chunk retry | 5 | 1s, 2s, 4s, 8s, 16s, then mark upload failed — requires manual retry from Dashboard |

## Partial-batch failure policy

Scenario: 1 of 4 nodes fails to Ack a scheduled start in time (see scenario 3 in
[sequence_diagrams.md](sequence_diagrams.md)). **Recommended default: proceed with the
nodes that did Ack, surface a clear warning naming the excluded node(s), and let the
operator decide** whether to retry that node's shot separately or accept the partial
take. This is a product/UX decision, not a hard architectural constraint — present as
the default, not the only allowed behavior; a config flag to instead abort-all could be
added later if a particular shoot needs strict all-or-nothing takes.

## Session recovery edge case: grace window expiry mid-recording

If a node reconnects *after* the 60-second grace window (e.g. 90s after dropping), it is
treated as a brand-new session (`connection_lifecycle.md`). Critically: **the video file
already on the phone is not lost** — the camera plugin wrote it locally the whole time,
independent of any server-side session bookkeeping. The new session simply doesn't know
about that file's provenance automatically; it still shows up in that node's `/videos`
listing (or its future WS/upload equivalent) and can be uploaded normally. No footage is
silently lost even when the server-side session identity resets.

## Data-loss prevention principle (explicit invariant)

**Local recording must never be gated on network state.** This is already true today —
the `camera` plugin writes to local storage regardless of whether the HTTP
controller/WS connection is alive — and it must remain true through this entire
redesign. WS/network failures are allowed to affect the *control/orchestration* layer
(a node might miss a stop command and keep recording longer than intended, or fail to
receive a synchronized start), but they must never stop or corrupt an already-in-progress
local recording. Every failure-recovery decision above is designed around this: the
network layer degrades gracefully around a local recording process that keeps running
regardless.

## Chaos scenarios to eventually script (not run yet, this pass is docs-only)

- Wi-Fi AP drop mid-recording (simulates scenario 4 in `sequence_diagrams.md`).
- AP reboot with all N nodes reconnecting simultaneously (tests reconnect-jitter, checks
  nodes don't thundering-herd the server).
- PC sleep/resume (Director-side interruption — not yet covered by any doc; flag as an
  open gap for a future pass).
- Phone screen-lock during recording — ties directly to the `keepScreenOn` work already
  planned in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); don't duplicate that
  plan's content here, just note the dependency.
