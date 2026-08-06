"""Manual multi-device smoke test for the new WS networking core (server/gateway).

Starts the Gateway (WebSocketServer + UDP discovery + heartbeat + scheduler) on this
PC and gives you a tiny interactive prompt to list connected phones and trigger a
synchronized start/stop via the Scheduler - exactly what the Dashboard integration will
eventually wrap in a GUI, without waiting for that to land.

Usage:
    python scripts/gateway_smoke_test.py

Then on each phone: open the Three Cam app (the existing HTTP server keeps running
too - this does not require rebuilding anything beyond what was already built for the
WS client). The phone's UDP discovery reply to this PC's probe is also what triggers it
to open a WS connection back here (see mobile/three_cam_mobile/lib/main.dart's discovery
handler) - so within a few seconds of both being on the same Wi-Fi/hotspot, `list`
should show it.

Commands:
    list    - show currently connected device_ids and discovered (UDP) devices
    start   - broadcast a synchronized START to all connected devices
    stop    - broadcast a synchronized STOP to all connected devices
    quit    - stop the gateway and exit
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.gateway.gateway import Gateway, GatewayConfig  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    gateway = Gateway(GatewayConfig())
    print("Starting Gateway (WS on port 8088, UDP discovery on port 8089)...")
    gateway.start()
    print("Gateway running. Open Three Cam on your phones now.")
    print("Commands: list | start | stop | quit\n")

    try:
        while True:
            try:
                command = input("> ").strip().lower()
            except EOFError:
                break

            if command == "list":
                connected = gateway.connected_device_ids()
                discovered = gateway.list_discovered_devices()
                print(f"Connected over WS ({len(connected)}): {connected}")
                print(
                    "Discovered over UDP "
                    f"({len(discovered)}): "
                    f"{[(node.device_id, node.ip, node.name) for node in discovered]}"
                )
            elif command == "start":
                result = gateway.start_recording(camera_name="one")
                print(f"START -> acked={result.acked} missing={result.missing_ack} "
                      f"excluded={result.excluded_missing_data}")
            elif command == "stop":
                result = gateway.stop_recording(camera_name="one")
                print(f"STOP  -> acked={result.acked} missing={result.missing_ack} "
                      f"excluded={result.excluded_missing_data}")
            elif command in ("quit", "exit", "q"):
                break
            elif command == "":
                continue
            else:
                print("Unknown command. Use: list | start | stop | quit")
    finally:
        print("Stopping Gateway...")
        gateway.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
