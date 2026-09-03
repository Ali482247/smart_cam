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
from collections import deque
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
APP_VERSION = "1.1.0"
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
        "record_command_timeout_seconds": 8.0,
        "video_list_timeout_seconds": 30.0,
        "stop_grace_seconds": 0.75,
        "stop_retry_count": 2,
        "stop_retry_delay_seconds": 0.15,
        "post_stop_confirm_timeout_seconds": 12.0,
        "post_stop_confirm_interval_seconds": 0.75,
        "post_stop_video_refresh_delay_seconds": 1.5,
        "auto_refresh_videos_after_stop": False,
        "next_index": 0,
        "next_device_slot": 1,
        "required_phone_count": 3,
        "block_recording_if_missing_phones": True,
        "min_free_storage_bytes": 1073741824,
        "min_battery_percent": 15,
        "recording_watchdog_enabled": True,
        "abort_recording_on_phone_loss": False,
        "recording_watchdog_interval_seconds": 0.5,
        "recording_watchdog_timeout_seconds": 1.5,
        "recording_watchdog_start_grace_seconds": 5.0,
        "recording_watchdog_consecutive_failures": 3,
        "recording_watchdog_warning_cooldown_seconds": 10.0,
        "recording_watchdog_can_stop_recording": False,
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
        "custom_signers": [],
        "deleted_signers": [],
        "last_deleted_signer": None,
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
    state["custom_signers"] = normalize_custom_signers(state.get("custom_signers", []))
    state["deleted_signers"] = normalize_deleted_signers(state.get("deleted_signers", []))
    if not isinstance(state.get("last_deleted_signer"), dict):
        state["last_deleted_signer"] = None
    available_items = signer_items(state)
    available_ids = {signer_id for signer_id, _name in available_items}
    if state["selected_signer_id"] not in available_ids:
        state["selected_signer_id"] = available_items[0][0] if available_items else "signer_1"
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


def signer_items(state: dict | None = None) -> list[tuple[str, str]]:
    deleted = set(normalize_deleted_signers(state.get("deleted_signers", []))) if state is not None else set()
    items = [item for item in SIGNERS if item[0] not in deleted]
    if state is not None:
        items.extend(item for item in normalize_custom_signers(state.get("custom_signers", [])) if item[0] not in deleted)
    return items


def signer_names(state: dict | None = None) -> dict[str, str]:
    return dict(signer_items(state))


def signer_label_for(signer_id: str, state: dict | None = None) -> str:
    name = signer_names(state).get(signer_id, signer_id)
    return f"{signer_id} - {name}"


def normalize_custom_signers(value) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: dict[str, str] = {}
    for item in value:
        if isinstance(item, dict):
            signer_id = str(item.get("id") or item.get("signer_id") or "").strip()
            name = str(item.get("name") or item.get("signer_name") or "").strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            signer_id = str(item[0]).strip()
            name = str(item[1]).strip()
        else:
            continue
        match = re.fullmatch(r"(?:signer_)?(\d{1,4})", signer_id)
        if not match or not name:
            continue
        normalized[f"signer_{int(match.group(1))}"] = name
    return sorted(normalized.items(), key=lambda item: safe_int(item[0].split("_", 1)[1], 0) or 0)


def normalize_deleted_signers(value) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: set[str] = set()
    for item in value:
        signer_id = str(item).strip()
        match = re.fullmatch(r"(?:signer_)?(\d{1,4})", signer_id)
        if match:
            normalized.add(f"signer_{int(match.group(1))}")
    return sorted(normalized, key=lambda item: safe_int(item.split("_", 1)[1], 0) or 0)


def parse_signer_entry(value: str) -> tuple[str, str]:
    text = value.strip()
    match = re.match(r"^(?:signer[_\s-]*)?(\d{1,4})(?:\s+|[-:]+)(.+)$", text, flags=re.IGNORECASE)
    if not match:
        raise ValueError("Enter signer as: 15 Name")
    number = int(match.group(1))
    if number <= 0:
        raise ValueError("Signer number must be greater than 0")
    name = re.sub(r"\s+", " ", match.group(2).strip())
    if not name:
        raise ValueError("Signer name is required")
    return f"signer_{number}", name


def signer_dir_name(signer_id: str) -> str:
    name = SIGNER_NAMES.get(signer_id, signer_id)
    return safe_name(f"{signer_id}_{name}")


def signer_dir_name_for(signer_id: str, state: dict | None = None) -> str:
    name = signer_names(state).get(signer_id, signer_id)
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
        return f"{word_id:04d}_{text}" if text else f"{word_id:04d}"
    return text or "word"


def word_number_prefix(word_id: int | str | None) -> str:
    value = safe_int(word_id)
    return f"{value:04d}" if value is not None else ""


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
        gesture_count = safe_int(item.get("gesture_count") or item.get("counts") or item.get("count"), 1) or 1
        normalized.append(
            {
                "word_id": safe_int(item.get("word_id"), index + 1),
                "page": safe_int(item.get("page")),
                "count": max(1, gesture_count),
                "uzbek": text,
                "source_pdf": str(item.get("source_pdf") or ""),
                "source_set": str(item.get("source_set") or ""),
            }
        )
    return normalized


def word_gesture_count(word: dict | None, default: int = 1) -> int:
    if not word:
        return max(1, safe_int(default, 1) or 1)
    return max(1, safe_int(word.get("count") or word.get("gesture_count") or word.get("counts"), default) or default)


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

    page_texts = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    text = "\n".join(page_texts)
    separate_count_items = extract_words_from_separate_count_column(page_texts, path)
    if separate_count_items:
        return separate_count_items
    items = []
    for line in text.splitlines():
        line = normalize_word_text(line)
        match = re.match(r"^(\d{1,4})\s+(\d{1,4})(?:\s+(\d{1,3}))?\s+(.+?)(?:\s+(\d{1,3}))?$", line)
        if not match:
            continue
        word_text = normalize_word_text(match.group(4))
        if should_skip_pdf_word(word_text):
            continue
        items.append(
            {
                "word_id": int(match.group(1)),
                "page": int(match.group(2)),
                "count": max(1, safe_int(match.group(3) or match.group(5), 1) or 1),
                "uzbek": word_text,
                "source_pdf": path.name,
                "source_set": source_set_from_pdf(path),
            }
        )
    if not items:
        items = extract_words_from_pypdf_lines(text, path)
    if not items:
        raise RuntimeError("pypdf did not extract table rows")
    return items


