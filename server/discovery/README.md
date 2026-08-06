# server/discovery

`DiscoveryProvider` interface (`start()` / `stop()` / `onNodeFound(callback)`) so multiple
discovery mechanisms can coexist without touching `ConnectionManager` or `DeviceRegistry`.

- Phase 1: `UdpProbeDiscovery` — today's mechanism (PC broadcasts `THREE_CAM_DISCOVER` on UDP,
  phones reply unicast), ported as-is behind the interface. No wire-format change.
- Phase 3: `MdnsDiscovery` added alongside it (additive, not a replacement).

See `docs/network_architecture.md` §Discovery Layer for the interface contract and migration rationale.
