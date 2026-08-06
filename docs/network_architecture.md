# Network Architecture

## Purpose & Scope

This is the umbrella document for the distributed multi-camera platform's networking
redesign. It explains *why* each layer exists and how the layers fit together. The other
six docs go deep on one layer each and cross-reference this one for context:

- [protocol_specification.md](protocol_specification.md) — wire format
- [clock_synchronization.md](clock_synchronization.md) — offset/RTT measurement
- [scheduler.md](scheduler.md) — synchronized command execution
- [connection_lifecycle.md](connection_lifecycle.md) — per-node connection state machine
- [sequence_diagrams.md](sequence_diagrams.md) — end-to-end scenarios
- [failure_recovery.md](failure_recovery.md) — what happens when things break

## Why this redesign, not new features

The current prototype (see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the
mobile-side feature backlog) already does the hard product-visible part: it records
video reliably and controls several phones from one PC. What it does *not* have is any
guarantee about *how simultaneously* those phones start/stop, or any resilience when a
phone drops off Wi-Fi mid-session. Those two gaps — synchronization and reliability — are
what separate a prototype from a professional system, and they live entirely in the
networking core. Adding product features (live preview, camera groups, roles) on top of
today's HTTP fire-and-forget model would just mean rebuilding them again once the core
changes. So this redesign happens first.

## System Overview

```
                         ┌─────────────────────────────────────┐
                         │            Director PC               │
                         │                                       │
  ┌───────────┐  direct  │  ┌────────┐         ┌──────────────┐ │
  │ Dashboard │◄────────►│  │Gateway │◄───────►│ asyncio core │ │
  │ (Tk today)│ in-proc  │  │(Python │         │ (event loop, │ │
  │           │  call    │  │ class) │         │ own thread)  │ │
  └───────────┘          │  └───┬────┘         └──────┬───────┘ │
                         │      │                      │         │
                         │  ┌───┴──────┬───────────┬───┴────────┐│
                         │  │CameraSvc │Scheduler  │Connection  ││
                         │  │StorageSvc│SyncSvc    │Manager     ││
                         │  │UploadSvc │MetadataSvc│DeviceReg.  ││
                         │  └──────────┴───────────┴────────────┘│
                         └───────┬───────────────────┬────────────┘
                                 │ WS + protobuf      │ HTTP (upload)
                                 │ (persistent,       │ (resumable,
                                 │  binary frames)     │  chunked)
                    ┌────────────┼──────────┬─────────┴──────┐
                    ▼            ▼          ▼                 ▼
              CameraNode1  CameraNode2  CameraNode3  ...  CameraNode(N)
```

The Director never records video. It orchestrates: discovers nodes, holds one persistent
WS connection per node, schedules synchronized start/stop, and receives status/events.
Video bytes only ever flow node → UploadService, over plain HTTP, on a separate path from
the control-plane WS connection — a slow/interrupted upload must never block or jitter
the control plane, and vice versa.

## Layer Catalogue

| Layer | Responsibility | Must NOT know about | Maps to |
|---|---|---|---|
| Discovery | Find CameraNodes on the network | Connection state, protocol payloads | `server/discovery` |
| Transport | Move binary frames over a persistent WS connection | Message *meaning*, camera state | `server/network` |
| Protocol | Encode/decode Envelope + payloads, versioning | Transport mechanics, business logic | `server/protocol`, `protocol/` |
| Synchronization | Measure clock offset/RTT per node | Scheduling decisions, camera state | `server/synchronization` |
| Connection | Pool, reconnect, heartbeat, session state, metrics | Camera/recording business logic | `server/connection` |
| Session | Per-node identity, capabilities, state snapshot | Transport implementation | `server/device_registry` |
| Event | Internal pub/sub of domain events | Transport, UI | in-process, consumed by `server/gateway` |
| Gateway | Single Python-interface entry point for Dashboard → backend services (in-process call in Phase 1) | Mobile client existence, transport implementation | `server/gateway` |
| gRPC | Reserved for internal service-to-service calls once backend services run as separate processes (not used in Phase 1) | Mobile client existence | `server/grpc` |
| Upload | Resumable video transfer | Control-plane WS state | `server/upload` |
| Scheduling | Compute `executeAt`, broadcast, track ACKs | Camera plugin API, transport bytes | `server/scheduler` |