def extract_words_from_separate_count_column(page_texts: list[str], path: Path) -> list[dict]:
    all_rows: list[dict] = []
    global_seen_ids: set[int] = set()
    for text in page_texts:
        lines = [normalize_word_text(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        rows: list[dict] = []
        page_seen_ids: set[int] = set()
        index = 0
        while index < len(lines):
            line = lines[index]
            match = re.match(r"^(\d{1,4})\s+(\d{1,4})(?:\s+(.+))?$", line)
            if not match:
                index += 1
                continue
            word_id = int(match.group(1))
            if word_id in page_seen_ids:
                index += 1
                continue
            word_parts = [match.group(3) or ""]
            cursor = index + 1
            while cursor < len(lines):
                continuation = lines[cursor]
                if re.match(r"^\d{1,4}\s+\d{1,4}(?:\s+.+)?$", continuation):
                    break
                if continuation.lower() == "count" or re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", continuation):
                    break
                continuation_number = safe_int(continuation)
                if continuation_number is not None and 1 <= continuation_number <= 50:
                    break
                if not should_skip_pdf_word(continuation):
                    word_parts.append(continuation)
                cursor += 1
            word_text = normalize_word_text(" ".join(part for part in word_parts if part))
            if should_skip_pdf_word(word_text):
                index += 1
                continue
            page_seen_ids.add(word_id)
            rows.append(
                {
                    "word_id": word_id,
                    "page": int(match.group(2)),
                    "count": 1,
                    "uzbek": word_text,
                    "source_pdf": path.name,
                    "source_set": source_set_from_pdf(path),
                }
            )
            index = cursor
        if not rows:
            continue

        counts: list[int] = []
        for index, line in enumerate(lines):
            if line.lower() != "count":
                continue
            for count_line in lines[index + 1 :]:
                value = safe_int(count_line)
                if value is None or not 1 <= value <= 50:
                    break
                counts.append(value)
            break
        if len(counts) < len(rows):
            suffix_counts = []
            for line in reversed(lines):
                value = safe_int(line)
                if value is None or not 1 <= value <= 50:
                    break
                suffix_counts.append(value)
            counts = list(reversed(suffix_counts))
        if len(counts) < len(rows):
            continue
        for row, count in zip(rows, counts[-len(rows) :]):
            if int(row["word_id"]) in global_seen_ids:
                continue
            row["count"] = max(1, count)
            global_seen_ids.add(int(row["word_id"]))
            all_rows.append(row)
    if all_rows:
        return all_rows

    text = "\n".join(page_texts)
    lines = [normalize_word_text(line) for line in text.splitlines()]
    rows: list[dict] = []
    seen_ids: set[int] = set()
    counts: list[int] = []
    in_count_column = False
    for line in lines:
        if not line:
            in_count_column = False
            continue
        lowered = line.lower()
        if lowered == "count":
            in_count_column = True
            continue
        if in_count_column:
            value = safe_int(line)
            if value is not None and 1 <= value <= 50:
                counts.append(value)
                continue
            in_count_column = False

        match = re.match(r"^(\d{1,4})\s+(\d{1,4})\s+(.+)$", line)
        if not match:
            continue
        word_id = int(match.group(1))
        if word_id in seen_ids:
            continue
        word_text = normalize_word_text(match.group(3))
        if should_skip_pdf_word(word_text):
            continue
        seen_ids.add(word_id)
        rows.append(
            {
                "word_id": word_id,
                "page": int(match.group(2)),
                "count": 1,
                "uzbek": word_text,
                "source_pdf": path.name,
                "source_set": source_set_from_pdf(path),
            }
        )
    if not rows or len(counts) < len(rows):
        return []
    for row, count in zip(rows, counts):
        row["count"] = max(1, count)
    return rows


def extract_words_from_pypdf_lines(text: str, path: Path) -> list[dict]:
    lines = [normalize_word_text(line) for line in text.splitlines()]
    lines = [
        line
        for line in lines
        if line and not should_skip_pdf_word(line) and not re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", line)
    ]
    items = []
    index = 0
    while index + 2 < len(lines):
        word_id = safe_int(lines[index])
        page = safe_int(lines[index + 1])
        if word_id is None or page is None:
            index += 1
            continue
        cursor = index + 2
        next_word_id = safe_int(lines[cursor])
        if next_word_id == word_id + 1 and cursor + 1 < len(lines):
            cursor += 1
        gesture_count = 1
        possible_count = safe_int(lines[cursor])
        if possible_count is not None and 1 <= possible_count <= 50 and cursor + 1 < len(lines):
            gesture_count = possible_count
            cursor += 1
        word_text = normalize_word_text(lines[cursor])
        next_cursor = cursor + 1
        possible_trailing_count = safe_int(lines[next_cursor]) if next_cursor < len(lines) else None
        next_row_word_id = safe_int(lines[next_cursor + 1]) if next_cursor + 1 < len(lines) else None
        if (
            possible_trailing_count is not None
            and 1 <= possible_trailing_count <= 50
            and (next_row_word_id == word_id + 1 or next_cursor + 2 >= len(lines))
        ):
            gesture_count = possible_trailing_count
            next_cursor += 1
        if should_skip_pdf_word(word_text):
            index += 1
            continue
        items.append(
            {
                "word_id": word_id,
                "page": page,
                "count": gesture_count,
                "uzbek": word_text,
                "source_pdf": path.name,
                "source_set": source_set_from_pdf(path),
            }
        )
        index = next_cursor
    return items


def should_skip_pdf_word(text: str) -> bool:
    lowered = text.lower()
    return (
        not text
        or text == "ФОН"
        or lowered.startswith("page ")
        or "signer_" in lowered
        or lowered in {"uzbek", "i = №", "ii = №"}
        or bool(re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", text))
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
        count_text = ""
        word_parts = []
        for x, text in sorted(cells):
            if x < 55:
                word_id_text += text
            elif x < 90:
                page_text += text
            elif x < 130 and re.fullmatch(r"\d{1,3}", text.strip()):
                count_text += text
            elif x < 385:
                word_parts.append(text)
            elif x < 430 and re.fullmatch(r"\d{1,3}", text.strip()):
                count_text += text
        word_id = safe_int(re.sub(r"\D+", "", word_id_text))
        page = safe_int(re.sub(r"\D+", "", page_text))
        gesture_count = safe_int(re.sub(r"\D+", "", count_text), 1) or 1
        word_text = normalize_word_text("".join(word_parts))
        if word_id is None or page is None or should_skip_pdf_word(word_text):
            continue
        items.append(
            {
                "word_id": word_id,
                "page": page,
                "count": max(1, gesture_count),
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


def short_device_id(value) -> str:
    text = str(value or "")
    if len(text) <= 14:
        return text
    return f"{text[:7]}...{text[-4:]}"


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


def recording_command_timeout(config: dict) -> float:
    return float(config.get("record_command_timeout_seconds", max(8.0, float(config.get("timeout_seconds", 1.5)))))


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


def local_sidecar_payload(video: dict, target: Path, phone: dict) -> dict:
    size_bytes = target.stat().st_size if target.exists() else safe_int(video.get("size"), 0)
    status = str(video.get("status") or ("error" if not size_bytes else "ok"))
    if safe_int(size_bytes, 0) == 0:
        status = "error"
    return {
        "record": safe_int(video.get("record") or video.get("recordIndex")),
        "signer": video.get("signer") or video.get("signerId") or video.get("signer_id"),
        "word_id": safe_int(video.get("word_id") or video.get("wordId") or video.get("global_index")),
        "word": video.get("word") or video.get("gloss_uz"),
        "take": video.get("take") or video.get("takeLabel") or video.get("take_label"),
        "device": safe_int(video.get("device") or video.get("deviceSlot") or phone.get("device_slot")),
        "started_at": video.get("started_at") or video.get("recordingStartedAt"),
        "stopped_at": video.get("stopped_at") or video.get("created_at") or video.get("createdAt"),
        "duration_ms": safe_int(video.get("duration_ms")),
        "size_bytes": safe_int(size_bytes, 0),
        "status": status,
        "app_version": video.get("app_version") or APP_VERSION,
        "file": target.name,
        "source_device": phone_display_name(phone),
    }


def send_all(config: dict, endpoint: str, task: dict | None = None) -> list[tuple[str, str]]:
    phones = get_phones(config, discover=not endpoint in {"/start", "/stop", "/toggle"})
    timeout = (
        recording_command_timeout(config)
        if endpoint in {"/start", "/stop", "/toggle"}
        else float(config.get("timeout_seconds", 1.5))
    )
    if endpoint == "/start" and config.get("check_ready_before_start", False):
        check_ready_for_recording(config, phones, timeout)
    if endpoint == "/start" and config.get("block_recording_if_missing_phones", True):
        check_all_configured_phones_online(config, timeout)
    endpoint_by_phone = build_endpoint_map(config, phones, endpoint, task=task)
    retries = max(1, int(config.get("stop_retry_count", 2))) if endpoint == "/stop" else 1
    retry_delay = max(0.0, float(config.get("stop_retry_delay_seconds", 0.15)))

    def request_with_retry(phone: dict) -> tuple[str, str]:
        last_result = (phone_display_name(phone), "ERROR: not sent")
        for attempt in range(retries):
            last_result = request_phone(phone, endpoint_by_phone[id(phone)], timeout)
            if not str(last_result[1]).startswith("ERROR:"):
                return last_result
            if attempt + 1 < retries and retry_delay:
                time.sleep(retry_delay)
        return last_result

    results = []
    with ThreadPoolExecutor(max_workers=len(phones)) as executor:
        futures = {
            executor.submit(request_with_retry, phone): phone
            for phone in phones
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results


def build_endpoint_map(
    config: dict,
    phones: list[dict],
    endpoint: str,
    task: dict | None = None,
    scan_remote_indexes: bool = True,
) -> dict[int, str]:
    if endpoint != "/start":
        return {id(phone): endpoint for phone in phones}

    now = datetime.now()
    date_stamp = now.strftime("%Y %m %d")
    time_stamp = now.strftime("%H%M%S")
    timeout = float(config.get("timeout_seconds", 3))
    if scan_remote_indexes:
        record_index = next_record_index(config, phones, timeout)
    else:
        record_index = int(config.get("next_index", 0))
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
            phone.get("camera_name")
            or safe_name(str(phone.get("device_label") or ""))
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
                    "app_version": APP_VERSION,
                }
            )
        query = urllib.parse.urlencode(params)
        endpoints[id(phone)] = f"/start?{query}"
    return endpoints


def send_start_fast(config: dict, task: dict | None = None) -> list[tuple[str, str]]:
    phones = get_phones(config, discover=False)
    if not phones:
        raise RuntimeError("No phones configured.")

    endpoint_by_phone = build_endpoint_map(config, phones, "/start", task=task, scan_remote_indexes=False)
    timeout = float(config.get("start_timeout_seconds", recording_command_timeout(config)))
    retries = max(1, int(config.get("start_retry_count", 1)))
    retry_delay = max(0.0, float(config.get("start_retry_delay_seconds", 0.08)))

    def request_start(phone: dict) -> tuple[str, str]:
        last_result = (phone_display_name(phone), "ERROR: not sent")
        for attempt in range(retries):
            last_result = request_phone(phone, endpoint_by_phone[id(phone)], timeout)
            if not str(last_result[1]).startswith("ERROR:"):
                return last_result
            if attempt + 1 < retries and retry_delay:
                time.sleep(retry_delay)
        return last_result

    results = []
    with ThreadPoolExecutor(max_workers=len(phones)) as executor:
        futures = [executor.submit(request_start, phone) for phone in phones]
        for future in as_completed(futures):
            results.append(future.result())
    return results


def start_result_failures(results: list[tuple[str, str]], required: int) -> list[str]:
    failures = []
    ok_count = 0
    for name, body in results:
        if str(body).startswith("ERROR:"):
            failures.append(f"{name}: {body}")
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            failures.append(f"{name}: bad response")
            continue
        if not payload.get("ok", True) or not payload.get("recording", False):
            failures.append(f"{name}: {payload.get('error', body)}")
            continue
        ok_count += 1
    if ok_count < required:
        failures.append(f"connected started {ok_count}/{required}")
    return failures


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
                if target.suffix.lower() == ".mp4":
                    sidecar = target.with_suffix(".json")
                    sidecar.write_text(
                        json.dumps(local_sidecar_payload(video, target, phone), indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
            results.append((name, f"downloaded {count}, total {len(videos)}"))
        except Exception as error:
            results.append((name, f"ERROR: {error}"))
    return results


def list_videos_all(config: dict) -> list[dict]:
    phones = configured_phones(config)
    timeout = float(config.get("video_list_timeout_seconds", max(8.0, float(config.get("timeout_seconds", 3)))))
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


def payload_video_matches_task(payload: dict, task: dict | None) -> bool:
    video_name = str(payload.get("lastVideoName") or payload.get("name") or "")
    if not task:
        return bool(video_name)
    expected_session = str(task.get("session_id") or "")
    expected_record = safe_int(task.get("record_index"))
    metadata = payload.get("lastVideoMetadata") if isinstance(payload.get("lastVideoMetadata"), dict) else payload
    actual_session = str(
        payload.get("sessionId")
        or payload.get("session_id")
        or metadata.get("sessionId")
        or metadata.get("session_id")
        or ""
    )
    actual_record = safe_int(
        payload.get("recordIndex")
        or payload.get("record")
        or metadata.get("recordIndex")
        or metadata.get("record")
    )
    if expected_session and actual_session and actual_session != expected_session:
        return False
    if expected_record is not None and actual_record is not None and actual_record != expected_record:
        return False
    if expected_session and expected_session not in video_name and actual_record is None:
        return False
    return bool(video_name)


def stop_payload_is_confirmed(body: str, task: dict | None) -> bool:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    if not payload.get("ok", True):
        return False
    size_bytes = safe_int(payload.get("lastVideoSizeBytes") or payload.get("size") or payload.get("size_bytes"))
    if size_bytes is not None and size_bytes <= 0:
        return False
    return payload_video_matches_task(payload, task)


def stop_payload_from_video(phone: dict, video: dict) -> dict:
    metadata = dict(video)
    return {
        "ok": True,
        "recording": False,
        "lastVideoPath": video.get("relativePath") or video.get("relative_path") or video.get("path"),
        "lastVideoName": video.get("name"),
        "lastVideoSizeBytes": safe_int(video.get("size") or video.get("size_bytes")),
        "lastVideoMetadata": metadata,
        "recordIndex": safe_int(video.get("recordIndex") or video.get("record")),
        "startedAt": video.get("started_at") or video.get("startedAt"),
        "stoppedAt": video.get("stopped_at") or video.get("created_at") or video.get("createdAt"),
        "sessionId": video.get("sessionId") or video.get("session_id"),
        "deviceId": phone.get("device_id"),
        "deviceSlot": safe_int(phone.get("device_slot")),
        "deviceLabel": phone.get("device_label") or phone.get("name"),
        "confirmedBy": "videos_poll",
    }


def find_saved_video_on_phone(phone: dict, task: dict | None, timeout: float) -> dict | None:
    status = get_json(phone, "/status", timeout)
    if stop_payload_is_confirmed(json.dumps(status, ensure_ascii=False), task):
        status["ok"] = True
        status["recording"] = False
        status["confirmedBy"] = "status_poll"
        return status
    payload = get_json(phone, "/videos", timeout)
    for video in payload.get("videos", []):
        if isinstance(video, dict) and payload_video_matches_task(video, task):
            return stop_payload_from_video(phone, video)
    return None


def confirm_stop_saves(
    config: dict,
    stop_results: list[tuple[str, str]],
    task: dict | None,
) -> list[tuple[str, str]]:
    phones = configured_phones(config)
    timeout = float(config.get("timeout_seconds", 3))
    video_timeout = float(config.get("video_list_timeout_seconds", max(8.0, timeout)))
    confirm_timeout = max(0.0, float(config.get("post_stop_confirm_timeout_seconds", 12.0)))
    interval = max(0.1, float(config.get("post_stop_confirm_interval_seconds", 0.75)))
    result_by_name = {name: body for name, body in stop_results}
    confirmed: dict[str, str] = {}
    pending = []
    for phone in phones:
        name = phone_display_name(phone)
        body = result_by_name.get(name, "ERROR: no stop response")
        if stop_payload_is_confirmed(body, task):
            confirmed[name] = body
        else:
            pending.append(phone)

    deadline = time.time() + confirm_timeout
    last_error_by_name: dict[str, str] = {
        phone_display_name(phone): result_by_name.get(phone_display_name(phone), "ERROR: no stop response")
        for phone in pending
    }
    while pending and time.time() <= deadline:
        remaining = []
        with ThreadPoolExecutor(max_workers=max(1, len(pending))) as executor:
            futures = {executor.submit(find_saved_video_on_phone, phone, task, video_timeout): phone for phone in pending}
            for future in as_completed(futures):
                phone = futures[future]
                name = phone_display_name(phone)
                try:
                    payload = future.result()
                except Exception as error:
                    last_error_by_name[name] = f"ERROR: save not confirmed yet: {error}"
                    remaining.append(phone)
                    continue
                if payload:
                    confirmed[name] = json.dumps(payload, ensure_ascii=False)
                else:
                    last_error_by_name[name] = "ERROR: saved file not found by post-stop polling"
                    remaining.append(phone)
        pending = remaining
        if pending and time.time() < deadline:
            time.sleep(interval)

    results = []
    for phone in phones:
        name = phone_display_name(phone)
        results.append((name, confirmed.get(name) or last_error_by_name.get(name) or result_by_name.get(name, "ERROR: no result")))
    return results


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
        self.signer_var = StringVar(
            value=signer_label_for(self.dataset_state.get("selected_signer_id", "signer_1"), self.dataset_state)
        )
        self.new_signer_var = StringVar(value="")
        self.word_var = StringVar(value="")
        self.progress_var = StringVar(value="")
        self.gesture_count_var = IntVar(value=max(1, safe_int(self.dataset_state.get("gesture_count"), 1) or 1))
        self.background_var = BooleanVar(value=bool(self.dataset_state.get("background_mode", False)))
        self.video_rows: dict[str, dict] = {}
        self.active_task: dict | None = None
        self.recording = False
        self._stop_command_running = False
        self.busy = False
        self.status = StringVar(value="Готово")
        self.record_start_time: float | None = None
        self.timer_var = StringVar(value="00:00:00")
        self.auto_stop_var = StringVar()
        self._timer_job = None
        self._auto_stop_job = None
        self._poll_job = None
        self._recording_watchdog_stop = threading.Event()
        self._recording_watchdog_thread: threading.Thread | None = None
        self._emergency_stop_running = False
        self._live_recording_log_job = None
        self._live_recording_log_path: Path | None = None
        self._live_recording_log_offset = 0
        self.device_status_cache: dict[str, dict] = {}
        self.session_history = load_session_history()
        self._session_started_at: dict[str, float] = {}
        self.recording_log_entries: list[str] = []
        self.recording_status_by_word: dict[str, str] = dict(
            self.dataset_state.get("recording_status_by_word", {})
            if isinstance(self.dataset_state.get("recording_status_by_word"), dict)
            else {}
        )
        self.camera_state_by_name: dict[str, str] = {}

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
            values=[signer_label_for(item[0], self.dataset_state) for item in signer_items(self.dataset_state)],
            state="readonly",
            width=34,
        )
        self.signer_combo.pack(side="left", padx=(6, 10))
        self.signer_combo.bind("<<ComboboxSelected>>", self.signer_changed)
        ttk.Label(dataset_top, text="New signer").pack(side="left")
        self.new_signer_entry = ttk.Entry(dataset_top, textvariable=self.new_signer_var, width=24)
        self.new_signer_entry.pack(side="left", padx=(6, 6))
        self.new_signer_entry.bind("<Return>", lambda _event: self.add_signer_clicked())
        ttk.Button(dataset_top, text="ADD", command=self.add_signer_clicked).pack(side="left", padx=(0, 4))
        ttk.Button(dataset_top, text="UPDATE", command=self.update_signer_clicked).pack(side="left", padx=(0, 4))
        ttk.Button(dataset_top, text="DELETE", command=self.delete_signer_clicked).pack(side="left", padx=(0, 4))
        self.undo_delete_signer_button = ttk.Button(dataset_top, text="UNDO", command=self.undo_delete_signer_clicked)
        self.undo_delete_signer_button.pack(side="left", padx=(0, 8))
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

        word_columns = ttk.Frame(dataset_frame)
        word_columns.pack(fill="x", pady=(8, 0))
        word_columns.columnconfigure(0, weight=1, uniform="word_columns")
        word_columns.columnconfigure(1, weight=1, uniform="word_columns")
        self.word_trees = []
        for column_index in range(2):
            tree = ttk.Treeview(
                word_columns,
                columns=("word", "count", "take"),
                show="headings",
                height=6,
                selectmode="browse",
            )
            tree.heading("word", text="Word")
            tree.heading("count", text="count")
            tree.heading("take", text="Take")
            tree.column("word", width=390, stretch=True)
            tree.column("count", width=48, stretch=False, anchor="center")
            tree.column("take", width=64, stretch=False, anchor="center")
            tree.tag_configure("ok", foreground="#1e8449")
            tree.tag_configure("error", foreground="#c0392b")
            tree.tag_configure("current", background="#d6eaf8")
            tree.grid(row=0, column=column_index, sticky="ew", padx=(0, 6) if column_index == 0 else (6, 0))
            tree.bind("<<TreeviewSelect>>", self.word_tree_selected)
            self.word_trees.append(tree)

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

        mid_frame = ttk.Frame(frame)
        mid_frame.pack(fill="x", pady=(0, 12))
        mid_frame.columnconfigure(0, weight=0)
        mid_frame.columnconfigure(1, weight=1)

        ws_frame = ttk.Frame(frame)

        ws_row = ttk.Frame(ws_frame)

        self.ws_record_button = ttk.Button(ws_row, text="SYNC START", command=self.ws_toggle_clicked)

        self.ws_status_button = ttk.Button(ws_row, text="WS статус", command=self.ws_status_clicked)


        live_logs = ttk.LabelFrame(mid_frame, text="Live recording logs", padding=6)
        live_logs.grid(row=0, column=0, sticky="nw")
        live_logs.columnconfigure(0, weight=1)

        self.live_recording_log_tree = ttk.Treeview(
            live_logs,
            columns=("time", "event", "details"),
            show="headings",
            height=4,
            selectmode="browse",
        )
        for col, title, width, stretch in (
            ("time", "Time", 82, False),
            ("event", "Event", 110, False),
            ("details", "Latest recording log", 430, False),
        ):
            self.live_recording_log_tree.heading(col, text=title)
            self.live_recording_log_tree.column(col, width=width, stretch=stretch)
        self.live_recording_log_tree.tag_configure("error", foreground="#c0392b")
        self.live_recording_log_tree.tag_configure("ok", foreground="#1e8449")
        self.live_recording_log_tree.tag_configure("recording", foreground="#b9770e")
        self.live_recording_log_tree.grid(row=0, column=0, sticky="ew")

        live_log_scroll = ttk.Scrollbar(live_logs, orient="vertical", command=self.live_recording_log_tree.yview)
        live_log_scroll.grid(row=0, column=1, sticky="ns")
        self.live_recording_log_tree.configure(yscrollcommand=live_log_scroll.set)

        devices = ttk.LabelFrame(frame, text="Devices", padding=8)
        devices.pack(fill="x", pady=(0, 12))
        devices.columnconfigure(0, weight=1)

        devices_table = ttk.Frame(devices)
        devices_table.grid(row=0, column=0, sticky="ew")
        devices_table.columnconfigure(0, weight=1)

        self.devices_tree = ttk.Treeview(
            devices_table,
            columns=("slot", "camera", "state", "device_id", "device", "url", "free", "battery"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        self.devices_tree.heading("slot", text="Slot")
        self.devices_tree.heading("camera", text="Camera name")
        self.devices_tree.heading("state", text="State")
        self.devices_tree.heading("device_id", text="Device ID")
        self.devices_tree.heading("device", text="Device")
        self.devices_tree.heading("url", text="URL")
        self.devices_tree.heading("free", text="Free")
        self.devices_tree.heading("battery", text="Battery")
        self.devices_tree.column("slot", width=52, stretch=False)
        self.devices_tree.column("camera", width=110, stretch=False)
        self.devices_tree.column("state", width=90, stretch=False)
        self.devices_tree.column("device_id", width=120, stretch=False)
        self.devices_tree.column("device", width=135, stretch=False)
        self.devices_tree.column("url", width=250, stretch=True)
        self.devices_tree.column("free", width=90, stretch=False)
        self.devices_tree.column("battery", width=90, stretch=False)
        self.devices_tree.tag_configure("offline", foreground="#c0392b")
        self.devices_tree.tag_configure("saved", foreground="#1e8449")
        self.devices_tree.tag_configure("recording", foreground="#b9770e")
        self.devices_tree.tag_configure("warning", foreground="#b9770e")
        self.devices_tree.grid(row=0, column=0, sticky="ew")
        devices_scroll = ttk.Scrollbar(devices_table, orient="vertical", command=self.devices_tree.yview)
        devices_scroll.grid(row=0, column=1, sticky="ns")
        self.devices_tree.configure(yscrollcommand=devices_scroll.set)
        self.devices_tree.bind("<<TreeviewSelect>>", self.device_selected)

        self.device_slot_var = StringVar()
        self.camera_name_var = StringVar()

        videos = ttk.Frame(frame)
        video_top_actions = ttk.Frame(videos)
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
        self.refresh_undo_delete_signer_button()
        self.refresh_device_table()
        self.start_status_polling()
        self.start_live_recording_log_polling()

    def write(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def recording_log_path(self, when: datetime | None = None) -> Path:
        stamp = (when or datetime.now()).strftime("%Y%m%d")
        return recording_log_dir() / f"recording_log_{stamp}.ndjson"

    def append_recording_log_line(self, line: str, when: datetime | None = None) -> Path:
        path = self.recording_log_path(when)
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return path

    def recording_event_write(self, event: str, **fields) -> dict:
        now = datetime.now()
        payload = {
            "ts": now.astimezone().isoformat(timespec="milliseconds"),
            "event": event,
            "app_version": APP_VERSION,
        }
        payload.update({key: value for key, value in fields.items() if value is not None})
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.recording_log_entries.append(line)
        self.append_recording_log_line(line, now)
        if hasattr(self, "recording_log"):
            self.recording_log.insert("end", line + "\n")
            self.recording_log.see("end")
        self.insert_live_recording_log_line(line)
        try:
            current_path = self.recording_log_path(now)
            if current_path == self._live_recording_log_path:
                self._live_recording_log_offset = current_path.stat().st_size
        except OSError:
            pass
        return payload

    def recording_log_write(self, message: str) -> None:
        self.recording_event_write("LOG", message=message)

    def latest_recording_log_path(self) -> Path:
        today = self.recording_log_path()
        if today.exists():
            return today
        logs = sorted(
            recording_log_dir().glob("recording_log_*.ndjson"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
        )
        return logs[-1] if logs else today

    def start_live_recording_log_polling(self) -> None:
        self.refresh_live_recording_log(initial=True)

    def refresh_live_recording_log(self, initial: bool = False) -> None:
        path = self.latest_recording_log_path()
        try:
            size = path.stat().st_size if path.exists() else 0
        except OSError:
            size = 0

        path_changed = path != self._live_recording_log_path
        if initial or path_changed or size < self._live_recording_log_offset:
            self._live_recording_log_path = path
            self._live_recording_log_offset = 0
            if hasattr(self, "live_recording_log_tree"):
                self.live_recording_log_tree.delete(*self.live_recording_log_tree.get_children())
            if path.exists():
                for line in self.tail_recording_log_lines(path, limit=60):
                    self.insert_live_recording_log_line(line)
                self._live_recording_log_offset = size
        elif path.exists() and size > self._live_recording_log_offset:
            try:
                with path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(self._live_recording_log_offset)
                    lines = f.readlines()
                    self._live_recording_log_offset = f.tell()
            except OSError:
                lines = []
            for line in lines:
                self.insert_live_recording_log_line(line)

        self._live_recording_log_job = self.root.after(1000, self.refresh_live_recording_log)

    def tail_recording_log_lines(self, path: Path, limit: int = 60) -> list[str]:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\n") for line in deque(f, maxlen=limit) if line.strip()]
        except OSError:
            return []

    def insert_live_recording_log_line(self, line: str) -> None:
        if not line.strip() or not hasattr(self, "live_recording_log_tree"):
            return
        row = self.live_recording_log_row(line)
        tag = self.live_recording_log_tag(row)
        tree = self.live_recording_log_tree
        tree.insert(
            "",
            "end",
            values=(row["time"], row["event"], row["details"]),
            tags=(tag,) if tag else (),
        )
        children = tree.get_children()
        if len(children) > 120:
            tree.delete(*children[: len(children) - 120])
        tree.see(tree.get_children()[-1])

    def live_recording_log_row(self, line: str) -> dict[str, str]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return {"time": "", "event": "RAW", "status": "", "details": line[:160]}

        ts = str(payload.get("ts") or "")
        time_text = ts[11:23] if len(ts) >= 23 else ts
        word = str(payload.get("word") or payload.get("message") or "")
        word_id = payload.get("word_id")
        if word_id not in (None, "") and word:
            word = f"{word_id} {word}"
        status = str(payload.get("status") or "")
        failures = payload.get("failures")
        if not status and isinstance(failures, list):
            status = "ok" if not failures else f"{len(failures)} failed"
        file_name = str(payload.get("file") or payload.get("path") or "")
        if "\\" in file_name or "/" in file_name:
            file_name = Path(file_name).name
        device = str(payload.get("device") or payload.get("device_label") or "")
        take = str(payload.get("take") or "")
        event = str(payload.get("event") or "")
        parts = []
        if device:
            parts.append(device)
        if word:
            parts.append(f"{word} / take {take}" if take else word)
        elif take:
            parts.append(f"take {take}")
        if status:
            parts.append(status)
        if file_name:
            parts.append(file_name)
        return {"time": time_text, "event": event, "status": status, "details": " | ".join(parts)}

    def live_recording_log_tag(self, row: dict[str, str]) -> str:
        status = row.get("status", "").lower()
        event = row.get("event", "").lower()
        if "error" in status or "failed" in status or "failed" in event:
            return "error"
        if "warning" in status or "warning" in event:
            return "recording"
        if status == "ok" or "save" in event or "check" in event:
            return "ok"
        if "start" in event or "record" in event:
            return "recording"
        return ""

    def save_recording_log_file(self, path: Path | None = None) -> Path:
        if path is None:
            path = self.recording_log_path()
            path.parent.mkdir(exist_ok=True)
            path.touch(exist_ok=True)
            return path
        content = "\n".join(self.recording_log_entries)
        if content:
            content += "\n"
        if path != self.recording_log_path():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.exists():
            path.parent.mkdir(exist_ok=True)
            path.touch()
        return path

    def save_recording_log_clicked(self) -> None:
        initial = self.recording_log_path()
        path = filedialog.asksaveasfilename(
            title="Save recording log",
            initialdir=str(initial.parent),
            initialfile=initial.name,
            defaultextension=".ndjson",
            filetypes=(("NDJSON log", "*.ndjson"), ("All files", "*.*")),
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

    def task_event_fields(self, task: dict | None) -> dict:
        if not task:
            return {"record": None}
        devices = [
            {
                "device": phone_display_name(phone),
                "device_id": phone.get("device_id"),
                "slot": safe_int(phone.get("device_slot")),
                "camera": phone.get("camera_name"),
                "url": phone.get("url"),
            }
            for phone in configured_phones(self.config)
        ]
        return {
            "session": task.get("session_id"),
            "record": task.get("record_index"),
            "signer": task.get("signer_id"),
            "signer_name": task.get("signer_name"),
            "word_id": safe_int(task.get("word_id")),
            "word": task.get("word"),
            "take": task.get("take_label"),
            "mode": task.get("mode"),
            "app_version": task.get("app_version") or APP_VERSION,
            "devices": devices,
        }

    def log_phone_results(self, event: str, results: list[tuple[str, str]]) -> None:
        for name, body in results:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.root.after(0, lambda n=name, b=body: self.recording_event_write(event, device=n, status="error", reason=b))
                continue
            if not payload.get("ok", True):
                self.root.after(
                    0,
                    lambda n=name, p=payload: self.recording_event_write(
                        event,
                        device=n,
                        device_id=p.get("deviceId"),
                        device_slot=safe_int(p.get("deviceSlot")),
                        device_label=p.get("deviceLabel"),
                        status="error",
                        reason=p.get("error", p),
                        session=p.get("sessionId"),
                    ),
                )
                continue
            size_bytes = safe_int(payload.get("lastVideoSizeBytes"))
            status = "ok"
            reason = None
            if event in {"STOP_SAVE", "SAVE"}:
                if not payload.get("lastVideoName"):
                    status = "error"
                    reason = "missing_video_name"
                elif size_bytes is not None and size_bytes <= 0:
                    status = "error"
                    reason = "zero_size"
            self.root.after(
                0,
                lambda n=name, p=payload, s=status, r=reason, z=size_bytes: self.recording_event_write(
                    event,
                    device=n,
                    device_id=p.get("deviceId"),
                    device_slot=safe_int(p.get("deviceSlot")),
                    device_label=p.get("deviceLabel"),
                    status=s,
                    reason=r,
                    session=p.get("sessionId"),
                    file=p.get("lastVideoName") or p.get("activeVideoName"),
                    size_bytes=z,
                ),
            )

    def stop_save_failures(self, results: list[tuple[str, str]], task: dict | None = None) -> list[str]:
        failures = []
        expected_session = str(task.get("session_id")) if task and task.get("session_id") else ""
        expected_record = safe_int(task.get("record_index")) if task else None
        for name, body in results:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                failures.append(f"{name}: bad response")
                continue
            if not payload.get("ok", True):
                failures.append(f"{name}: {payload.get('error', 'ERROR')}")
                continue
            size_bytes = safe_int(payload.get("lastVideoSizeBytes"))
            if expected_session and str(payload.get("sessionId") or "") != expected_session:
                failures.append(f"{name}: session mismatch ({payload.get('sessionId') or 'none'})")
                continue
            metadata = payload.get("lastVideoMetadata") if isinstance(payload.get("lastVideoMetadata"), dict) else {}
            actual_record = safe_int(payload.get("recordIndex") or metadata.get("recordIndex") or metadata.get("record"))
            if expected_record is not None and actual_record is not None and actual_record != expected_record:
                failures.append(f"{name}: record mismatch ({actual_record})")
                continue
            if not payload.get("lastVideoName"):
                failures.append(f"{name}: no saved file confirmation")
            elif size_bytes is not None and size_bytes <= 0:
                failures.append(f"{name}: zero-byte file")
        return failures

    def save_dataset(self) -> None:
        self.dataset_state["selected_signer_id"] = self.selected_signer_id()
        self.dataset_state["gesture_count"] = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        self.dataset_state["background_mode"] = bool(self.background_var.get())
        self.dataset_state["custom_signers"] = normalize_custom_signers(self.dataset_state.get("custom_signers", []))
        self.dataset_state["deleted_signers"] = normalize_deleted_signers(self.dataset_state.get("deleted_signers", []))
        self.dataset_state["recording_status_by_word"] = self.recording_status_by_word
        save_dataset_state(self.dataset_state)

    def selected_signer_id(self) -> str:
        selected = self.signer_var.get()
        if " - " in selected:
            return selected.split(" - ", 1)[0]
        return str(self.dataset_state.get("selected_signer_id") or "signer_1")

    def refresh_signer_combo(self) -> None:
        values = [signer_label_for(item[0], self.dataset_state) for item in signer_items(self.dataset_state)]
        self.signer_combo.configure(values=values)
        selected_id = self.dataset_state.get("selected_signer_id", self.selected_signer_id())
        selected_label = signer_label_for(str(selected_id), self.dataset_state)
        if selected_label in values:
            self.signer_var.set(selected_label)

    def custom_signer_map(self) -> dict[str, str]:
        return dict(normalize_custom_signers(self.dataset_state.get("custom_signers", [])))

    def set_custom_signers(self, custom: dict[str, str]) -> None:
        self.dataset_state["custom_signers"] = sorted(
            custom.items(), key=lambda item: safe_int(item[0].split("_", 1)[1], 0) or 0
        )

    def deleted_signer_set(self) -> set[str]:
        return set(normalize_deleted_signers(self.dataset_state.get("deleted_signers", [])))

    def set_deleted_signers(self, deleted: set[str]) -> None:
        self.dataset_state["deleted_signers"] = normalize_deleted_signers(list(deleted))

    def select_first_available_signer(self) -> None:
        items = signer_items(self.dataset_state)
        signer_id = items[0][0] if items else "signer_1"
        self.dataset_state["selected_signer_id"] = signer_id
        self.signer_var.set(signer_label_for(signer_id, self.dataset_state))

    def refresh_undo_delete_signer_button(self) -> None:
        if not hasattr(self, "undo_delete_signer_button"):
            return
        state = NORMAL if isinstance(self.dataset_state.get("last_deleted_signer"), dict) else DISABLED
        self.undo_delete_signer_button.configure(state=state)

    def fill_signer_entry_from_selection(self) -> None:
        signer_id = self.selected_signer_id()
        custom = self.custom_signer_map()
        if signer_id in custom:
            number = signer_id.split("_", 1)[1]
            self.new_signer_var.set(f"{number} {custom[signer_id]}")
        else:
            self.new_signer_var.set("")

    def add_signer_clicked(self) -> None:
        try:
            signer_id, name = parse_signer_entry(self.new_signer_var.get())
        except ValueError as error:
            messagebox.showerror("Add signer", str(error))
            return
        if signer_id in SIGNER_NAMES:
            messagebox.showerror("Add signer", f"{signer_id} already exists")
            return
        custom = self.custom_signer_map()
        if signer_id in custom:
            messagebox.showerror("Add signer", f"{signer_id} already exists")
            return
        custom[signer_id] = name
        self.set_custom_signers(custom)
        self.dataset_state["selected_signer_id"] = signer_id
        self.signer_var.set(signer_label_for(signer_id, self.dataset_state))
        self.new_signer_var.set("")
        self.save_dataset()
        self.refresh_signer_combo()
        self.refresh_dataset_labels()
        self.refresh_undo_delete_signer_button()
        self.write(f"Signer added: {signer_label_for(signer_id, self.dataset_state)}")

    def update_signer_clicked(self) -> None:
        old_id = self.selected_signer_id()
        custom = self.custom_signer_map()
        if old_id not in custom:
            messagebox.showerror("Update signer", "Only added signers can be changed")
            return
        try:
            new_id, name = parse_signer_entry(self.new_signer_var.get())
        except ValueError as error:
            messagebox.showerror("Update signer", str(error))
            return
        if new_id in SIGNER_NAMES:
            messagebox.showerror("Update signer", f"{new_id} already exists")
            return
        if new_id != old_id and new_id in custom:
            messagebox.showerror("Update signer", f"{new_id} already exists")
            return
        custom.pop(old_id)
        custom[new_id] = name
        self.set_custom_signers(custom)
        self.dataset_state["selected_signer_id"] = new_id
        self.signer_var.set(signer_label_for(new_id, self.dataset_state))
        self.new_signer_var.set("")
        self.save_dataset()
        self.refresh_signer_combo()
        self.refresh_dataset_labels()
        self.refresh_undo_delete_signer_button()
        self.write(f"Signer updated: {old_id} -> {signer_label_for(new_id, self.dataset_state)}")

    def delete_signer_clicked(self) -> None:
        signer_id = self.selected_signer_id()
        available = signer_items(self.dataset_state)
        if len(available) <= 1:
            messagebox.showerror("Delete signer", "At least one signer must remain")
            return
        custom = self.custom_signer_map()
        names = signer_names(self.dataset_state)
        name = names.get(signer_id, signer_id)
        if signer_id not in names:
            messagebox.showerror("Delete signer", "Select a signer to delete")
            return
        if not messagebox.askyesno("Delete signer", f"Delete {signer_label_for(signer_id, self.dataset_state)}?"):
            return
        was_custom = signer_id in custom
        if was_custom:
            custom.pop(signer_id)
            self.set_custom_signers(custom)
        else:
            deleted = self.deleted_signer_set()
            deleted.add(signer_id)
            self.set_deleted_signers(deleted)
        self.dataset_state["last_deleted_signer"] = {
            "id": signer_id,
            "name": name,
            "was_custom": was_custom,
        }
        self.select_first_available_signer()
        self.new_signer_var.set("")
        self.save_dataset()
        self.refresh_signer_combo()
        self.refresh_dataset_labels()
        self.refresh_undo_delete_signer_button()
        self.write(f"Signer deleted: {signer_id}")

    def undo_delete_signer_clicked(self) -> None:
        deleted_signer = self.dataset_state.get("last_deleted_signer")
        if not isinstance(deleted_signer, dict):
            messagebox.showinfo("Undo delete signer", "No deleted signer to restore")
            return
        signer_id = str(deleted_signer.get("id") or "").strip()
        name = str(deleted_signer.get("name") or signer_id).strip()
        match = re.fullmatch(r"(?:signer_)?(\d{1,4})", signer_id)
        if not match or not name:
            self.dataset_state["last_deleted_signer"] = None
            self.save_dataset()
            self.refresh_undo_delete_signer_button()
            messagebox.showerror("Undo delete signer", "Deleted signer data is invalid")
            return
        signer_id = f"signer_{int(match.group(1))}"
        custom = self.custom_signer_map()
        if bool(deleted_signer.get("was_custom")):
            custom[signer_id] = name
            self.set_custom_signers(custom)
        else:
            deleted = self.deleted_signer_set()
            deleted.discard(signer_id)
            self.set_deleted_signers(deleted)
        self.dataset_state["selected_signer_id"] = signer_id
        self.signer_var.set(signer_label_for(signer_id, self.dataset_state))
        self.dataset_state["last_deleted_signer"] = None
        self.new_signer_var.set("")
        self.save_dataset()
        self.refresh_signer_combo()
        self.refresh_dataset_labels()
        self.refresh_undo_delete_signer_button()
        self.write(f"Signer restored: {signer_label_for(signer_id, self.dataset_state)}")

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
            self.refresh_word_columns()
            return
        word = self.current_word()
        if not word:
            self.word_var.set("IMPORT PDF")
            self.progress_var.set("No words imported")
            self.refresh_word_columns()
            return
        main_index = int(self.dataset_state.get("main_word_index", 0))
        view_index = int(self.dataset_state.get("view_word_index", main_index))
        gesture_count = word_gesture_count(word, self.dataset_state.get("gesture_count", 1))
        if safe_int(self.gesture_count_var.get(), 1) != gesture_count:
            self.gesture_count_var.set(gesture_count)
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(word_key(word), 0))
        mode = "manual back" if self.dataset_state.get("manual_back_mode") else "main queue"
        self.word_var.set(word_display(word))
        self.progress_var.set(
            f"{view_index + 1}/{len(words)} / take {min(done + 1, gesture_count)} of {gesture_count} / {mode}"
        )
        self.refresh_word_columns()

    def refresh_word_columns(self) -> None:
        if not hasattr(self, "word_trees"):
            return
        words = self.dataset_state.get("words", [])
        view_index = int(self.dataset_state.get("view_word_index", 0))
        midpoint = (len(words) + 1) // 2
        for tree in self.word_trees:
            tree.delete(*tree.get_children())
        for column_index, column_words in enumerate((words[:midpoint], words[midpoint:])):
            tree = self.word_trees[column_index]
            offset = 0 if column_index == 0 else midpoint
            for local_index, word in enumerate(column_words):
                index = offset + local_index
                key = word_key(word)
                status = self.recording_status_by_word.get(key, "")
                tags = []
                if status == "ok":
                    tags.append("ok")
                elif status == "error":
                    tags.append("error")
                if index == view_index and not self.background_var.get():
                    tags.append("current")
                done = int(self.dataset_state.get("takes_done_by_word", {}).get(key, 0))
                word_id = word_number_prefix(word.get("word_id"))
                label = f"{word_id} {word.get('uzbek', '')}".strip()
                tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(label, word_gesture_count(word, self.dataset_state.get("gesture_count", 1)), take_label(done + 1)),
                    tags=tuple(tags),
                )

    def word_tree_selected(self, event=None) -> None:
        widget = event.widget if event is not None else None
        if widget is None:
            return
        selected = widget.selection()
        if not selected:
            return
        index = safe_int(selected[0])
        words = self.dataset_state.get("words", [])
        if index is None or index < 0 or index >= len(words):
            return
        self.background_var.set(False)
        self.dataset_state["background_mode"] = False
        self.dataset_state["view_word_index"] = index
        self.dataset_state["manual_back_mode"] = index != int(self.dataset_state.get("main_word_index", 0))
        self.save_dataset()
        self.refresh_dataset_labels()

    def signer_changed(self, _event=None) -> None:
        self.dataset_state["selected_signer_id"] = self.selected_signer_id()
        self.fill_signer_entry_from_selection()
        self.save_dataset()
        self.refresh_dataset_labels()
        self.write(f"Signer selected: {self.signer_var.get()}")

    def gesture_count_changed(self) -> None:
        gesture_count = max(1, safe_int(self.gesture_count_var.get(), 1) or 1)
        self.dataset_state["gesture_count"] = gesture_count
        word = self.current_word()
        if word:
            word["count"] = gesture_count
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
            self.recording_status_by_word = {}
            self.dataset_state["manual_back_mode"] = False
            self.save_dataset()
            self.root.after(0, self.refresh_dataset_labels)
            return f"Imported {len(words)} words from {len(paths)} PDF(s)." + (
                "\n" + "\n".join(warnings) if warnings else ""
            )

        self.run_background("Importing PDF...", action)

    def build_current_task(self) -> dict:
        signer_id = self.selected_signer_id()
        signer_name = signer_names(self.dataset_state).get(signer_id, signer_id)
        gesture_count = word_gesture_count(None, self.gesture_count_var.get())
        if self.background_var.get():
            return {
                "signer_id": signer_id,
                "signer_name": signer_name,
                "signer_dir": signer_dir_name_for(signer_id, self.dataset_state),
                "mode": "background",
                "word": BACKGROUND_WORD,
                "word_id": "",
                "list": "",
                "word_dir": BACKGROUND_WORD,
                "take_number": 1,
                "take_label": take_label(1),
                "gesture_count": gesture_count,
                "retake": False,
                "app_version": APP_VERSION,
            }
        word = self.current_word()
        if not word:
            raise RuntimeError("Import PDF before recording")
        gesture_count = word_gesture_count(word, self.dataset_state.get("gesture_count", 1))
        if safe_int(self.gesture_count_var.get(), 1) != gesture_count:
            self.gesture_count_var.set(gesture_count)
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(word_key(word), 0))
        take_number = done + 1
        return {
            "signer_id": signer_id,
            "signer_name": signer_name,
            "signer_dir": signer_dir_name_for(signer_id, self.dataset_state),
            "mode": "word",
            "word": word.get("uzbek", ""),
            "word_id": word.get("word_id", ""),
            "list": word.get("source_set", ""),
            "word_dir": word_dir_name(word),
            "take_number": take_number,
            "take_label": take_label(take_number),
            "gesture_count": gesture_count,
            "retake": bool(self.dataset_state.get("retake_mode", False)),
            "app_version": APP_VERSION,
        }

    def complete_current_task(self, *, ok: bool = True) -> None:
        if self.background_var.get():
            return
        word = self.current_word()
        if not word:
            return
        gesture_count = word_gesture_count(word, self.dataset_state.get("gesture_count", 1))
        key = word_key(word)
        done = int(self.dataset_state.get("takes_done_by_word", {}).get(key, 0)) + 1
        self.dataset_state.setdefault("takes_done_by_word", {})[key] = done
        self.recording_status_by_word[key] = "ok" if ok else "error"
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
        self.recording_status_by_word = {}
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
            name = phone_display_name(phone)
            known_status = bool(device_status)
            state = self.camera_state_by_name.get(name) or (
                "online" if device_status.get("ok", False) else ("unknown" if not known_status else "offline")
            )
            values = (
                phone.get("device_slot", ""),
                phone.get("camera_name", ""),
                state,
                short_device_id(phone.get("device_id")),
                phone.get("device_name") or phone.get("device_label") or phone.get("name", ""),
                phone.get("url", ""),
                device_status.get("free", "—"),
                device_status.get("battery", "—"),
            )
            tags = (
                ("offline",)
                if state in {"offline", "error"} or (known_status and not device_status.get("ok", False))
                else (
                    ("saved",)
                    if state == "saved"
                    else (("recording",) if state == "recording" else (("warning",) if state == "warning" else ()))
                )
            )
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
        if self.recording:
            self.stop_recording_clicked()
        else:
            self.start_recording_clicked()

    def set_http_recording_state(self, recording: bool) -> None:
        self.recording = recording
        self.record_button.configure(text="STOP REC" if recording else "START REC")
        if recording:
            self.start_timer()
            self.start_recording_watchdog()
        else:
            self.stop_recording_watchdog()
            self.stop_timer()

    def start_recording_watchdog(self) -> None:
        if not self.config.get("recording_watchdog_enabled", True):
            return
        if self._recording_watchdog_thread is not None and self._recording_watchdog_thread.is_alive():
            return

        self._recording_watchdog_stop = threading.Event()
        stop_event = self._recording_watchdog_stop
        watched_task = self.active_task

        def worker() -> None:
            interval = max(0.2, float(self.config.get("recording_watchdog_interval_seconds", 0.5)))
            timeout = max(0.5, float(self.config.get("recording_watchdog_timeout_seconds", 1.5)))
            grace = max(0.0, float(self.config.get("recording_watchdog_start_grace_seconds", 5.0)))
            failure_limit = max(1, int(self.config.get("recording_watchdog_consecutive_failures", 3)))
            warning_cooldown = max(
                1.0,
                float(self.config.get("recording_watchdog_warning_cooldown_seconds", 10.0)),
            )
            can_stop_recording = bool(self.config.get("recording_watchdog_can_stop_recording", False)) and bool(
                self.config.get("abort_recording_on_phone_loss", False)
            )
            grace_until = time.time() + grace
            consecutive_failures: dict[str, int] = {}
            last_warning_at: dict[str, float] = {}

            while not stop_event.wait(interval):
                if not self.recording or self._stop_command_running:
                    return
                phones = configured_phones(self.config)
                if not phones:
                    continue

                failures: list[str] = []
                failed_names: set[str] = set()
                with ThreadPoolExecutor(max_workers=max(1, len(phones))) as executor:
                    futures = {executor.submit(get_json, phone, "/status", timeout): phone for phone in phones}
                    for future in as_completed(futures):
                        phone = futures[future]
                        name = phone_display_name(phone)
                        try:
                            status = future.result()
                        except Exception as error:
                            failed_names.add(name)
                            failures.append(f"{name}: no status ({error})")
                            continue
                        if time.time() >= grace_until and status.get("recording") is False:
                            failed_names.add(name)
                            failures.append(f"{name}: recording stopped")
                        elif status.get("recording") is True:
                            consecutive_failures.pop(name, None)

                now = time.time()
                if not failures or now < grace_until:
                    continue

                persistent_failures = []
                for failure in failures:
                    name = failure.split(":", 1)[0]
                    consecutive_failures[name] = consecutive_failures.get(name, 0) + 1
                    if consecutive_failures[name] >= failure_limit:
                        persistent_failures.append(failure)

                for name in list(consecutive_failures):
                    if name not in failed_names:
                        consecutive_failures.pop(name, None)

                if not persistent_failures:
                    continue

                reason = "; ".join(persistent_failures)
                if can_stop_recording:
                    self.root.after(0, lambda r=reason, t=watched_task: self.emergency_stop_recording(r, t))
                    return

                should_warn = any(
                    now - last_warning_at.get(failure.split(":", 1)[0], 0.0) >= warning_cooldown
                    for failure in persistent_failures
                )
                if not should_warn:
                    continue
                for failure in persistent_failures:
                    last_warning_at[failure.split(":", 1)[0]] = now

                def report_watchdog_warning(
                    r=reason,
                    t=watched_task,
                    items=tuple(persistent_failures),
                ) -> None:
                    if not self.recording or self._stop_command_running:
                        return
                    self.recording_event_write("WATCHDOG_WARNING", reason=r, **self.task_event_fields(t))
                    self.write(f"WATCHDOG WARNING: {r}")
                    self.status.set(f"Recording continues; watchdog warning: {r}")
                    for item in items:
                        self.camera_state_by_name[item.split(":", 1)[0]] = "warning"
                    self.refresh_device_table()

                self.root.after(0, report_watchdog_warning)

        self._recording_watchdog_thread = threading.Thread(target=worker, daemon=True)
        self._recording_watchdog_thread.start()

    def stop_recording_watchdog(self) -> None:
        self._recording_watchdog_stop.set()

    def emergency_stop_recording(self, reason: str, task: dict | None) -> None:
        if not self.recording or self._stop_command_running or self._emergency_stop_running:
            return
        self._emergency_stop_running = True
        self.recording_event_write("EMERGENCY_STOP", reason=reason, **self.task_event_fields(task))
        self.write(f"EMERGENCY STOP: {reason}")
        self.status.set(f"Emergency stop: {reason}")
        self.stop_recording_clicked()

    def start_recording_clicked(self) -> None:
        if self.busy:
            return

        try:
            task = self.build_current_task()
        except Exception as error:
            self.write(f"ERROR: {error}")
            self.status.set("Error")
            return

        phones = configured_phones(self.config)
        required = int(self.config.get("required_phone_count", self.config.get("min_phones", len(phones) or 1)))
        self.record_button.configure(state=DISABLED)
        self.status.set("Checking devices...")

        def worker() -> None:
            try:
                timeout = float(self.config.get("timeout_seconds", 3))
                check_all_configured_phones_online(self.config, timeout)
                check_ready_for_recording(self.config, phones, timeout)
                self.root.after(
                    0,
                    lambda: self.recording_event_write("START_PENDING", **self.task_event_fields(task)),
                )
                results = send_start_fast(self.config, task=task)
                failures = start_result_failures(results, required)
                if failures:
                    try:
                        send_all(self.config, "/stop", task=task)
                    except Exception:
                        pass
                    raise RuntimeError("START blocked: " + "; ".join(failures))
                task_text = (
                    f"{task.get('mode')} / {task.get('word')} "
                    f"/ take {task.get('take_label')}"
                )
                message = format_results("Command sent:", results)

                def apply_start_ack() -> None:
                    self.active_task = task
                    self.set_http_recording_state(True)
                    self.record_button.configure(state=NORMAL)
                    self._session_started_at["http"] = time.time()
                    self.recording_event_write("START", **self.task_event_fields(task))
                    self.log_phone_results("START_ACK", results)
                    self.camera_state_by_name.update({name: "recording" for name, body in results if not str(body).startswith("ERROR:")})
                    for name, body in results:
                        if str(body).startswith("ERROR:"):
                            self.camera_state_by_name[name] = "error"
                    self.refresh_device_table()
                    self.write(f"START task: {task_text}")
                    self.write(message)
                    if not self._stop_command_running:
                        self.status.set("Ready")

                self.root.after(0, apply_start_ack)
            except Exception as error:
                message = f"ERROR: {error}"

                def rollback() -> None:
                    if self.recording and self.active_task is task:
                        self.set_http_recording_state(False)
                        self._session_started_at.pop("http", None)
                    self.record_button.configure(state=NORMAL)
                    self.camera_state_by_name = {
                        phone_display_name(phone): "error"
                        for phone in configured_phones(self.config)
                    }
                    self.refresh_device_table()
                    self.recording_event_write("START_FAILED", reason=message, **self.task_event_fields(task))
                    self.write(message)
                    self.status.set("Error")

                self.root.after(0, rollback)

        threading.Thread(target=worker, daemon=True).start()

    def stop_recording_clicked(self) -> None:
        if self._stop_command_running:
            return

        task = self.active_task
        self._stop_command_running = True
        self.record_button.configure(state=DISABLED)
        self.status.set("Stopping recording...")

        def worker() -> None:
            try:
                stop_grace = 0.0 if self._emergency_stop_running else max(0.0, float(self.config.get("stop_grace_seconds", 0.75)))
                if stop_grace:
                    time.sleep(stop_grace)
                results = send_all(self.config, "/stop", task=task)
                videos = None
                if self.config.get("auto_refresh_videos_after_stop", False):
                    time.sleep(max(0.0, float(self.config.get("post_stop_video_refresh_delay_seconds", 1.5))))
                    videos = list_videos_all(self.config)
                saved_log = self.save_recording_log_file()
                results = confirm_stop_saves(self.config, results, task)
                failures = self.stop_save_failures(results, task)

                def apply_stop() -> None:
                    self.set_http_recording_state(False)
                    self.complete_current_task(ok=not failures)
                    if videos is not None:
                        self.refresh_videos_table(videos)
                    self.record_session_history("http")
                    self.recording_event_write("STOP", **self.task_event_fields(task))
                    self.log_phone_results("STOP_SAVE", results)
                    failed_names = {item.split(":", 1)[0] for item in failures}
                    required = int(self.config.get("required_phone_count", self.config.get("min_phones", len(results) or 1)))
                    saved_ok = max(0, len(results) - len(failed_names))
                    self.recording_event_write(
                        "SESSION_CHECK",
                        expected=required,
                        saved_ok=saved_ok,
                        failed=len(failed_names),
                        failures=failures,
                        **self.task_event_fields(task),
                    )
                    for name, _body in results:
                        self.camera_state_by_name[name] = "error" if name in failed_names else "saved"
                    self.refresh_device_table()
                    self.recording_event_write("LOG_SAVED", path=str(saved_log))
                    self.write(format_results("Command sent:", results))
                    if failures:
                        warning = "SAVE ERROR: " + "; ".join(failures)
                        self.write(warning)
                        self.status.set(warning)
                        messagebox.showerror("Save confirmation failed", warning)
                    else:
                        self.status.set("Ready")

                self.root.after(0, apply_stop)
            except Exception as error:
                message = f"ERROR: {error}"
                self.root.after(0, lambda m=message: self.write(m))
                self.root.after(0, lambda: self.status.set("Error"))
            finally:
                def finish() -> None:
                    self._stop_command_running = False
                    self._emergency_stop_running = False
                    self.record_button.configure(state=DISABLED if self.busy else NORMAL)

                self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

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
        if self._live_recording_log_job is not None:
            self.root.after_cancel(self._live_recording_log_job)
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
