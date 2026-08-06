import argparse
import io
import zlib
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
from tkinter import BOTH, DISABLED, NORMAL, BooleanVar, IntVar, StringVar, Tk, Text, filedialog, messagebox, ttk
from tkinter import font as tkfont

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
DATASET_STATE_NAME = "three_cam_dataset_state.json"
SESSION_HISTORY_NAME = "three_cam_session_history.json"
RECORDING_LOG_DIR_NAME = "recording_logs"
SESSION_HISTORY_LIMIT = 200
DISCOVERY_MESSAGE = "THREE_CAM_DISCOVER"
BACKGROUND_WORD = "background"
SIGNERS = [
    ("signer_1", "Шоира"),
    ("signer_2", "Адолат"),
    ("signer_3", "Фазилят"),
    ("signer_4", "Дилназ"),
    ("signer_5", "Шахзода_1"),
    ("signer_6", "Парогат"),
    ("signer_7", "Намуна"),
    ("signer_8", "Муслима"),
    ("signer_9", "Нафиса"),
    ("signer_10", "Лазокат"),
    ("signer_11", "Нигора_под_вопросом"),
    ("signer_12", "Шахзода_под_вопросом"),
    ("signer_13", "AAE"),
    ("signer_14", "XS"),
]
SIGNER_NAMES = dict(SIGNERS)
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
        "required_phone_count": 3,
        "block_recording_if_missing_phones": True,
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


def default_dataset_state() -> dict:
    return {
        "selected_signer_id": "signer_1",
        "words": [],
        "main_word_index": 0,
        "view_word_index": 0,
        "gesture_count": 1,
        "takes_done_by_word": {},
        "background_mode": False,
        "manual_back_mode": False,
    }


def load_dataset_state() -> dict:
    path = app_dir() / DATASET_STATE_NAME
    state = default_dataset_state()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                state.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass
    state["words"] = normalize_word_items(state.get("words", []))
    state["selected_signer_id"] = str(state.get("selected_signer_id") or "signer_1")
    state["gesture_count"] = max(1, int(safe_int(state.get("gesture_count"), 1) or 1))
    state["main_word_index"] = clamp_index(safe_int(state.get("main_word_index"), 0) or 0, len(state["words"]))
    state["view_word_index"] = clamp_index(safe_int(state.get("view_word_index"), state["main_word_index"]) or 0, len(state["words"]))
    state["background_mode"] = bool(state.get("background_mode", False))
    state["manual_back_mode"] = bool(state.get("manual_back_mode", False))
    if not isinstance(state.get("takes_done_by_word"), dict):
        state["takes_done_by_word"] = {}
    return state


def save_dataset_state(state: dict) -> None:
    path = app_dir() / DATASET_STATE_NAME
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


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


def recording_log_dir() -> Path:
    path = app_dir() / RECORDING_LOG_DIR_NAME
    path.mkdir(exist_ok=True)
    return path


