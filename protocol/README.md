# protocol

Canonical `.proto` schema source (Envelope, command payloads, event payloads) — the
shared contract between the Python server (`server/protocol/`) and the Dart mobile
client.

No schemas exist yet. Phase 1 plan: hand-rolled minimal binary codec for the Envelope
subset actually used (Flutter has no protobuf tooling installed today); full
protobuf-dart codegen revisited in Phase 2. See `docs/protocol_specification.md`.
