import argparse
import json
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, DISABLED, NORMAL, StringVar, Tk, Text, ttk

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# The new networking core (server/) is a sibling of dashboard/, not an installed
# package - add the repo root to sys.path so `from server...` imports resolve
# (network_architecture.md §Threading Model: Dashboard stays on Tk's mainloop and
# talks to the asyncio core only through server/gateway's synchronous Gateway API,
# never touching asyncio primitives or the WebSocket transport directly).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GATEWAY_IMPORT_ERROR = ""
try:
    from server.gateway.gateway import Gateway, GatewayConfig  # noqa: E402
except Exception as error:  # noqa: BLE001 - legacy HTTP dashboard must still open
    Gateway = None
    GatewayConfig = None
    GATEWAY_IMPORT_ERROR = f"{type(error).__name__}: {error}"

CONFIG_NAME = "three_cam_controller_config.json"
SESSION_HISTORY_NAME = "three_cam_session_history.json"
SESSION_HISTORY_LIMIT = 200
DISCOVERY_MESSAGE = "THREE_CAM_DISCOVER"
DEFAULT_CAMERA_NAMES = [
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
]


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def default_config() -> dict:
    return {
        "auto_discover": True,
        "discovery_port": 8089,
        "control_port": 8088,
        "min_phones": 1,
        "timeout_seconds": 1.5,
        "next_index": 0,
        "next_device_slot": 1,
        "min_free_storage_bytes": 1073741824,
        "min_battery_percent": 15,
        "target_video": {
            "width": 1920,
            "height": 1080, 
            "fps": 30,
            "video_bitrate": 8000000,
            "audio_bitrate": 192000,
            "audio_sample_rate": 48000,
        },
        "phones": [],
    }


def load_config() -> dict:
    path = app_dir() / CONFIG_NAME
    config = default_config()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            config.update(json.load(f))
    else:
        save_config(config)
    config["phones"] = assign_camera_names(config.get("phones", []))
    return config


def save_config(config: dict) -> None:
    path = app_dir() / CONFIG_NAME
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_session_history() -> list[dict]:
    path = app_dir() / SESSION_HISTORY_NAME
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_session_history(history: list[dict]) -> None:
    path = app_dir() / SESSION_HISTORY_NAME
    with path.open("w", encoding="utf-8") as f:
        json.dump(history[-SESSION_HISTORY_LIMIT:], f, indent=2, ensure_ascii=False)


