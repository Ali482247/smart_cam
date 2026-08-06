# server/synchronization

Per-node clock offset / round-trip-time measurement (NTP-style 4-timestamp exchange).
Feeds `offsetUncertaintyMs` into the Scheduler's lead-time calculation.

Algorithm, sampling strategy, and accuracy validation plan in `docs/clock_synchronization.md`.
