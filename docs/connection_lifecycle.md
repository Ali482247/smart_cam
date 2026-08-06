# Connection Lifecycle

See [network_architecture.md](network_architecture.md) for where `ConnectionManager`
sits, [protocol_specification.md](protocol_specification.md) for the `Hello`/`Welcome`/
`Heartbeat` messages referenced below, and
[clock_synchronization.md](clock_synchronization.md) for what happens to offset state
across a reconnect.

## States

```
DISCONNECTED
   │  connect()
   ▼
CONNECTING
   │  WS handshake completes
   ▼
HANDSHAKING            (Hello sent, waiting for Welcome)
   │  Welcome received
   ▼
CONNECTED_IDLE  ◄──────────────────┐
   │  ScheduledCommand executes    │ recording stops
   ▼                               │
CONNECTED_ACTIVE (recording) ──────┘
   │  connection drops (any state above)
   ▼
RECONNECTING
   │  reconnect succeeds within grace window
   ▼
SESSION_RECOVERY ──► CONNECTED_IDLE (state resumed)
   │  grace window expires / reconnect fails
   ▼
DISCONNECTED
```

## Handshake sequence

1. Node opens the WS connection, sends `Hello{device_id, device_name, manufacturer,
   os_version, device_slot, device_label, android_id}`.
2. Server responds `Welcome{session_id, protocol_version, server_time_ms, error}`.
3. Only after a valid `Welcome` (empty `error`) is the connection promoted to
   `CONNECTED_IDLE`.
4. Immediately after promotion, the clock-sync burst (8 samples, see
   `clock_synchronization.md`) begins — a node is not considered "ready" for scheduled
   commands until it has at least one offset estimate.

## Heartbeat / keepalive

- Every 5 seconds, node → server: `Heartbeat{battery_pct, free_storage_bytes,
  total_storage_bytes, temperature_c, recording}`.
- Server tracks `lastSeenAt` per node.
- **3 missed heartbeats (15s)** → node marked `SUSPECT` (still shown connected in
  Dashboard, but flagged).
- **6 missed heartbeats (30s)** → node marked `OFFLINE`, fires a `DeviceDisconnected`
  event (see Event Layer in `network_architecture.md`).

## Reconnect policy (mobile client)

Exponential backoff: **1s, 2s, 4s, 8s, capped at 15s**, each delay jittered ±20% to
avoid every node retrying in lockstep after a shared network blip (e.g. AP reboot). On
reconnect, the node presents the **same** `device_id` and its last known `session_id`;
the server decides fresh-session vs. resume based on the grace window below.

## Session recovery

- If reconnection happens within a **60-second grace window** of the disconnect, and no
  other connection has since claimed that `device_id`'s slot, the server **resumes** the
  existing Session object — recording state, role/slot, etc. carry over. No restart
  command is needed; if the node was `CONNECTED_ACTIVE` (recording) when it dropped, and
  the local camera plugin never stopped recording (network state never gates local
  recording — see the data-loss-prevention invariant in
  [failure_recovery.md](failure_recovery.md)), it simply resumes reporting status as
  still recording.
- If the grace window has expired, the reconnect is treated as a **new session** —
  capability negotiation (`Hello`/`Welcome`) runs again from scratch, and clock-sync
  offset is re-measured (never reused from before the gap, per
  `clock_synchronization.md`).

## One-active-session-per-node invariant

If a second connection arrives claiming a `device_id` that already has a `CONNECTED_*`
session (e.g. the phone app restarted without a clean disconnect), the server closes the
**older** connection — newest connection wins — and logs a warning event. This avoids
ever having two live sessions issuing conflicting state for the same physical device.

## ConnectionManager responsibilities (recap)

Connection pool, reconnect orchestration (server side: accepting the new connection and
running session-recovery logic), heartbeat tracking, per-node metrics (RTT samples feed
`scheduler.md`'s lead-time calculation; heartbeat gaps feed a rough packet-loss
estimate), and the hookup into `DeviceRegistry` for identity/capability lookups.

## Cross-references

- Failure-mode matrix and retry/backoff numeric table: [failure_recovery.md](failure_recovery.md).
- What "resume" means for clock-sync state specifically: [clock_synchronization.md](clock_synchronization.md) §On reconnect.
