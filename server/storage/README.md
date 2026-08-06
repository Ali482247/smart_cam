# server/storage

StorageService: tracks per-node free/total storage (reported on every heartbeat),
triggers `StorageWarning` events when a node drops below the configured threshold.

See `docs/failure_recovery.md` for the storage-exhaustion failure scenario.