**Strict layering rule** (non-negotiable, applies to every layer above): camera code
must never import or reference anything from the transport layer, and the transport
layer must never import or reference anything camera-specific. Scheduling and
synchronization are each independently replaceable — a different scheduling algorithm
or a different clock-sync method must be swappable without touching transport or
protocol code. All cross-layer calls go through interfaces, never concrete classes
reaching across layer boundaries. No business logic in transport, no UI logic in
networking.

## Discovery Layer: interface, not a fixed mechanism

Today's mechanism (PC broadcasts `THREE_CAM_DISCOVER` on UDP port 8089, each phone
replies unicast with a JSON status blob — see `mobile/three_cam_mobile/lib/main.dart`
lines ~483-519) already works reliably at 4 devices and needs zero mobile-side change.
mDNS/Bonjour is the eventual target for larger deployments, but it is a **different
model**: phones self-announce (`_threecam._tcp.local`) instead of the PC probing for
them. Because these are genuinely different control flows, not a drop-in swap, the
Discovery Layer is designed behind an interface so both can exist side by side:

```
interface DiscoveryProvider:
    start() -> None
    stop() -> None
    onNodeFound(callback: (NodeInfo) -> None) -> None
```

- **Phase 1 (now):** only `UdpProbeDiscovery` is implemented — the current wire format,
  ported as-is behind this interface. This redesign pass does not change discovery
  behavior at all, only wraps it.
- **Phase 3 (later):** `MdnsDiscovery` is added as a second, concurrently-running
  provider. `ConnectionManager`/`DeviceRegistry` consume `NodeInfo` events from whichever
  provider(s) are active and don't know or care which one found a given node.

| | UDP-probe (today) | mDNS (Phase 3) |
|---|---|---|
| Direction | PC-initiated pull | Phone-initiated self-announce |
| Works today | Yes, tested on real devices | Not implemented |
| OEM risk | None known | Some Android OEMs require a multicast lock; can be flaky |
| Router/VLAN risk | Broadcast domain must be shared (already required today) | Some routers filter mDNS across VLANs — worse at 50-device scale across multiple APs |
| Change required | None | Mobile-side: register as an mDNS service |

## Threading Model

`three_cam_controller.py`'s Tk `mainloop()` is a blocking C call with no `await` points —
it cannot share a thread with an asyncio event loop. The asyncio core (network,
connection, scheduler, synchronization, camera/upload/storage state, device registry,
heartbeat) all run as tasks on **one** event loop in its own thread. The Dashboard keeps
its own Tk mainloop in a separate thread.

**Decision: no gRPC for this boundary.** Dashboard and the asyncio core are two threads
inside the *same process* — there is no process/machine boundary here, so a network
protocol (gRPC, sockets, HTTP) between them would add serialization, port management,
and a whole class of "gRPC channel failed" errors for something that can be a plain
function call. Instead:

- `Gateway` is a plain Python class exposing the same methods `CameraService`,
  `Scheduler`, etc. need (`start_recording()`, `get_status()`, `discover()`, ...) —
  called directly, in-process.
