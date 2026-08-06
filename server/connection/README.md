# server/connection

`ConnectionManager`: connection pool, reconnect handling, heartbeat/keepalive plumbing,
per-node session state, connection metrics (RTT, packet-loss estimate).

Enforces the "one active session per deviceId" invariant described in
`docs/connection_lifecycle.md`.