def safe_int(value, fallback: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def clamp_index(index: int, count: int) -> int:
    if count <= 0:
        return 0
    return max(0, min(index, count - 1))


def signer_label(signer_id: str) -> str:
    name = SIGNER_NAMES.get(signer_id, signer_id)
    return f"{signer_id} - {name}"


def signer_dir_name(signer_id: str) -> str:
    name = SIGNER_NAMES.get(signer_id, signer_id)
    return safe_name(f"{signer_id}_{name}")


def word_key(word: dict) -> str:
    word_id = word.get("word_id")
    return str(word_id) if word_id not in (None, "") else safe_name(str(word.get("uzbek") or "word"))


def word_display(word: dict | None) -> str:
    if not word:
        return "No words imported"
    word_id = word.get("word_id")
    page = word.get("page")
    prefix = []
    if word_id not in (None, ""):
        prefix.append(f"№ {word_id}")
    if page not in (None, ""):
        prefix.append(f"page {page}")
    text = str(word.get("uzbek") or "").strip()
    return f"{' / '.join(prefix)}\n{text}" if prefix else text


def word_dir_name(word: dict | None) -> str:
    if not word:
        return "word"
    text = safe_name(str(word.get("uzbek") or "word"))
    word_id = safe_int(word.get("word_id"))
    if word_id is not None:
        return f"{word_id:03d}_{text}" if text else f"{word_id:03d}"
    return text or "word"


def take_label(take_number: int) -> str:
    take_number = max(1, take_number)
    label = ""
    value = take_number
    while value:
        value -= 1
        label = chr(ord("a") + (value % 26)) + label
        value //= 26
    return label


def normalize_word_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    # PDF coordinate extraction can split letters into separate cells. Join the
    # common Google Sheets fragments without changing meaningful spaces elsewhere.
    text = re.sub(r"\b([A-ZА-ЯOUEHMS])\s+([a-zа-я][a-zа-я'])", r"\1\2", text)
    text = re.sub(r"\b(En|Er|Esh|Eg|Sevm|Birovn|Magnitofon|Mebel)\s+", r"\1", text)
    return text


def normalize_word_items(items: list) -> list[dict]:
    normalized = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            text = normalize_word_text(item)
            if text:
                normalized.append({"word_id": index + 1, "page": None, "uzbek": text})
            continue
        if not isinstance(item, dict):
            continue
        text = normalize_word_text(str(item.get("uzbek") or item.get("word") or ""))
        if not text:
            continue
        normalized.append(
            {
                "word_id": safe_int(item.get("word_id"), index + 1),
                "page": safe_int(item.get("page")),
                "uzbek": text,
                "source_pdf": str(item.get("source_pdf") or ""),
                "source_set": str(item.get("source_set") or ""),
            }
        )
    return normalized


def source_set_from_pdf(path: Path) -> str:
    match = re.search(r"(set_\d+)", path.name, re.IGNORECASE)
    return match.group(1).lower() if match else path.stem


def extract_words_from_pdf(path: Path) -> list[dict]:
    try:
        return extract_words_with_pypdf(path)
    except Exception:
        return extract_words_from_google_sheets_pdf(path)


def extract_words_with_pypdf(path: Path) -> list[dict]:
    from pypdf import PdfReader  # type: ignore

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    items = []
    for line in text.splitlines():
        line = normalize_word_text(line)
        match = re.match(r"^(\d{1,4})\s+(\d{1,4})\s+(.+)$", line)
        if not match:
            continue
        word_text = normalize_word_text(match.group(3))
        if should_skip_pdf_word(word_text):
            continue
        items.append(
            {
                "word_id": int(match.group(1)),
                "page": int(match.group(2)),
                "uzbek": word_text,
                "source_pdf": path.name,
                "source_set": source_set_from_pdf(path),
            }
        )
    if not items:
        raise RuntimeError("pypdf did not extract table rows")
    return items


def should_skip_pdf_word(text: str) -> bool:
    lowered = text.lower()
    return (
        not text
        or text == "ФОН"
        or lowered.startswith("page ")
        or "signer_" in lowered
        or lowered in {"uzbek", "i = №", "ii = №"}
        or bool(re.match(r"^[0-9./-]{6,}$", text))
    )


def pdf_streams(path: Path) -> list[str]:
    data = path.read_bytes()
    streams = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        raw = match.group(1)
        for offset in (0, 2):
            try:
                streams.append(zlib.decompress(raw[offset:]).decode("latin-1", errors="replace"))
                break
            except zlib.error:
                continue
    return streams


def hex_to_text(hex_value: str) -> str:
    chars = []
    for index in range(0, len(hex_value), 4):
        chars.append(chr(int(hex_value[index : index + 4], 16)))
    return "".join(chars)


def parse_cmap(text: str) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for line in text.splitlines():
        char_match = re.match(r"\s*<([0-9A-Fa-f]{4})>\s+<([0-9A-Fa-f]+)>\s*$", line)
        if char_match:
            mapping[int(char_match.group(1), 16)] = hex_to_text(char_match.group(2))
            continue
        range_match = re.match(
            r"\s*<([0-9A-Fa-f]{4})>\s+<([0-9A-Fa-f]{4})>\s+<([0-9A-Fa-f]{4})>\s*$",
            line,
        )
        if range_match:
            start = int(range_match.group(1), 16)
            end = int(range_match.group(2), 16)
            base = int(range_match.group(3), 16)
            for value in range(start, end + 1):
                mapping[value] = chr(base + value - start)
    return mapping


def decode_pdf_hex(hex_value: str, mapping: dict[int, str]) -> str:
    decoded = []
    for index in range(0, len(hex_value), 4):
        decoded.append(mapping.get(int(hex_value[index : index + 4], 16), ""))
    return "".join(decoded)


def extract_words_from_google_sheets_pdf(path: Path) -> list[dict]:
    streams = pdf_streams(path)
    cmaps = [parse_cmap(stream) for stream in streams if "begincmap" in stream]
    if len(cmaps) < 3:
        raise RuntimeError("PDF text maps not found")
    font_maps = {"F4": cmaps[0], "F6": cmaps[1], "F7": cmaps[2]}
    glyphs = []
    for stream in streams:
        if " Tj" not in stream or "BT" not in stream:
            continue
        font = "F4"
        x = 0.0
        y = 0.0
        for line in stream.splitlines():
            font_match = re.search(r"/(F\d+)\s+[\d.]+\s+Tf", line)
            if font_match:
                font = font_match.group(1)
            tm_match = re.search(r"[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+([-\d.]+)\s+([-\d.]+)\s+Tm", line)
            if tm_match:
                x = float(tm_match.group(1))
                y = float(tm_match.group(2))
            td_match = re.search(r"([-\d.]+)\s+([-\d.]+)\s+Td\s+<([0-9A-Fa-f]+)>\s+Tj", line)
            if td_match:
                x += float(td_match.group(1))
                y += float(td_match.group(2))
                glyphs.append((x, y, decode_pdf_hex(td_match.group(3), font_maps.get(font, {}))))
                continue
            tj_match = re.search(r"<([0-9A-Fa-f]+)>\s+Tj", line)
            if tj_match:
                glyphs.append((x, y, decode_pdf_hex(tj_match.group(1), font_maps.get(font, {}))))

    rows: dict[int, list[tuple[float, str]]] = {}
    for x, y, text in glyphs:
        if not text:
            continue
        rows.setdefault(round(y / 2) * 2, []).append((x, text))

    items = []
    for _, cells in sorted(rows.items()):
        word_id_text = ""
        page_text = ""
        word_parts = []
        for x, text in sorted(cells):
            if x < 55:
                word_id_text += text
            elif x < 90:
                page_text += text
            elif x < 362:
                word_parts.append(text)
        word_id = safe_int(re.sub(r"\D+", "", word_id_text))
        page = safe_int(re.sub(r"\D+", "", page_text))
        word_text = normalize_word_text("".join(word_parts))
        if word_id is None or page is None or should_skip_pdf_word(word_text):
            continue
        items.append(
            {
                "word_id": word_id,
                "page": page,
                "uzbek": word_text,
                "source_pdf": path.name,
                "source_set": source_set_from_pdf(path),
            }
        )
    if not items:
        raise RuntimeError("No word rows found in PDF")
    return items


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


def download_file(phone: dict, relative_path: str, target: Path, timeout: float) -> None:
    query = urllib.parse.urlencode({"path": relative_path})
    url = normalize_url(phone["url"]) + "/download?" + query
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        target.write_bytes(response.read())


def send_all(config: dict, endpoint: str, task: dict | None = None) -> list[tuple[str, str]]:
    phones = get_phones(config, discover=not endpoint in {"/start", "/stop", "/toggle"})
    timeout = float(config.get("timeout_seconds", 1.5))
    if endpoint == "/start" and config.get("check_ready_before_start", False):
        check_ready_for_recording(config, phones, timeout)
    if endpoint == "/start" and config.get("block_recording_if_missing_phones", True):
        check_all_configured_phones_online(config, timeout)
    endpoint_by_phone = build_endpoint_map(config, phones, endpoint, task=task)
    results = []
    with ThreadPoolExecutor(max_workers=len(phones)) as executor:
        futures = {
            executor.submit(request_phone, phone, endpoint_by_phone[id(phone)], timeout): phone
            for phone in phones
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results


def build_endpoint_map(config: dict, phones: list[dict], endpoint: str, task: dict | None = None) -> dict[int, str]:
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
    if task is not None:
        task["session_id"] = session_id
        task["record_index"] = record_index
        task["date"] = date_stamp
        task["time"] = time_stamp

    endpoints = {}
    for phone in phones:
        camera_name = (
            safe_name(str(phone.get("device_label") or ""))
            or phone.get("camera_name")
            or camera_name_from_slot(safe_int(phone.get("device_slot")))
        )
        params = {
            "camera": camera_name,
            "date": date_stamp,
            "time": time_stamp,
            "index": str(record_index),
            "session": session_id,
        }
        if task:
            params.update(
                {
                    "signer_id": str(task.get("signer_id", "")),
                    "signer_name": str(task.get("signer_name", "")),
                    "signer_dir": str(task.get("signer_dir", "")),
                    "mode": str(task.get("mode", "word")),
                    "word": str(task.get("word", "")),
                    "word_id": str(task.get("word_id", "")),
                    "list": str(task.get("list", "")),
                    "word_dir": str(task.get("word_dir", "")),
                    "take_label": str(task.get("take_label", "")),
                    "take_number": str(task.get("take_number", "")),
                    "gesture_count": str(task.get("gesture_count", "")),
                    "retake": "1" if task.get("retake") else "0",
                }
            )
        query = urllib.parse.urlencode(params)
        endpoints[id(phone)] = f"/start?{query}"
    return endpoints


def check_all_configured_phones_online(config: dict, timeout: float) -> None:
    phones = configured_phones(config)
    required = int(config.get("required_phone_count", config.get("min_phones", len(phones) or 1)))
    if len(phones) < required:
        raise RuntimeError(f"WARNING: configured {len(phones)}/{required} phones. Recording blocked.")
    missing = []
    with ThreadPoolExecutor(max_workers=max(1, len(phones))) as executor:
        futures = {executor.submit(get_json, phone, "/status", timeout): phone for phone in phones}
        for future in as_completed(futures):
            phone = futures[future]
            try:
                payload = future.result()
                if not payload.get("ok", True):
                    missing.append(phone_display_name(phone))
            except Exception:
                missing.append(f"{phone_display_name(phone)} {phone.get('url', '')}")
    online = len(phones) - len(missing)
    if online < required:
        raise RuntimeError(
            f"WARNING: connected {online}/{required} phones. Recording blocked.\nMissing: "
            + ", ".join(missing)
        )


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
                relative_path = str(video.get("relativePath") or video.get("relative_path") or video.get("name") or "")
                if not relative_path:
                    continue
                safe_parts = [safe_name(part) for part in re.split(r"[\\/]+", relative_path) if part]
                if not safe_parts:
                    continue
                target = phone_dir.joinpath(*safe_parts)
                if not target.exists():
                    download_file(phone, relative_path, target, max(timeout, 30))
                    count += 1
            results.append((name, f"downloaded {count}, total {len(videos)}"))
        except Exception as error:
            results.append((name, f"ERROR: {error}"))
    return results


def list_videos_all(config: dict) -> list[dict]:
    phones = configured_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    videos: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, len(phones))) as executor:
        futures = {executor.submit(get_json, phone, "/videos", timeout): phone for phone in phones}
        for future in as_completed(futures):
            phone = futures[future]
            device = phone_display_name(phone)
            try:
                payload = future.result()
                for video in payload.get("videos", []):
                    if not isinstance(video, dict):
                        continue
                    item = dict(video)
                    item["phone_name"] = device
                    item["phone_url"] = phone.get("url", "")
                    item["device_id"] = phone.get("device_id", "")
                    videos.append(item)
            except Exception as error:
                videos.append(
                    {
                        "phone_name": device,
                        "phone_url": phone.get("url", ""),
                        "name": f"WARNING: {error}",
                        "status": "warning",
                    }
                )
    videos.sort(key=lambda item: str(item.get("modified", "")), reverse=True)
    return videos