def safe_int(value, fallback: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def camera_name_from_slot(slot: int | None) -> str:
    if slot is None or slot < 1:
        return "camera"
    if slot <= len(DEFAULT_CAMERA_NAMES):
        return DEFAULT_CAMERA_NAMES[slot - 1]
    return f"camera_{slot}"


def next_available_slot(config: dict, discovered: list[dict] | None = None) -> int:
    used = {
        safe_int(phone.get("device_slot"))
        for phone in config.get("phones", [])
        if safe_int(phone.get("device_slot")) is not None
    }
    if discovered:
        used.update(
            safe_int(phone.get("device_slot"))
            for phone in discovered
            if safe_int(phone.get("device_slot")) is not None
        )

    slot = int(config.get("next_device_slot", 1))
    while slot in used:
        slot += 1
    config["next_device_slot"] = slot + 1
    return slot


def phone_display_name(phone: dict) -> str:
    return (
        phone.get("device_label")
        or phone.get("camera_name")
        or phone.get("name")
        or phone.get("url")
        or "camera"
    )


def normalize_url(url: str) -> str:
    return url.rstrip("/")


def local_broadcast_addresses() -> list[str]:
    addresses = {"255.255.255.255"}
    hostname = socket.gethostname()
    try:
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = item[4][0]
            if ip.startswith("127."):
                continue
            parts = ip.split(".")
            if len(parts) == 4:
                addresses.add(".".join(parts[:3] + ["255"]))
    except socket.gaierror:
        pass
    return sorted(addresses)


def discover_phones(config: dict, seconds: float = 2.5) -> list[dict]:
    port = int(config.get("discovery_port", 8089))
    control_port = int(config.get("control_port", 8088))
    found: dict[str, dict] = {}
    existing_by_device_id = {
        str(phone.get("device_id")): phone
        for phone in config.get("phones", [])
        if phone.get("device_id")
    }
    existing_by_url = {
        normalize_url(str(phone.get("url"))): phone
        for phone in config.get("phones", [])
        if phone.get("url")
    }

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.25)

        for address in local_broadcast_addresses():
            try:
                sock.sendto(DISCOVERY_MESSAGE.encode("utf-8"), (address, port))
            except OSError:
                pass

        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                data, remote = sock.recvfrom(8192)
            except socket.timeout:
                continue
            try:
                payload = json.loads(data.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if payload.get("app") != "three_cam":
                continue

            ip = payload.get("ip") or remote[0]
            phone_port = int(payload.get("port") or control_port)
            url = f"http://{ip}:{phone_port}"
            name = payload.get("name") or f"camera_{len(found) + 1}"
            device_id = str(payload.get("deviceId") or payload.get("device_id") or url)
            existing = existing_by_device_id.get(device_id) or existing_by_url.get(url)
            device_slot = safe_int(
                payload.get("deviceSlot") or payload.get("device_slot"),
                safe_int(existing.get("device_slot")) if existing else None,
            )
            device_label = str(
                payload.get("deviceLabel")
                or payload.get("device_label")
                or (existing.get("device_label") if existing else "")
                or name
            )

            item = dict(existing or {})
            if device_slot is None:
                device_slot = next_available_slot(config, list(found.values()))
            item.update(
                {
                    "name": str(name),
                    "url": url,
                    "device_id": device_id,
                    "device_name": str(payload.get("deviceName") or payload.get("device_name") or name),
                    "device_slot": device_slot,
                    "device_label": device_label,
                }
            )
            if not item.get("camera_name"):
                item["camera_name"] = safe_name(device_label) or camera_name_from_slot(device_slot)
            found[device_id] = item

    phones = list(found.values())
    phones.sort(key=lambda item: (safe_int(item.get("device_slot"), 9999), item.get("url", "")))
    return phones


def assign_camera_names(phones: list[dict]) -> list[dict]:
    assigned = []
    for index, phone in enumerate(phones):
        item = dict(phone)
        slot = safe_int(item.get("device_slot"), index + 1)
        item["device_slot"] = slot
        label_name = safe_name(str(item.get("device_label") or ""))
        existing_name = str(item.get("camera_name") or "")
        if label_name and (not existing_name or existing_name in DEFAULT_CAMERA_NAMES):
            item["camera_name"] = label_name
        else:
            item["camera_name"] = existing_name or camera_name_from_slot(slot)
        assigned.append(item)
    return assigned


def configured_phones(config: dict) -> list[dict]:
    phones = [phone for phone in config.get("phones", []) if phone.get("url")]
    return assign_camera_names(phones)


def get_phones(config: dict, *, discover: bool = True) -> list[dict]:
    phones = []
    if discover and config.get("auto_discover", True):
        phones = discover_phones(config)
        if phones:
            config["phones"] = phones
            save_config(config)
    if not phones:
        phones = configured_phones(config)

    min_phones = int(config.get("min_phones", 1))
    if len(phones) < min_phones:
        raise RuntimeError(
            f"Найдено телефонов: {len(phones)}. Нужно минимум {min_phones}. "
            "Открой Three Cam на телефонах и проверь, что все в одной Wi-Fi сети."
        )
    return phones


def request_phone(phone: dict, endpoint: str, timeout: float, method: str = "POST") -> tuple[str, str]:
    name = phone.get("name") or phone["url"]
    url = normalize_url(phone["url"]) + endpoint
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return name, body
    except urllib.error.URLError as error:
        return name, f"ERROR: {error}"
    except TimeoutError:
        return name, "ERROR: timeout"


def get_json(phone: dict, endpoint: str, timeout: float) -> dict:
    url = normalize_url(phone["url"]) + endpoint
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def video_index_from_name(name: str) -> int | None:
    match = re.search(r"_(\d+)\.mp4$", name)
    if not match:
        return None
    return safe_int(match.group(1))


def next_record_index(config: dict, phones: list[dict], timeout: float) -> int:
    if not config.get("scan_remote_video_indexes", False):
        return int(config.get("next_index", 0))

    indexes = []
    with ThreadPoolExecutor(max_workers=max(1, len(phones))) as executor:
        futures = [executor.submit(get_json, phone, "/videos", timeout) for phone in phones]
        for future in as_completed(futures):
            try:
                payload = future.result()
            except Exception:
                continue
            for video in payload.get("videos", []):
                index = video_index_from_name(str(video.get("name", "")))
                if index is not None:
                    indexes.append(index)
    if indexes:
        return max(indexes) + 1
    return int(config.get("next_index", 0))


def download_file(phone: dict, name: str, target: Path, timeout: float) -> None:
    url = normalize_url(phone["url"]) + "/download?name=" + urllib.parse.quote(name)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        target.write_bytes(response.read())


def send_all(config: dict, endpoint: str) -> list[tuple[str, str]]:
    phones = get_phones(config, discover=not endpoint in {"/start", "/stop", "/toggle"})
    timeout = float(config.get("timeout_seconds", 1.5))
    if endpoint == "/start" and config.get("check_ready_before_start", False):
        check_ready_for_recording(config, phones, timeout)
    endpoint_by_phone = build_endpoint_map(config, phones, endpoint)
    results = []
    with ThreadPoolExecutor(max_workers=len(phones)) as executor:
        futures = {
            executor.submit(request_phone, phone, endpoint_by_phone[id(phone)], timeout): phone
            for phone in phones
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results


def build_endpoint_map(config: dict, phones: list[dict], endpoint: str) -> dict[int, str]:
    if endpoint != "/start":
        return {id(phone): endpoint for phone in phones}

    now = datetime.now()
    date_stamp = now.strftime("%Y %m %d")
    time_stamp = now.strftime("%H%M%S")
    timeout = float(config.get("timeout_seconds", 3))
    record_index = next_record_index(config, phones, timeout)
    session_id = f"{now.strftime('%Y%m%d')}_{time_stamp}_{record_index}"
    config["next_index"] = record_index + 1
    save_config(config)

    endpoints = {}
    for phone in phones:
        camera_name = (
            safe_name(str(phone.get("device_label") or ""))
            or phone.get("camera_name")
            or camera_name_from_slot(safe_int(phone.get("device_slot")))
        )
        query = urllib.parse.urlencode(
            {
                "camera": camera_name,
                "date": date_stamp,
                "time": time_stamp,
                "index": str(record_index),
                "session": session_id,
            }
        )
        endpoints[id(phone)] = f"/start?{query}"
    return endpoints


def check_ready_for_recording(config: dict, phones: list[dict], timeout: float) -> None:
    min_free = int(config.get("min_free_storage_bytes", 1073741824))
    min_battery = int(config.get("min_battery_percent", 15))
    warnings = []
    for phone in phones:
        name = phone_display_name(phone)
        try:
            status = get_json(phone, "/status", timeout)
        except Exception as error:
            warnings.append(f"{name}: status error: {error}")
            continue

        free_storage = status.get("freeStorageBytes")
        if isinstance(free_storage, int) and free_storage < min_free:
            warnings.append(
                f"{name}: мало памяти {format_bytes(free_storage)} "
                f"(нужно минимум {format_bytes(min_free)})"
            )

        battery_percent = status.get("batteryPercent")
        charging = bool(status.get("batteryCharging"))
        if isinstance(battery_percent, int) and battery_percent < min_battery and not charging:
            warnings.append(
                f"{name}: низкий заряд батареи {battery_percent}% "
                f"(нужно минимум {min_battery}%, не на зарядке)"
            )
    if warnings:
        raise RuntimeError("Нельзя начать запись:\n" + "\n".join(warnings))


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return "unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024


def download_all(config: dict) -> list[tuple[str, str]]:
    phones = get_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    output_root = app_dir() / "downloaded_videos"
    output_root.mkdir(exist_ok=True)

    results = []
    for phone in phones:
        name = phone_display_name(phone)
        try:
            payload = get_json(phone, "/videos", timeout)
            videos = payload.get("videos", [])
            phone_dir = output_root / safe_name(name)
            phone_dir.mkdir(exist_ok=True)
            count = 0
            for video in videos:
                video_name = video["name"]
                target = phone_dir / video_name
                if not target.exists():
                    download_file(phone, video_name, target, max(timeout, 30))
                    count += 1
            results.append((name, f"downloaded {count}, total {len(videos)}"))
        except Exception as error:
            results.append((name, f"ERROR: {error}"))
    return results


def clear_videos_all(config: dict) -> list[tuple[str, str]]:
    phones = get_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    config["next_index"] = 0
    save_config(config)
    save_session_history([])
    results = []
    for phone in phones:
        name, body = request_phone(phone, "/clear-videos", timeout, method="POST")
        try:
            payload = json.loads(body)
            if payload.get("ok"):
                results.append((name, f"deleted {payload.get('deleted', 0)}"))
            else:
                results.append((name, f"ERROR: {payload.get('error', body)}"))
        except json.JSONDecodeError:
            results.append((name, body))
    return results


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


def format_results(title: str, results: list[tuple[str, str]]) -> str:
    lines = [title]
    for name, result in results:
        lines.append(f"{name}: {result}")
    return "\n".join(lines)


def status_all(config: dict) -> list[tuple[str, str]]:
    phones = get_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    results = []
    for phone in phones:
        name = phone_display_name(phone)
        try:
            payload = get_json(phone, "/status", timeout)
            results.append((name, format_phone_status(payload)))
        except Exception as error:
            results.append((name, f"ERROR: {error}"))
    return results


def format_phone_status(payload: dict) -> str:
    target = payload.get("targetVideo") or {}
    target_text = (
        f"{target.get('width', '?')}x{target.get('height', '?')} "
        f"{target.get('fps', '?')}fps"
        if isinstance(target, dict)
        else str(target)
    )
    battery_percent = payload.get("batteryPercent")
    battery_text = f"{battery_percent}%" if isinstance(battery_percent, int) else "unknown"
    if payload.get("batteryCharging"):
        battery_text += " (заряжается)"

    parts = [
        f"device={payload.get('deviceName') or payload.get('deviceId') or 'unknown'}",
        f"recording={payload.get('recording')}",
        f"battery={battery_text}",
        f"free={format_bytes(payload.get('freeStorageBytes'))}",
        f"target={target_text}",
    ]
    if payload.get("sessionId"):
        parts.append(f"session={payload['sessionId']}")
    if payload.get("lastVideoName"):
        size = format_bytes(payload.get("lastVideoSizeBytes"))
        parts.append(f"last={payload['lastVideoName']} ({size})")
    return ", ".join(parts)


class ControllerApp:
    def __init__(self, root: Tk, config: dict):
        self.root = root
        self.config = config
        self.recording = False
        self.busy = False
        self.status = StringVar(value="Готово")
        self.record_start_time: float | None = None
        self.timer_var = StringVar(value="00:00:00")
        self.auto_stop_var = StringVar()
        self._timer_job = None
        self._auto_stop_job = None
        self._poll_job = None
        self.device_status_cache: dict[str, dict] = {}
        self.session_history = load_session_history()
        self._session_started_at: dict[str, float] = {}

        # New WS+Scheduler networking core (network_architecture.md), run alongside the
        # legacy HTTP path above - per the migration rules this is additive: the
        # existing "START REC"/"STOP REC" buttons keep using HTTP untouched, and the
        # "SYNC REC" buttons below are the only thing that goes through the Gateway.
        self.ws_recording = False
        self.gateway = None
        self.ws_status = StringVar(value="WS: запускается...")
        if Gateway is not None and GatewayConfig is not None:
            self.gateway = Gateway(GatewayConfig())
        else:
            self.ws_status.set(f"WS: disabled ({GATEWAY_IMPORT_ERROR})")
        if self.gateway is not None:
            try:
                self.gateway.start()
                self.ws_status.set("WS: готов (0 устройств)")
            except Exception as error:  # noqa: BLE001 - must not prevent the legacy dashboard from opening
                self.ws_status.set(f"WS: ошибка запуска ({error})")

        root.title("Three Cam Controller")
        root.geometry("820x560")
        root.minsize(700, 460)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        frame = ttk.Frame(root, padding=14)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Three Cam Controller", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(4, 12))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(0, 12))

        self.discover_button = ttk.Button(buttons, text="Авто поиск", command=self.discover_clicked)
        self.discover_button.pack(side="left", padx=(0, 8))

        self.record_button = ttk.Button(buttons, text="START REC", command=self.toggle_clicked)
        self.record_button.pack(side="left", padx=(0, 8))

        self.status_button = ttk.Button(buttons, text="Проверить", command=self.status_clicked)
        self.status_button.pack(side="left", padx=(0, 8))

        self.download_button = ttk.Button(buttons, text="Скачать видео", command=self.download_clicked)
        self.download_button.pack(side="left", padx=(0, 8))

        self.history_button = ttk.Button(buttons, text="История", command=self.history_clicked)
        self.history_button.pack(side="left")

        timer_frame = ttk.Frame(frame)
        timer_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(timer_frame, text="Таймер записи:").pack(side="left")
        ttk.Label(
            timer_frame, textvariable=self.timer_var, font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=(6, 20))
        ttk.Label(timer_frame, text="Автостоп через (мин, пусто = выкл):").pack(side="left")
        ttk.Entry(timer_frame, textvariable=self.auto_stop_var, width=6).pack(side="left", padx=(6, 0))

        ws_frame = ttk.LabelFrame(frame, text="New networking (WS + Scheduler, synchronized)", padding=8)
        ws_frame.pack(fill="x", pady=(0, 12))

        ws_row = ttk.Frame(ws_frame)
        ws_row.pack(fill="x")

        self.ws_record_button = ttk.Button(ws_row, text="SYNC START", command=self.ws_toggle_clicked)
        self.ws_record_button.pack(side="left", padx=(0, 8))

        self.ws_status_button = ttk.Button(ws_row, text="WS статус", command=self.ws_status_clicked)
        self.ws_status_button.pack(side="left", padx=(0, 8))

        ttk.Label(ws_row, textvariable=self.ws_status).pack(side="left")

        devices = ttk.LabelFrame(frame, text="Devices", padding=8)
        devices.pack(fill="x", pady=(0, 12))

        self.devices_tree = ttk.Treeview(
            devices,
            columns=("slot", "camera", "device", "url", "free", "battery"),
            show="headings",
            height=5,
            selectmode="browse",
        )
        self.devices_tree.heading("slot", text="Slot")
        self.devices_tree.heading("camera", text="Camera name")
        self.devices_tree.heading("device", text="Device")
        self.devices_tree.heading("url", text="URL")
        self.devices_tree.heading("free", text="Free")
        self.devices_tree.heading("battery", text="Battery")
        self.devices_tree.column("slot", width=52, stretch=False)
        self.devices_tree.column("camera", width=110, stretch=False)
        self.devices_tree.column("device", width=150, stretch=True)
        self.devices_tree.column("url", width=190, stretch=True)
        self.devices_tree.column("free", width=90, stretch=False)
        self.devices_tree.column("battery", width=90, stretch=False)
        self.devices_tree.tag_configure("offline", foreground="#c0392b")
        self.devices_tree.pack(fill="x")
        self.devices_tree.bind("<<TreeviewSelect>>", self.device_selected)

        device_editor = ttk.Frame(devices)
        device_editor.pack(fill="x", pady=(8, 0))
        ttk.Label(device_editor, text="Slot").pack(side="left")
        self.device_slot_var = StringVar()
        ttk.Entry(device_editor, textvariable=self.device_slot_var, width=6).pack(side="left", padx=(4, 10))
        ttk.Label(device_editor, text="Camera name").pack(side="left")
        self.camera_name_var = StringVar()
        ttk.Entry(device_editor, textvariable=self.camera_name_var, width=18).pack(side="left", padx=(4, 10))
        ttk.Button(device_editor, text="Save device", command=self.save_selected_device).pack(side="left")

        self.log = Text(frame, height=18, wrap="word")
        self.log.pack(fill=BOTH, expand=True)

        self.write("1) Открой Three Cam на всех телефонах, которые хочешь подключить.")
        self.write("2) Нажми Авто поиск. Сколько телефонов найдено, столько и будет управляться.")
        self.write("Пробел тоже нажимает START/STOP.")
        self.root.bind("<space>", lambda _event: self.toggle_clicked())
        self.refresh_device_table()
        self.start_status_polling()

    def write(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = DISABLED if busy else NORMAL
        self.discover_button.configure(state=state)
        self.record_button.configure(state=state)
        self.status_button.configure(state=state)
        self.download_button.configure(state=state)
        self.history_button.configure(state=state)
        self.ws_record_button.configure(state=state)
        self.ws_status_button.configure(state=state)

    def refresh_device_table(self) -> None:
        selected = self.devices_tree.selection()
        selected_id = selected[0] if selected else None
        self.devices_tree.delete(*self.devices_tree.get_children())
        for index, phone in enumerate(configured_phones(self.config)):
            iid = str(index)
            device_key = phone.get("device_id") or phone.get("url")
            device_status = self.device_status_cache.get(device_key, {})
            values = (
                phone.get("device_slot", ""),
                phone.get("camera_name", ""),
                phone.get("device_name") or phone.get("device_label") or phone.get("name", ""),
                phone.get("url", ""),
                device_status.get("free", "—"),
                device_status.get("battery", "—"),
            )
            tags = () if device_status.get("ok", True) else ("offline",)
            self.devices_tree.insert("", "end", iid=iid, values=values, tags=tags)
        if selected_id and self.devices_tree.exists(selected_id):
            self.devices_tree.selection_set(selected_id)

    def start_status_polling(self, interval_ms: int = 15000) -> None:
        def worker() -> None:
            phones = configured_phones(self.config)
            timeout = float(self.config.get("timeout_seconds", 3))
            cache: dict[str, dict] = {}
            if phones:
                with ThreadPoolExecutor(max_workers=len(phones)) as executor:
                    futures = {
                        executor.submit(get_json, phone, "/status", timeout): phone
                        for phone in phones
                    }
                    for future, phone in futures.items():
                        device_key = phone.get("device_id") or phone.get("url")
                        try:
                            status = future.result()
                            battery_percent = status.get("batteryPercent")
                            cache[device_key] = {
                                "free": format_bytes(status.get("freeStorageBytes")),
                                "battery": (
                                    f"{battery_percent}%"
                                    if isinstance(battery_percent, int)
                                    else "—"
                                ),
                                "ok": True,
                            }
                        except Exception:
                            cache[device_key] = {"free": "—", "battery": "—", "ok": False}

            def apply() -> None:
                self.device_status_cache = cache
                self.refresh_device_table()
                self._poll_job = self.root.after(interval_ms, self.start_status_polling)

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def selected_phone_index(self) -> int | None:
        selected = self.devices_tree.selection()
        if not selected:
            return None
        try:
            return int(selected[0])
        except ValueError:
            return None

    def device_selected(self, _event=None) -> None:
        index = self.selected_phone_index()
        phones = configured_phones(self.config)
        if index is None or index >= len(phones):
            return
        phone = phones[index]
        self.device_slot_var.set(str(phone.get("device_slot") or ""))
        self.camera_name_var.set(str(phone.get("camera_name") or ""))

    def save_selected_device(self) -> None:
        index = self.selected_phone_index()
        phones = configured_phones(self.config)
        if index is None or index >= len(phones):
            self.write("Select a device first.")
            return

        slot = safe_int(self.device_slot_var.get())
        if slot is None or slot < 1:
            self.write("Slot must be a positive number.")
            return

        camera_name = safe_name(self.camera_name_var.get())
        if not camera_name:
            camera_name = camera_name_from_slot(slot)

        target_url = phones[index].get("url")
        target_device_id = phones[index].get("device_id")
        for phone in self.config.get("phones", []):
            if phone.get("device_id") == target_device_id or phone.get("url") == target_url:
                phone["device_slot"] = slot
                phone["camera_name"] = camera_name
                break
        save_config(self.config)
        self.refresh_device_table()
        self.write(f"Saved device: slot={slot}, camera_name={camera_name}")

    def start_timer(self) -> None:
        if self.record_start_time is not None:
            return
        self.record_start_time = time.time()
        self._tick_timer()

        auto_stop_minutes = safe_int(self.auto_stop_var.get())
        if auto_stop_minutes and auto_stop_minutes > 0:
            self._auto_stop_job = self.root.after(auto_stop_minutes * 60 * 1000, self.auto_stop_triggered)

    def stop_timer(self) -> None:
        if self.recording or self.ws_recording:
            return
        self.record_start_time = None
        if self._timer_job is not None:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None
        if self._auto_stop_job is not None:
            self.root.after_cancel(self._auto_stop_job)
            self._auto_stop_job = None
        self.timer_var.set("00:00:00")

    def _tick_timer(self) -> None:
        if self.record_start_time is None:
            return
        elapsed = int(time.time() - self.record_start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self._timer_job = self.root.after(1000, self._tick_timer)

    def record_session_history(self, mode: str) -> None:
        started_at = self._session_started_at.pop(mode, None)
        duration_seconds = int(time.time() - started_at) if started_at else None
        entry = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "mode": mode,
            "duration_seconds": duration_seconds,
            "phones": len(configured_phones(self.config)),
        }
        self.session_history.append(entry)
        save_session_history(self.session_history)

    def history_clicked(self) -> None:
        if not self.session_history:
            self.write("История сессий пуста.")
            return
        self.write("--- История записи (последние 20) ---")
        for entry in self.session_history[-20:]:
            duration = entry.get("duration_seconds")
            if isinstance(duration, int):
                duration_text = f"{duration // 60}м {duration % 60}с"
            else:
                duration_text = "?"
            self.write(
                f"{entry.get('started_at')} [{entry.get('mode')}] "
                f"длительность={duration_text}, камер={entry.get('phones')}"
            )

    def auto_stop_triggered(self) -> None:
        self._auto_stop_job = None
        self.write("Автостоп: время вышло, останавливаю запись.")
        if self.recording:
            self.toggle_clicked()
        if self.ws_recording:
            self.ws_toggle_clicked()

    def run_background(self, title: str, action) -> None:
        if self.busy:
            return
        self.set_busy(True)
        self.status.set(title)

        def worker() -> None:
            try:
                message = action()
                self.root.after(0, lambda: self.write(message))
                self.root.after(0, lambda: self.status.set("Готово"))
            except Exception as error:
                self.root.after(0, lambda: self.write(f"ERROR: {error}"))
                self.root.after(0, lambda: self.status.set("Ошибка"))
            finally:
                self.root.after(0, lambda: self.set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def discover_clicked(self) -> None:
        def action() -> str:
            phones = discover_phones(self.config)
            if phones:
                self.config["phones"] = phones
                save_config(self.config)
                self.root.after(0, self.refresh_device_table)
            return format_results(
                f"Найдено телефонов: {len(phones)}",
                [(phone_display_name(phone), phone["url"]) for phone in phones],
            )

        self.run_background("Ищу телефоны...", action)

    def toggle_clicked(self) -> None:
        endpoint = "/stop" if self.recording else "/start"
        title = "Останавливаю запись..." if self.recording else "Запускаю запись..."

        def action() -> str:
            results = send_all(self.config, endpoint)
            self.recording = not self.recording
            button_text = "STOP REC" if self.recording else "START REC"
            self.root.after(0, lambda: self.record_button.configure(text=button_text))
            self.root.after(0, self.start_timer if self.recording else self.stop_timer)
            if self.recording:
                self._session_started_at["http"] = time.time()
            else:
                self.root.after(0, lambda: self.record_session_history("http"))
            return format_results("Команда отправлена:", results)

        self.run_background(title, action)

    def status_clicked(self) -> None:
        def action() -> str:
            results = status_all(self.config)
            return format_results("Статус:", results)

        self.run_background("Проверяю телефоны...", action)

    def download_clicked(self) -> None:
        def action() -> str:
            results = download_all(self.config)
            return format_results("Скачивание:", results)

        self.run_background("Скачиваю видео...", action)

    def ws_toggle_clicked(self) -> None:
        """Synchronized start/stop via the new Scheduler (scheduler.md) - unlike the
        legacy START REC button, this waits for every connected node's ACK before the
        computed executeAt deadline, so all nodes actually start at the same instant
        instead of "as fast as parallel HTTP requests happen to land".
        """
        if self.gateway is None:
            self.write(f"WS is not available: {GATEWAY_IMPORT_ERROR or self.ws_status.get()}")
            return
        title = "Синхронный стоп (WS)..." if self.ws_recording else "Синхронный старт (WS)..."

        def action() -> str:
            if self.ws_recording:
                result = self.gateway.stop_recording(camera_name="one")
            else:
                result = self.gateway.start_recording(camera_name="one")
            self.ws_recording = not self.ws_recording
            button_text = "SYNC STOP" if self.ws_recording else "SYNC START"
            self.root.after(0, lambda: self.ws_record_button.configure(text=button_text))
            self.root.after(0, self.start_timer if self.ws_recording else self.stop_timer)
            if self.ws_recording:
                self._session_started_at["ws"] = time.time()
            else:
                self.root.after(0, lambda: self.record_session_history("ws"))
            return (
                f"WS sync: acked={result.acked}, missing_ack={result.missing_ack}, "
                f"excluded (no rtt/offset yet)={result.excluded_missing_data}"
            )

        self.run_background(title, action)

    def ws_status_clicked(self) -> None:
        if self.gateway is None:
            self.write(f"WS is not available: {GATEWAY_IMPORT_ERROR or self.ws_status.get()}")
            return

        def action() -> str:
            connected = self.gateway.connected_device_ids()
            discovered = self.gateway.list_discovered_devices()
            self.root.after(0, lambda: self.ws_status.set(f"WS: готов ({len(connected)} устройств)"))
            return (
                f"WS подключено ({len(connected)}): {connected}\n"
                f"UDP обнаружено ({len(discovered)}): "
                f"{[(node.device_id, node.ip, node.name) for node in discovered]}"
            )

        self.run_background("Проверяю WS...", action)

    def on_close(self) -> None:
        if self._timer_job is not None:
            self.root.after_cancel(self._timer_job)
        if self._auto_stop_job is not None:
            self.root.after_cancel(self._auto_stop_job)
        if self._poll_job is not None:
            self.root.after_cancel(self._poll_job)
        try:
            if self.gateway is not None:
                self.gateway.stop()
        except Exception:  # noqa: BLE001 - never block window close on shutdown errors
            pass
        self.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Control Three Cam mobile apps over hotspot/Wi-Fi.")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--toggle", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--clear-videos", action="store_true")
    args = parser.parse_args()

    config = load_config()
    try:
        if args.discover:
            phones = discover_phones(config)
            if phones:
                config["phones"] = phones
                save_config(config)
            print(format_results("Discover:", [(phone["name"], phone["url"]) for phone in phones]))
        elif args.start:
            print(format_results("Start:", send_all(config, "/start")))
        elif args.stop:
            print(format_results("Stop:", send_all(config, "/stop")))
        elif args.toggle:
            print(format_results("Toggle:", send_all(config, "/toggle")))
        elif args.status:
            print(format_results("Status:", status_all(config)))
        elif args.download:
            print(format_results("Download:", download_all(config)))
        elif args.clear_videos:
            print(format_results("Clear videos:", clear_videos_all(config)))
        else:
            root = Tk()
            ControllerApp(root, config)
            root.mainloop()
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
