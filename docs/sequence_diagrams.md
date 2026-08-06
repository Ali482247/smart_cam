# Sequence Diagrams

Synthesis doc — walks through end-to-end scenarios spanning
[network_architecture.md](network_architecture.md),
[protocol_specification.md](protocol_specification.md),
[clock_synchronization.md](clock_synchronization.md),
[scheduler.md](scheduler.md), [connection_lifecycle.md](connection_lifecycle.md), and
[failure_recovery.md](failure_recovery.md). If a scenario here doesn't line up with one
of those docs, that doc is wrong and needs fixing — this doc is the consistency check.

## 1. Node connect + handshake + first clock-sync burst

```
Node                                    Server
 │──── WS connect ───────────────────────►│
 │──── Hello{device_id,...} ─────────────►│
 │◄─── Welcome{session_id, server_time} ──│
 │  (promoted to CONNECTED_IDLE)
 │──── ClockSyncRequest{t0} ──────────────►│   ×8, ~200ms apart
 │◄─── ClockSyncReply{t0,t1,t2} ───────────│
 │  (compute offset, discard outliers, average)
 │  (node now has an offset estimate; ready for ScheduledCommand)
```

## 2. Synchronized start-recording across 3 nodes

```
Dashboard → Gateway → Scheduler: "start recording"
Scheduler → ConnectionManager: get offset/RTT_p99 for nodes A,B,C
Scheduler: leadTimeMs = max(...) + 50ms
Scheduler: executeAtServerMs = now + leadTimeMs

Scheduler ──ScheduledCommand{execute_at_ms}──► A  (parallel)
Scheduler ──ScheduledCommand{execute_at_ms}──► B  (parallel)
Scheduler ──ScheduledCommand{execute_at_ms}──► C  (parallel)

A ──Ack{OK}──► Scheduler
B ──Ack{OK}──► Scheduler
C ──Ack{OK}──► Scheduler
   (all received before executeAtServerMs - 200ms)

[countdown elapses locally on each node, using its own offset-adjusted timer]

A: starts recording, sends Event{RECORDING_STARTED}
B: starts recording, sends Event{RECORDING_STARTED}
C: starts recording, sends Event{RECORDING_STARTED}

Gateway → Dashboard: all 3 confirmed recording (UI updates)
```

## 3. Node misses the Ack deadline

```
A ──Ack{OK}──► Scheduler   (in time)
B ──Ack{OK}──► Scheduler   (in time)
C: (no Ack by executeAtServerMs - 200ms)

Scheduler faces a policy branch (see failure_recovery.md §Partial-batch policy):

Branch 1 — proceed with partial:
  Scheduler proceeds with A, B. Surfaces "C did not confirm, excluded from this take"
  warning to Dashboard. Operator can manually retry C for a subsequent take.

Branch 2 — abort all:
  Scheduler sends CancelCommand{command_id} to A and B (best-effort; if they already
  started, this becomes a stop-immediately follow-up). Surfaces "recording aborted: C
  unresponsive" to Dashboard. Operator retries the whole batch.

Recommendation: Branch 1 by default (see failure_recovery.md) — losing one node's shot
is usually better than losing the whole take, but this is a product decision the
operator should be able to override.
```

## 4. Node disconnects mid-recording, reconnects within grace window

```
A: CONNECTED_ACTIVE (recording)
[Wi-Fi drop]
Server: 3 missed heartbeats (15s) → A marked SUSPECT
Server: 6 missed heartbeats (30s) → A marked OFFLINE, fires Event{DEVICE_DISCONNECTED}
Dashboard: shows A as disconnected, but note — A's camera plugin never stopped, footage
           keeps recording locally regardless of network state (invariant, see
           failure_recovery.md).

[45s after drop, within the 60s grace window]
A ──── WS reconnect ────────────────────►│
A ──── Hello{same device_id} ───────────►│
Server: within grace window, no other session claimed this device_id
       → SESSION_RECOVERY: resume existing Session (recording=true carried over)
Server ◄─── Welcome{same session_id, server_time} ───
A: re-runs clock-sync burst (offset re-measured, not reused)
A ──── Heartbeat{recording: true} ──────►│
Server: Event{DEVICE_CONNECTED} fires again; Dashboard shows A back online, still recording
```

## 5. Video upload after stop

```
Scheduler → A: ScheduledCommand{STOP, execute_at_ms}
A: Ack{OK}
[countdown elapses]
A: stops recording, writes local file, sends Event{RECORDING_STOPPED}
A: (independently of the still-open WS control connection)
A ──HTTP resumable upload, chunked, checksummed──► UploadService
A ──Event{UPLOAD_STARTED}──► (over WS, informational)
   ... chunks continue while A's WS connection remains free for the NEXT command ...
A ──Event{UPLOAD_COMPLETED}──► (over WS)
```
Note: the control-plane WS connection and the upload HTTP connection are fully
independent — a slow upload never blocks A from receiving and Acking the next
`ScheduledCommand`.

## 6. Duplicate / out-of-order command delivery

```
Scheduler ──ScheduledCommand{seq=41, command_id=X}──► A
[Ack from A lost in transit — Scheduler never sees it]
Scheduler: retry (no Ack within timeout) ──ScheduledCommand{seq=41, command_id=X}──► A  (retransmit, same seq)
A: dedup cache already has seq=41 for this session → does NOT re-execute the command
A: re-sends Ack{command_id=X, OK}   (so the sender's retry loop terminates cleanly)
Scheduler: receives Ack, stops retrying. Recording was only started once.
```

## 7. New node joins mid-session

```
[Session already running with nodes A, B, C — a ScheduledCommand for "start" already
 broadcast and executing]

D ──── WS connect, Hello, Welcome, clock-sync burst ────► (joins CONNECTED_IDLE)

D is NOT included in the already-broadcast ScheduledCommand — it predates D's join.
D shows as "connected, idle" in Dashboard. Operator must issue a new command (e.g.
"start" again, targeting only D, or "stop all + start all fresh" if simultaneity with
A/B/C is required for this take) — the Scheduler never retroactively includes a late
joiner in a command that already has an executeAtServerMs in the past or near-future
for other nodes.
```
