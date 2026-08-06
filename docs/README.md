/# docs

Architecture documentation for the distributed multi-camera platform redesign
(Phase 0 — docs before code, per the project's own rule: no production networking code
until the design is written down and agreed on).

Recommended reading order:

1. [network_architecture.md](network_architecture.md) — umbrella doc, read first
2. [protocol_specification.md](protocol_specification.md)
3. [clock_synchronization.md](clock_synchronization.md)
4. [scheduler.md](scheduler.md)
5. [connection_lifecycle.md](connection_lifecycle.md)
6. [sequence_diagrams.md](sequence_diagrams.md) — consistency check across all of the above
7. [failure_recovery.md](failure_recovery.md)

Also see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — the pre-existing mobile-app
feature backlog (keep-screen-on, in-app settings, stable device roles), which these
architecture docs are written to be consistent with, not duplicate.
