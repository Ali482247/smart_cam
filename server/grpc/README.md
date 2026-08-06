server/grpc/

This directory intentionally contains no runtime code in Phase 1.

The Director Dashboard (Tkinter) and the asyncio networking core execute
inside the same Python process.

Communication between them happens through the in-process Gateway interface
using asyncio.run_coroutine_threadsafe().

No local gRPC transport is used because there is no process boundary.

This directory exists only as a placeholder for a future distributed backend.

If the backend is ever split into multiple independent services
(CameraService, UploadService, StorageService, Scheduler, etc.),
this directory will contain internal grpc.aio services.

Until that point, it remains unused.

Flutter CameraNode clients will never communicate using gRPC.

Mobile devices communicate only through:

• WebSocket
• Protocol Buffers (or JSON if Phase 1 keeps JSON)

gRPC is reserved exclusively for future service-to-service communication.