# server/network

WebSocket transport server (asyncio, e.g. `websockets` or `aiohttp`). Binary frames only,
one persistent connection per CameraNode, open for the whole session — no HTTP polling.

Owns nothing about camera or scheduling business logic (see `docs/network_architecture.md`,
"Strict layering rule": camera code must never know about WebSocket, and vice versa).

See `docs/network_architecture.md` §Transport Layer and `docs/protocol_specification.md`
for the Envelope framing this layer reads/writes.
