# server/device_registry

DeviceRegistry: the authoritative UUID → node-metadata store (capabilities, last-known
IP, role/slot, last-seen timestamp). Devices are identified by `deviceId` (UUID), never
by IP — IPs change across reconnects/networks, UUIDs don't.

See `docs/protocol_specification.md` §Session Layer.
