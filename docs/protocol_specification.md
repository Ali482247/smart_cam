# Protocol Specification

See [network_architecture.md](network_architecture.md) for how this layer fits into the
whole system, and [clock_synchronization.md](clock_synchronization.md) /
[scheduler.md](scheduler.md) for how `ClockSyncRequest/Reply` and `ScheduledCommand` are
actually used.

## Design goals

- Binary, versioned, extensible via `oneof` without breaking older clients.
- Self-describing enough to support dedup and ordering without a schema round-trip per
  message (sequence numbers live in the Envelope itself, not buried in a payload).
- Never JSON for commands — JSON's whitespace/field-order variability makes fixed-size,
  low-latency parsing harder to reason about at the <10ms budget this system targets.

## Envelope

Every message, in both directions, is wrapped in one `Envelope`:

```protobuf
syntax = "proto3";
package threecam.v1;

message Envelope {
  uint32 protocol_version = 1;
  string app_version      = 2;
  string device_id        = 3;   // client-generated UUIDv4 (see network_architecture.md §Device Identity)
  string session_id       = 4;   // assigned by server on Welcome, echoed by client thereafter
  uint64 sequence_number  = 5;   // monotonic per (device_id, session_id) — dedup + ordering key
  int64  timestamp_ms     = 6;   // sender's local clock at send time, epoch ms

  oneof payload {
    Hello            hello       = 10;
    Welcome          welcome     = 11;
    Heartbeat        heartbeat   = 12;
    ClockSyncRequest clock_req   = 13;
    ClockSyncReply   clock_reply = 14;
    ScheduledCommand sched_cmd   = 15;
    Ack              ack         = 16;
    StatusUpdate     status      = 17;
    Event            event       = 18;
  }
}
```

## Payload messages

```protobuf
message Hello {
  string device_name   = 1;
  string manufacturer   = 2;
  string os_version     = 3;
  int32  device_slot     = 4;  // 0 if unassigned
  string device_label   = 5;
  string android_id     = 6;   // optional debug metadata only, never the canonical identity
}

message Welcome {
  string session_id       = 1;
  uint32 protocol_version = 2;
  int64  server_time_ms   = 3;
  string error            = 4;  // non-empty => reject/degrade, see Versioning below
}

message Heartbeat {
  float  battery_pct         = 1;
  uint64 free_storage_bytes  = 2;
  uint64 total_storage_bytes = 3;
  float  temperature_c       = 4;  // if available; 0 = unavailable
  bool   recording           = 5;
}

message ClockSyncRequest {
  int64 t0_ms = 1;  // node's local send time
}

message ClockSyncReply {
  int64 t0_ms = 1;  // echoed from request
  int64 t1_ms = 2;  // server receive time
  int64 t2_ms = 3;  // server send time
}

message ScheduledCommand {
  enum Type { START = 0; STOP = 1; TOGGLE = 2; }
  Type   type            = 1;
  int64  execute_at_ms    = 2;  // server clock epoch ms — node converts via its offset, see clock_synchronization.md
  string command_id       = 3;  // Ack correlation key, independent of sequence_number
  string camera_name      = 4;
  string session_label    = 5;  // e.g. shared recording session id across nodes
  uint32 record_index      = 6;
}

message Ack {
  string command_id = 1;
  enum Result { OK = 0; REJECTED = 1; ALREADY_DONE = 2; }
  Result result = 2;
}

message StatusUpdate {
  bool   recording           = 1;
  float  actual_fps          = 2;
  string active_video_name   = 3;
  int64  recording_started_at_ms = 4;
}

message Event {
  enum Type {
    DEVICE_CONNECTED    = 0;
    DEVICE_DISCONNECTED = 1;
    RECORDING_STARTED   = 2;
    RECORDING_STOPPED   = 3;
    UPLOAD_STARTED      = 4;
    UPLOAD_COMPLETED    = 5;
    STORAGE_WARNING     = 6;
    BATTERY_WARNING     = 7;
    CONNECTION_LOST     = 8;
  }
  Type   type    = 1;
  string detail  = 2;  // free-form, e.g. "free=512MB" for STORAGE_WARNING
}
```

## ACK / Retry / Timeout / Dedup / Ordering

- **Critical messages** (`ScheduledCommand`, and any future message marked critical)
  require an `Ack` within a timeout — 2 seconds default for control commands, tunable
  per deployment.
- **Retry**: sender retries up to 3 times with backoff (300ms / 600ms / 1200ms — matches
  the table in [failure_recovery.md](failure_recovery.md)) if no `Ack` arrives.
- **Dedup**: receiver keys on `(device_id, session_id, sequence_number)` and caches the
  last 256 sequence numbers seen per session; a replayed/retransmitted message with an
  already-seen key is dropped, but the receiver still re-sends the original `Ack` (so a
  sender that only lost the *reply*, not the original delivery, doesn't spuriously retry
  forever — see the duplicate-delivery scenario in
  [sequence_diagrams.md](sequence_diagrams.md)).
- **Ordering**: receiver processes strictly increasing `sequence_number` per session; a
  message arriving slightly out of order is buffered briefly (small window) in case the
  gap fills in; anything older than the current watermark is dropped and logged, never
  processed out of order.

## Versioning

`protocol_version` is checked at `Hello`/`Welcome` time. If the server can't handle the
client's major version, `Welcome.error` is set to a human-readable reason and the
connection is closed cleanly rather than the server attempting to interpret bytes it
doesn't understand — silent misinterpretation of a version-mismatched payload is exactly
the class of bug this field exists to prevent.

## Session Layer fields

| Field | Set when | Travels on |
|---|---|---|
| `device_id`, `capabilities` (device_name/manufacturer/os_version) | Once, at `Hello` | Hello |
| `session_id` | Once, at `Welcome` | Welcome, then echoed on every subsequent Envelope |
| `battery_pct`, `free_storage_bytes`, `temperature_c`, `recording` | Every 5s | Heartbeat |
| `recording`/`upload` state transitions | Event-driven | Event, StatusUpdate |

## Identity decision (restated from network_architecture.md)

`device_id` is a **client-generated UUIDv4**, created once and persisted in
`shared_preferences` under `session_device_uuid`. It is never derived from IP, and
`android_id` is carried only as optional debug metadata inside `Hello`. Implementers:
use exactly this shared_preferences key name — don't invent a divergent one.

## Codegen tooling (open, flagged for Phase 1 vs Phase 2)

The Flutter project has no protobuf tooling today (`mobile/three_cam_mobile/pubspec.yaml`
has no `protobuf`/`grpc` dependency). Two options:

- **Phase 1 (recommended):** hand-roll a minimal binary reader/writer for just the
  Envelope + payload subset actually used — avoids pulling in a full protobuf-dart
  toolchain for a 4-device pilot, keeps the mobile build simple.
- **Phase 2:** switch to full `protoc`-generated Dart bindings once the schema stabilizes
  and the team is ready to add the build-step dependency.

This is a tooling call, not an architecture call — the wire format above is the same
either way.
