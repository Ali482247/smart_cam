import http.server
import socket
import socketserver
import sys
from pathlib import Path

PORT = 8090
APK_NAME = "ThreeCam-debug.apk"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def local_ips() -> list[str]:
    ips = []
    hostname = socket.gethostname()
    for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
        ip = item[4][0]
        if ip not in ips and not ip.startswith("127."):
            ips.append(ip)
    return ips


def main() -> int:
    root = Path(__file__).resolve().parent
    apk = root / APK_NAME
    if not apk.exists():
        print(f"APK не найден: {apk}")
        print("Сначала собери APK через BUILD_THREE_CAM_APK.bat")
        return 1

    print("Открой на телефонах одну из ссылок:")
    for ip in local_ips():
        print(f"http://{ip}:{PORT}/{APK_NAME}")
    print("")
    print("Не закрывай это окно, пока телефоны скачивают APK.")

    with socketserver.TCPServer(("", PORT), Handler) as server:
        server.allow_reuse_address = True
        server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