def mark_video_error(config: dict, video: dict, *, superseded: bool = False) -> tuple[str, str]:
    phone_url = video.get("phone_url")
    if not phone_url:
        raise RuntimeError("Selected video has no phone URL")
    timeout = float(config.get("timeout_seconds", 3))
    phone = {"url": phone_url, "name": video.get("phone_name") or phone_url}
    relative_path = str(video.get("relativePath") or video.get("relative_path") or video.get("name") or "")
    endpoint = "/mark-video-error?" + urllib.parse.urlencode(
        {"path": relative_path, "superseded": "1" if superseded else "0"}
    )
    return request_phone(phone, endpoint, timeout, method="POST")


def mark_video_superseded(config: dict, video: dict) -> tuple[str, str]:
    phone_url = video.get("phone_url")
    if not phone_url:
        raise RuntimeError("Selected video has no phone URL")
    timeout = float(config.get("timeout_seconds", 3))
    phone = {"url": phone_url, "name": video.get("phone_name") or phone_url}
    relative_path = str(video.get("relativePath") or video.get("relative_path") or video.get("name") or "")
    endpoint = "/mark-video-superseded?" + urllib.parse.urlencode({"path": relative_path})
    return request_phone(phone, endpoint, timeout, method="POST")


def reset_index_all(config: dict) -> list[tuple[str, str]]:
    phones = get_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    config["next_index"] = 0
    save_config(config)
    results = []
    for phone in phones:
        name, body = request_phone(phone, "/reset-index", timeout, method="POST")
        results.append((name, body))
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
        self.dataset_state = load_dataset_state()
        self.signer_var = StringVar(value=signer_label(self.dataset_state.get("selected_signer_id", "signer_1")))
        self.word_var = StringVar(value="")
        self.progress_var = StringVar(value="")
        self.gesture_count_var = IntVar(value=max(1, safe_int(self.dataset_state.get("gesture_count"), 1) or 1))
        self.background_var = BooleanVar(value=bool(self.dataset_state.get("background_mode", False)))
        self.video_rows: dict[str, dict] = {}
        self.active_task: dict | None = None
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
        self.recording_log_entries: list[str] = []

        # New WS+Scheduler networking core (network_architecture.md), run alongside the
        # legacy HTTP path above - per the migration rules this is additive: the
        # existing "START REC"/"STOP REC" buttons keep using HTTP untouched, and the
        # "SYNC REC" buttons below are the only thing that goes through the Gateway.
        self.ws_recording = False
        self.gateway = None
        self.ws_status = StringVar(value="WS: запускается...")
        if Gateway is not None and GatewayConfig is not None:
            self.gateway = Gateway(GatewayConfig())
            self.gateway = None
            self.ws_status.set("WS: disabled during dataset workflow")
        else:
            self.ws_status.set(f"WS: disabled ({GATEWAY_IMPORT_ERROR})")
        if self.gateway is not None:
            try:
                self.gateway.start()
                self.ws_status.set("WS: готов (0 устройств)")
            except Exception as error:  # noqa: BLE001 - must not prevent the legacy dashboard from opening
                self.ws_status.set(f"WS: ошибка запуска ({error})")

        root.title("Three Cam Controller")
        root.geometry("1180x760")
        root.minsize(980, 650)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        style = ttk.Style(root)
        record_font = tkfont.Font(root=root, family="Segoe UI", size=16, weight="bold")
        style.configure("Record.TButton", font=record_font, padding=(24, 12))

        frame = ttk.Frame(root, padding=14)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Three Cam Controller", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(4, 12))

        dataset_frame = ttk.LabelFrame(frame, text="Dataset", padding=8)
        dataset_frame.pack(fill="x", pady=(0, 12))

        dataset_top = ttk.Frame(dataset_frame)
        dataset_top.pack(fill="x", pady=(0, 8))
        ttk.Label(dataset_top, text="Signer").pack(side="left")
        self.signer_combo = ttk.Combobox(
            dataset_top,
            textvariable=self.signer_var,
            values=[signer_label(item[0]) for item in SIGNERS],
            state="readonly",
            width=34,
        )
        self.signer_combo.pack(side="left", padx=(6, 10))
        self.signer_combo.bind("<<ComboboxSelected>>", self.signer_changed)
        ttk.Button(dataset_top, text="IMPORT PDF", command=self.import_pdf_clicked).pack(side="left", padx=(0, 8))
        ttk.Label(dataset_top, text="Gestures per word").pack(side="left")
        self.gesture_spin = ttk.Entry(dataset_top, textvariable=self.gesture_count_var, width=5)
        self.gesture_spin.pack(side="left", padx=(6, 10))
        self.gesture_spin.bind("<FocusOut>", lambda _event: self.gesture_count_changed())
        self.gesture_spin.bind("<Return>", lambda _event: self.gesture_count_changed())
        ttk.Checkbutton(dataset_top, text="BACKGROUND", variable=self.background_var, command=self.background_toggled).pack(side="left")

        word_row = ttk.Frame(dataset_frame)
        word_row.pack(fill="x")
        word_row.columnconfigure(0, weight=1, uniform="word_row_side")
        word_row.columnconfigure(1, weight=3)
        word_row.columnconfigure(2, weight=1, uniform="word_row_side")

        word_text = ttk.Frame(word_row)
        word_text.grid(row=0, column=1, sticky="ew")
        ttk.Label(
            word_text,
            textvariable=self.word_var,
            font=("Segoe UI", 24, "bold"),
            anchor="center",
            justify="center",
        ).pack(fill="x")
        ttk.Label(word_text, textvariable=self.progress_var, anchor="center").pack(fill="x", pady=(2, 0))

        record_action = ttk.Frame(word_row)
        record_action.grid(row=0, column=2, sticky="n", padx=(12, 170), pady=(16, 0))
        self.record_button = ttk.Button(
            record_action,
            text="START REC",
            command=self.toggle_clicked,
            style="Record.TButton",
            width=14,
        )
        self.record_button.pack()
        ttk.Label(record_action, textvariable=self.timer_var, font=("Segoe UI", 22, "bold")).pack(pady=(8, 0))

        nav_row = ttk.Frame(dataset_frame)
        nav_row.pack(fill="x", pady=(8, 0))
        ttk.Button(nav_row, text="BACK WORD", command=self.back_word_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(nav_row, text="RESET VIEW", command=self.reset_view_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(nav_row, text="RESET WORDS", command=self.reset_words_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(nav_row, text="RESET INDEX", command=self.reset_index_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(nav_row, text="DELETE VIDEOS", command=self.delete_videos_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(nav_row, text="REFRESH VIDEOS", command=self.refresh_videos_clicked).pack(side="left")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(0, 12))

        self.discover_button = ttk.Button(buttons, text="Авто поиск", command=self.discover_clicked)
        self.discover_button.pack(side="left", padx=(0, 8))

        self.status_button = ttk.Button(buttons, text="Проверить", command=self.status_clicked)
        self.status_button.pack(side="left", padx=(0, 8))

        self.download_button = ttk.Button(buttons, text="Скачать видео", command=self.download_clicked)
        self.download_button.pack(side="left", padx=(0, 8))
        self.save_recording_log_button = ttk.Button(buttons, text="Save logs", command=self.save_recording_log_clicked)
        self.save_recording_log_button.pack(side="left", padx=(0, 8))

        self.history_button = ttk.Button(buttons, text="История", command=self.history_clicked)
        self.history_button.pack(side="left")

        timer_frame = ttk.Frame(frame)
        timer_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(timer_frame, text="Auto stop minutes:").pack(side="left")
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
            height=4,
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

        videos = ttk.LabelFrame(frame, text="Saved videos", padding=8)
        videos.pack(fill="x", pady=(0, 12))
        video_top_actions = ttk.Frame(videos)
        video_top_actions.pack(fill="x", pady=(0, 8))
        ttk.Label(video_top_actions, text="Select a video row, then choose:").pack(side="left", padx=(0, 10))
        ttk.Button(video_top_actions, text="BAD VIDEO", command=self.mark_selected_video_error_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(video_top_actions, text="BAD + RETAKE", command=self.mark_error_and_retake_selected_video_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(video_top_actions, text="RETAKE", command=self.retake_selected_video_clicked).pack(side="left", padx=(0, 8))
        self.videos_tree = ttk.Treeview(
            videos,
            columns=("status", "signer", "word", "take", "device", "name", "size"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        for col, title, width in (
            ("status", "Status", 70),
            ("signer", "Signer", 120),
            ("word", "Word", 180),
            ("take", "Take", 60),
            ("device", "Device", 110),
            ("name", "File", 360),
            ("size", "Size", 80),
        ):
            self.videos_tree.heading(col, text=title)
            self.videos_tree.column(col, width=width, stretch=col == "name")
        self.videos_tree.tag_configure("error", foreground="#c0392b")
        self.videos_tree.tag_configure("superseded", foreground="#7f8c8d")
        self.videos_tree.tag_configure("warning", foreground="#b9770e")
        self.videos_tree.pack(fill="x")
        self.videos_tree.bind("<Double-1>", self.video_double_clicked)
        logs_frame = ttk.Frame(frame)
        logs_frame.pack(fill="x", expand=False)
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.columnconfigure(1, weight=1)
        logs_frame.rowconfigure(0, weight=1)

        command_log_frame = ttk.LabelFrame(logs_frame, text="Command log", padding=6)
        command_log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.log = Text(command_log_frame, height=3, wrap="word")
        self.log.pack(fill=BOTH, expand=True)

        recording_log_frame = ttk.LabelFrame(logs_frame, text="Recording log", padding=6)
        recording_log_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.recording_log = Text(recording_log_frame, height=3, wrap="word")
        self.recording_log.pack(fill=BOTH, expand=True)

        self.write("1) Открой Three Cam на всех телефонах, которые хочешь подключить.")
        self.write("2) Нажми Авто поиск. Сколько телефонов найдено, столько и будет управляться.")
        self.write("Пробел тоже нажимает START/STOP.")
        self.root.bind("<space>", lambda _event: self.toggle_clicked())
        self.refresh_dataset_labels()
        self.refresh_device_table()
        self.start_status_polling()

    def write(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def recording_log_write(self, message: str) -> None:
        line = f"{datetime.now().isoformat(timespec='seconds')} | {message}"
        self.recording_log_entries.append(line)
        if hasattr(self, "recording_log"):
            self.recording_log.insert("end", line + "\n")
            self.recording_log.see("end")

    def save_recording_log_file(self, path: Path | None = None) -> Path:
        if path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = recording_log_dir() / f"recording_log_{stamp}.txt"
        content = "\n".join(self.recording_log_entries)
        if content:
            content += "\n"
        path.write_text(content, encoding="utf-8")
        return path

    def save_recording_log_clicked(self) -> None:
        initial = recording_log_dir() / f"recording_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(
            title="Save recording log",
            initialdir=str(initial.parent),
            initialfile=initial.name,
            defaultextension=".txt",
            filetypes=(("Text log", "*.txt"), ("All files", "*.*")),
        )
        if not path:
            return
        saved = self.save_recording_log_file(Path(path))
        self.write(f"Recording log saved: {saved}")

    def task_log_text(self, task: dict | None) -> str:
        if not task:
            return "task=unknown"
        return (
            f"session={task.get('session_id', '?')} index={task.get('record_index', '?')} "
            f"signer={task.get('signer_id', '?')} word_id={task.get('word_id', '?')} "
            f"word={task.get('word', '')} take={task.get('take_label', '?')}"
        )

    def log_phone_results(self, event: str, results: list[tuple[str, str]]) -> None:
        for name, body in results:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.root.after(0, lambda n=name, b=body: self.recording_log_write(f"{event} {n}: {b}"))
                continue
            if not payload.get("ok", True):
                self.root.after(
                    0,
                    lambda n=name, p=payload: self.recording_log_write(f"{event} {n}: ERROR {p.get('error', p)}"),
                )
                continue
            details = [f"{event} {name}: ok"]
            if payload.get("sessionId"):
                details.append(f"session={payload.get('sessionId')}")
            if payload.get("lastVideoName"):
                details.append(f"video={payload.get('lastVideoName')}")
            if payload.get("lastVideoSizeBytes") is not None:
                details.append(f"size={format_bytes(payload.get('lastVideoSizeBytes'))}")
            self.root.after(0, lambda text=" ".join(details): self.recording_log_write(text))

    def save_dataset(self) -> None:
        self.dataset_state["selected_signer_id"] = self.selected_signer_id()
        self.dataset_state["gesture_count"] = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        self.dataset_state["background_mode"] = bool(self.background_var.get())
        save_dataset_state(self.dataset_state)

    def selected_signer_id(self) -> str:
        selected = self.signer_var.get()
        if " - " in selected:
            return selected.split(" - ", 1)[0]
        return str(self.dataset_state.get("selected_signer_id") or "signer_1")

    def current_word(self) -> dict | None:
        words = self.dataset_state.get("words", [])
        if not words or self.background_var.get():
            return None
        index = clamp_index(int(self.dataset_state.get("view_word_index", 0)), len(words))
        return words[index]

    def refresh_dataset_labels(self) -> None:
        words = self.dataset_state.get("words", [])
        if self.background_var.get():
            self.word_var.set("BACKGROUND")
            self.progress_var.set(f"Signer: {self.signer_var.get()} / background mode")
            return
        word = self.current_word()
        if not word:
            self.word_var.set("IMPORT PDF")
            self.progress_var.set("No words imported")
            return
        main_index = int(self.dataset_state.get("main_word_index", 0))
        view_index = int(self.dataset_state.get("view_word_index", main_index))
        gesture_count = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(word_key(word), 0))
        mode = "manual back" if self.dataset_state.get("manual_back_mode") else "main queue"
        self.word_var.set(word_display(word))
        self.progress_var.set(
            f"{view_index + 1}/{len(words)} / take {min(done + 1, gesture_count)} of {gesture_count} / {mode}"
        )

    def signer_changed(self, _event=None) -> None:
        self.dataset_state["selected_signer_id"] = self.selected_signer_id()
        self.save_dataset()
        self.refresh_dataset_labels()
        self.write(f"Signer selected: {self.signer_var.get()}")

    def gesture_count_changed(self) -> None:
        self.dataset_state["gesture_count"] = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        self.save_dataset()
        self.refresh_dataset_labels()

    def background_toggled(self) -> None:
        self.dataset_state["background_mode"] = bool(self.background_var.get())
        self.save_dataset()
        self.refresh_dataset_labels()

    def import_pdf_clicked(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Import word PDFs",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
        )
        if not paths:
            return

        def action() -> str:
            words: list[dict] = []
            warnings = []
            for raw_path in paths:
                path = Path(raw_path)
                extracted = extract_words_from_pdf(path)
                words.extend(extracted)
                if any(item.get("uzbek") == "ФОН" for item in extracted):
                    warnings.append(f"{path.name}: contains ФОН")
            words = normalize_word_items(words)
            words.sort(key=lambda item: (safe_int(item.get("word_id"), 10**9) or 10**9, item.get("source_pdf", "")))
            if not words:
                raise RuntimeError("No words found in selected PDF files")
            self.dataset_state["words"] = words
            self.dataset_state["main_word_index"] = 0
            self.dataset_state["view_word_index"] = 0
            self.dataset_state["takes_done_by_word"] = {}
            self.dataset_state["manual_back_mode"] = False
            self.save_dataset()
            self.root.after(0, self.refresh_dataset_labels)
            return f"Imported {len(words)} words from {len(paths)} PDF(s)." + (
                "\n" + "\n".join(warnings) if warnings else ""
            )

        self.run_background("Importing PDF...", action)

    def build_current_task(self) -> dict:
        signer_id = self.selected_signer_id()
        signer_name = SIGNER_NAMES.get(signer_id, signer_id)
        gesture_count = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        if self.background_var.get():
            return {
                "signer_id": signer_id,
                "signer_name": signer_name,
                "signer_dir": signer_dir_name(signer_id),
                "mode": "background",
            "word": BACKGROUND_WORD,
            "word_id": "",
            "list": "",
            "word_dir": BACKGROUND_WORD,
                "take_number": 1,
                "take_label": take_label(1),
                "gesture_count": gesture_count,
                "retake": False,
            }
        word = self.current_word()
        if not word:
            raise RuntimeError("Import PDF before recording")
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(word_key(word), 0))
        take_number = done + 1
        return {
            "signer_id": signer_id,
            "signer_name": signer_name,
            "signer_dir": signer_dir_name(signer_id),
            "mode": "word",
            "word": word.get("uzbek", ""),
            "word_id": word.get("word_id", ""),
            "list": word.get("source_set", ""),
            "word_dir": word_dir_name(word),
            "take_number": take_number,
            "take_label": take_label(take_number),
            "gesture_count": gesture_count,
            "retake": bool(self.dataset_state.get("retake_mode", False)),
        }

    def complete_current_task(self) -> None:
        if self.background_var.get():
            return
        word = self.current_word()
        if not word:
            return
        gesture_count = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        key = word_key(word)
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(key, 0)) + 1
        self.dataset_state.setdefault("takes_done_by_word", {})[key] = done
        if not self.dataset_state.get("manual_back_mode") and done >= gesture_count:
            words = self.dataset_state.get("words", [])
            next_index = min(int(self.dataset_state.get("main_word_index", 0)) + 1, max(0, len(words) - 1))
            self.dataset_state["main_word_index"] = next_index
            self.dataset_state["view_word_index"] = next_index
        self.dataset_state["retake_mode"] = False
        self.save_dataset()
        self.refresh_dataset_labels()

    def back_word_clicked(self) -> None:
        words = self.dataset_state.get("words", [])
        if not words:
            return
        self.dataset_state["view_word_index"] = max(0, int(self.dataset_state.get("view_word_index", 0)) - 1)
        self.dataset_state["manual_back_mode"] = True
        self.save_dataset()
        self.refresh_dataset_labels()

    def reset_view_clicked(self) -> None:
        self.dataset_state["manual_back_mode"] = False
        self.dataset_state["retake_mode"] = False
        self.dataset_state["view_word_index"] = int(self.dataset_state.get("main_word_index", 0))
        self.save_dataset()
        self.refresh_dataset_labels()

    def reset_words_clicked(self) -> None:
        if not messagebox.askyesno("Reset words", "Start words again from the first word?"):
            return
        self.dataset_state["main_word_index"] = 0
        self.dataset_state["view_word_index"] = 0
        self.dataset_state["takes_done_by_word"] = {}
        self.dataset_state["manual_back_mode"] = False
        self.dataset_state["retake_mode"] = False
        self.save_dataset()
        self.refresh_dataset_labels()
        self.write("Words reset: started again from the first word.")

    def refresh_videos_table(self, videos: list[dict] | None = None) -> None:
        if not hasattr(self, "videos_tree"):
            return
        self.videos_tree.delete(*self.videos_tree.get_children())
        self.video_rows = {}
        if videos is None:
            videos = []
        for index, video in enumerate(videos):
            iid = str(index)
            status = str(video.get("status") or ("error" if video.get("isError") else "ok"))
            tags = (
                ("error",)
                if status == "error"
                else (("superseded",) if status == "superseded" else (("warning",) if status == "warning" else ()))
            )
            values = (
                status.upper(),
                video.get("signerName") or video.get("signer_name") or "",
                video.get("word") or video.get("mode") or "",
                video.get("takeLabel") or video.get("take_label") or "",
                video.get("deviceLabel") or video.get("phone_name") or "",
                video.get("name") or "",
                format_bytes(video.get("size") if isinstance(video.get("size"), int) else None),
            )
            self.video_rows[iid] = video
            self.videos_tree.insert("", "end", iid=iid, values=values, tags=tags)

    def refresh_videos_clicked(self) -> None:
        def action() -> str:
            videos = list_videos_all(self.config)
            self.root.after(0, lambda: self.refresh_videos_table(videos))
            return f"Videos refreshed: {len(videos)}"

        self.run_background("Refreshing videos...", action)

    def selected_video(self) -> dict | None:
        selected = self.videos_tree.selection() if hasattr(self, "videos_tree") else ()
        if not selected:
            return None
        return self.video_rows.get(selected[0])

    def video_double_clicked(self, _event=None) -> None:
        video = self.selected_video()
        if not video:
            return
        messagebox.showinfo(
            "Video",
            f"{video.get('name')}\n\nStatus: {video.get('status', 'ok')}\nWord: {video.get('word', '')}",
        )

    def mark_selected_video_error_clicked(self) -> None:
        video = self.selected_video()
        if not video:
            self.write("Select a video first.")
            return
        if not messagebox.askyesno("Mark error", f"Mark this video as error?\n{video.get('name')}"):
            return

        def action() -> str:
            name, body = mark_video_error(self.config, video)
            videos = list_videos_all(self.config)
            self.root.after(0, lambda: self.refresh_videos_table(videos))
            self.root.after(0, lambda: self.recording_log_write(f"MARK_ERROR device={name} video={video.get('name')}"))
            return f"{name}: {body}"

        self.run_background("Marking video error...", action)

    def mark_error_and_retake_selected_video_clicked(self) -> None:
        video = self.selected_video()
        if not video:
            self.write("Select a video first.")
            return
        if not messagebox.askyesno(
            "Ошибка + переснять",
            f"Пометить это видео как ERROR и перейти на пересъём?\n{video.get('name')}",
        ):
            return
        if not self.prepare_retake_from_video(video, write_message=False):
            return

        def action() -> str:
            name, body = mark_video_error(self.config, video, superseded=True)
            videos = list_videos_all(self.config)
            self.root.after(0, lambda: self.refresh_videos_table(videos))
            self.root.after(
                0,
                lambda: self.recording_log_write(f"MARK_ERROR_RETAKE device={name} video={video.get('name')}"),
            )
            return f"{name}: marked ERROR. Ready to retake."

        self.run_background("Marking error and preparing retake...", action)

    def retake_selected_video_clicked(self) -> None:
        video = self.selected_video()
        if not video:
            self.write("Select a video first.")
            return
        if not self.prepare_retake_from_video(video):
            return

        def action() -> str:
            name, _body = mark_video_superseded(self.config, video)
            videos = list_videos_all(self.config)
            self.root.after(0, lambda: self.refresh_videos_table(videos))
            self.root.after(0, lambda: self.recording_log_write(f"MARK_SUPERSEDED device={name} video={video.get('name')}"))
            return f"{name}: previous take marked SUPERSEDED. Ready to retake."

        self.run_background("Preparing retake...", action)

    def prepare_retake_from_video(self, video: dict, write_message: bool = True) -> bool:
        word_value = str(video.get("word") or "")
        if not word_value:
            self.write("Selected video has no word metadata.")
            return False
        if word_value.lower() == BACKGROUND_WORD or str(video.get("mode") or "").lower() == "background":
            self.background_var.set(True)
            self.dataset_state["background_mode"] = True
            self.dataset_state["manual_back_mode"] = False
            self.dataset_state["retake_mode"] = True
            self.save_dataset()
            self.refresh_dataset_labels()
            if write_message:
                self.write("Retake selected: background")
            return True
        words = self.dataset_state.get("words", [])
        for index, word in enumerate(words):
            if str(word.get("uzbek")) == word_value or str(word.get("word_id")) == str(video.get("wordId") or video.get("word_id")):
                self.dataset_state["view_word_index"] = index
                self.dataset_state["manual_back_mode"] = True
                self.dataset_state["retake_mode"] = True
                self.save_dataset()
                self.refresh_dataset_labels()
                if write_message:
                    self.write(f"Retake selected: {word_value}")
                return True
        self.write(f"Retake word not found in imported list: {word_value}")
        return False

    def reset_index_clicked(self) -> None:
        if not messagebox.askyesno("Reset index", "Reset future video indexes on controller and phones?"):
            return

        def action() -> str:
            return format_results("Reset index:", reset_index_all(self.config))

        self.run_background("Resetting indexes...", action)

    def delete_videos_clicked(self) -> None:
        if not messagebox.askyesno("Delete videos", "Delete all videos from all phones?"):
            return
        def action() -> str:
            result = format_results("Delete videos:", clear_videos_all(self.config))
            self.root.after(0, self.refresh_videos_table)
            return result

        self.run_background("Deleting videos...", action)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = DISABLED if busy else NORMAL
        self.discover_button.configure(state=state)
        self.record_button.configure(state=state)
        self.status_button.configure(state=state)
        self.download_button.configure(state=state)
        self.save_recording_log_button.configure(state=state)
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
            task = None
            if not self.recording:
                task = self.build_current_task()
                self.active_task = task
            results = send_all(self.config, endpoint, task=task)
            self.recording = not self.recording
            button_text = "STOP REC" if self.recording else "START REC"
            self.root.after(0, lambda: self.record_button.configure(text=button_text))
            self.root.after(0, self.start_timer if self.recording else self.stop_timer)
            if self.recording:
                self._session_started_at["http"] = time.time()
                self.root.after(0, lambda t=task: self.recording_log_write(f"START {self.task_log_text(t)}"))
                self.log_phone_results("START_ACK", results)
                if self.active_task:
                    task_text = (
                        f"{self.active_task.get('mode')} / {self.active_task.get('word')} "
                        f"/ take {self.active_task.get('take_label')}"
                    )
                    self.root.after(0, lambda: self.write(f"START task: {task_text}"))
            else:
                self.root.after(0, self.complete_current_task)
                videos = list_videos_all(self.config)
                self.root.after(0, lambda: self.refresh_videos_table(videos))
                self.root.after(0, lambda: self.record_session_history("http"))
                self.root.after(0, lambda t=self.active_task: self.recording_log_write(f"STOP {self.task_log_text(t)}"))
                self.log_phone_results("STOP_SAVE", results)
                saved_log = self.save_recording_log_file()
                self.root.after(0, lambda p=saved_log: self.recording_log_write(f"LOG_SAVED path={p}"))
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
