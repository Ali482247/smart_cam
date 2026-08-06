# server/camera

CameraService: server-side representation of each node's camera/recording state
(mirrors the `StatusUpdate`/`Event` messages received over WebSocket).

Must never import anything from `server/network` — it only reacts to already-decoded
protocol messages handed to it by the connection layer (see the strict layering rule in
`docs/network_architecture.md`).
