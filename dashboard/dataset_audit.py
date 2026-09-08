import argparse
import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path


def read_ndjson(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if path.is_dir():
            files = sorted(path.glob("recording_log_*.ndjson"))
        else:
            files = [path]
        for file_path in files:
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                for line_number, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as error:
                        rows.append(
                            {
                                "event": "AUDIT_BAD_JSON",
                                "path": str(file_path),
                                "line": line_number,
                                "error": str(error),
                            }
                        )
                        continue
                    row["_log_path"] = str(file_path)
                    row["_log_line"] = line_number
                    rows.append(row)
    return rows


def video_index(roots: list[Path]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.mp4"):
            index[path.name].append(path)
    return index


def sidecar_metadata(video_path: Path) -> dict:
    sidecar = video_path.with_suffix(".json")
    if not sidecar.exists():
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def ffprobe_duration_ms(video_path: Path) -> int | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return int(float(result.stdout.strip()) * 1000)
    except ValueError:
        return None


def expected_items(path: Path) -> set[str]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            payload = payload.get("phrases") or payload.get("items") or payload.get("words") or []
        rows = payload if isinstance(payload, list) else []
        return {
            str(row.get("phrase_id") or row.get("word_id") or row.get("id"))
            for row in rows
            if isinstance(row, dict) and (row.get("phrase_id") or row.get("word_id") or row.get("id"))
        }
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = csv.DictReader(f)
            return {
                str(row.get("phrase_id") or row.get("word_id") or row.get("id"))
                for row in rows
                if row.get("phrase_id") or row.get("word_id") or row.get("id")
            }
    ids = set()
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            first = stripped.split(maxsplit=1)[0].strip(",;|")
            if first.isdigit():
                ids.add(first)
    return ids


def shown_items(rows: list[dict]) -> set[str]:
    result = set()
    for row in rows:
        if row.get("event") not in {"START", "START_PENDING"}:
            continue
        item_id = row.get("phrase_id") if row.get("mode") == "phrase" else row.get("word_id")
        if item_id not in (None, ""):
            result.add(str(item_id))
    return result


def audit(logs: list[Path], videos: list[Path], expected_list: Path | None, required_cameras: int, tolerance_ms: int) -> dict:
    rows = read_ndjson(logs)
    files = video_index(videos)
    missing_files = []
    zero_files = []
    sessions: dict[str, dict[str, int]] = defaultdict(dict)

    for row in rows:
        if row.get("event") != "STOP_SAVE" or row.get("status") != "ok":
            continue
        name = str(row.get("file") or "")
        session = str(row.get("session") or row.get("sessionId") or "")
        device = str(row.get("device") or row.get("device_label") or "")
        paths = files.get(name, [])
        if not paths:
            missing_files.append({"session": session, "device": device, "file": name})
            continue
        path = paths[0]
        size = path.stat().st_size
        if size <= 0:
            zero_files.append({"session": session, "device": device, "file": name})
        metadata = sidecar_metadata(path)
        duration = metadata.get("duration_ms") or row.get("duration_ms") or ffprobe_duration_ms(path)
        if duration is not None and session:
            sessions[session][device or name] = int(duration)

    incomplete_sessions = []
    duration_spread = []
    for session, durations in sessions.items():
        if len(durations) < required_cameras:
            incomplete_sessions.append({"session": session, "cameras": len(durations), "durations": durations})
        if len(durations) >= 2:
            spread = max(durations.values()) - min(durations.values())
            if spread > tolerance_ms:
                duration_spread.append({"session": session, "spread_ms": spread, "durations": durations})

    list_check = None
    if expected_list is not None:
        expected = expected_items(expected_list)
        shown = shown_items(rows)
        list_check = {
            "expected_count": len(expected),
            "shown_count": len(shown),
            "missing_ids": sorted(expected - shown, key=lambda value: int(value) if value.isdigit() else value),
            "extra_ids": sorted(shown - expected, key=lambda value: int(value) if value.isdigit() else value),
        }

    return {
        "logs_read": len(rows),
        "missing_files": missing_files,
        "zero_files": zero_files,
        "incomplete_sessions": incomplete_sessions,
        "duration_spread": duration_spread,
        "list_check": list_check,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Three Cam NDJSON logs against saved videos.")
    parser.add_argument("--logs", nargs="+", type=Path, required=True, help="NDJSON files or directories")
    parser.add_argument("--videos", nargs="+", type=Path, required=True, help="Video roots to scan recursively")
    parser.add_argument("--expected-list", type=Path, help="Expected phrase/word list in txt/csv/json")
    parser.add_argument("--required-cameras", type=int, default=3)
    parser.add_argument("--tolerance-ms", type=int, default=1500)
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    report = audit(args.logs, args.videos, args.expected_list, args.required_cameras, args.tolerance_ms)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"logs_read={report['logs_read']}")
        print(f"missing_files={len(report['missing_files'])}")
        print(f"zero_files={len(report['zero_files'])}")
        print(f"incomplete_sessions={len(report['incomplete_sessions'])}")
        print(f"duration_spread={len(report['duration_spread'])}")
        if report["list_check"] is not None:
            check = report["list_check"]
            print(f"expected_count={check['expected_count']} shown_count={check['shown_count']}")
            print(f"missing_ids={','.join(check['missing_ids'])}")
    has_failures = any(
        report[key]
        for key in ("missing_files", "zero_files", "incomplete_sessions", "duration_spread")
    )
    if report["list_check"] and report["list_check"]["missing_ids"]:
        has_failures = True
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