- Because the Gateway's methods run on the asyncio event loop but must be invoked from
  Tk's thread, the call goes through
  [`asyncio.run_coroutine_threadsafe(coro, loop)`](https://docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe),
  which is the standard, supported way to hand work from a foreign thread to a running
  event loop. It returns a `concurrent.futures.Future`.
- Dispatching the result back to the Tk thread reuses the pattern the Dashboard
  **already has today** (`ControllerApp.run_background` in `three_cam_controller.py`:
  a worker thread does the work, then `root.after(0, callback)` marshals the result back
  onto Tk's own thread) — the worker thread just blocks on the `Future` from
  `run_coroutine_threadsafe` instead of making an HTTP call directly.

This keeps the Gateway defined as a clean interface (a fixed set of methods, not
"whatever gRPC generates"), so **if** Dashboard is ever split into a separate process
(e.g. a remote web dashboard), wrapping that same interface behind gRPC is a contained,
mechanical change — not a rewrite. gRPC is reserved for the actual case that needs it:
internal service-to-service calls once/if backend services (CameraService,
StorageService, etc.) are split into separate processes in Phase 2. Introducing it here,
now, for two threads in one process would be solving a distribution problem that doesn't
exist yet — the strict layering rule (interfaces over concrete transports) is satisfied
either way, so nothing is lost by deferring gRPC until there's an actual process
boundary to cross.

## Device Identity

Devices are identified by `deviceId`, never by IP (IPs change across networks/reconnects;
a stable identity is required for session recovery and role/slot persistence). Today
`deviceId` comes from Android's `Settings.Secure.ANDROID_ID` (native, Android-only — see
`MainActivity.kt`). Since the target architecture must eventually support iOS
CameraNodes, and the spec calls for UUID-based identity, `deviceId` becomes an
**app-generated UUIDv4**, created once in Dart on first launch and persisted via
`shared_preferences` under the key `session_device_uuid`. `ANDROID_ID` is kept as a
secondary, Android-only debug field in the Session Layer (useful for support: "was this
the same physical Android install") — it is not the canonical identity going forward.

## Scaling Notes (4 → 20 → 50 nodes)

- Connection pool: `ConnectionManager` must hold N persistent WS connections; at 50
  nodes this is still small for asyncio (thousands of connections are normal), not a
  concern by itself.
- Heartbeat fan-out: 50 nodes × 1 heartbeat/5s = 10 msg/s inbound, negligible.
- Scheduler broadcast: sending a `ScheduledCommand` to 50 nodes concurrently and waiting
  for 50 ACKs before a deadline is the part that needs load-testing (see
  [scheduler.md](scheduler.md) worked example) — RTT variance across more devices on a
  shared AP increases the lead-time safety margin needed.
- Gateway: single in-process entry point for Dashboard; flagged here as a candidate
  bottleneck if the Dashboard ever needs high-frequency polling of many nodes' status —
  not solved in this pass, just noted for Phase 2 (when/if it moves behind gRPC).

## Phased Rollout Plan

Mapped to the maturity staging already agreed on for the product:

| Product stage | Architecture phase | Contents |
|---|---|---|
| **MVP (~70%)** | *Already mostly done* | Reliable recording, multi-device control, start/stop, video download — today's HTTP prototype qualifies. |
| **Production v1.0 (~90%)** | **Phase 1** (this redesign, next implementation pass) | Persistent WS + protobuf Envelope, ConnectionManager, DeviceRegistry, Heartbeat, ACK/Retry, ClockSync, Scheduler with `executeAt`. Discovery stays UDP-probe (wrapped in `DiscoveryProvider`). Dashboard stays Tk, talks to the asyncio core via a direct in-process `Gateway` call (`asyncio.run_coroutine_threadsafe`) — no gRPC yet. |
| **Production v1.0 (cont.)** | **Phase 2** | *If and only if* backend services need to run as separate processes to scale independently: split Gateway/CameraService/StorageService/UploadService/SynchronizationService/MetadataService behind gRPC. Full protobuf-dart codegen (replacing Phase 1's hand-rolled Envelope codec). |
| **Enterprise (100%)** | **Phase 3** | mDNS as additive discovery, scale-tested to 50 nodes, live preview, camera groups/roles, cloud sync, higher fault tolerance. |

## Open Questions Already Resolved (recorded for traceability)

1. Discovery: keep UDP-probe in Phase 1, add mDNS in Phase 3 behind `DiscoveryProvider` — **decided**.
2. Device identity: app-generated UUIDv4 in Dart, `ANDROID_ID` demoted to debug metadata — **decided**.
3. Backend language: Python 3 + asyncio — **decided**.
4. Repo layout: monorepo restructure applied now (this pass) — **decided**.
