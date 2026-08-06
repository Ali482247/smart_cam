# server/scheduler

Scheduler Service: computes synchronized `executeAt` timestamps, broadcasts scheduled
commands (Start/Stop/Toggle) to all target nodes, tracks ACKs, retries/aborts on missed
deadlines.

Algorithm and worked numeric example in `docs/scheduler.md`. Depends on
`server/synchronization` for per-node clock offset/RTT estimates.
