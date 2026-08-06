# server/gateway

Gateway: a plain Python class — the single entry point the Dashboard calls into; fans
out to CameraService, StorageService, UploadService, SynchronizationService,
MetadataService, DeviceRegistry, Scheduler.

Exists to decouple the Dashboard's UI thread (Tk today, possibly a web UI later) from
the asyncio networking core's event loop, via `asyncio.run_coroutine_threadsafe` — not
via gRPC. Dashboard and the core are two threads in one process, not two processes, so
a network protocol between them would add serialization/port overhead for nothing.
Gateway is still defined as a clean interface (fixed methods, not "whatever gRPC
generates"), so if a real process boundary ever appears (e.g. a remote dashboard),
wrapping it behind gRPC later is a contained change, not a rewrite.

See `docs/network_architecture.md` §Threading Model.
