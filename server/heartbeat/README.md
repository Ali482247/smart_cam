# server/heartbeat

Heartbeat monitor: expects a `Heartbeat` envelope from every connected node every 5s;
feeds `ConnectionManager`'s offline detection (15s → SUSPECT, 30s → OFFLINE).

See `docs/connection_lifecycle.md` §Heartbeat/Keepalive.
