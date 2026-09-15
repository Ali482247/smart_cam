import json
import tempfile
import unittest
from pathlib import Path

from datetime import datetime

import three_cam_controller as tcc
from three_cam_controller import (
    ControllerApp,
    ITEM_TYPE_PHRASE,
    ITEM_TYPE_WORD,
    actual_fps_from_payload,
    ensure_recording_day,
    expected_duration_ms_from_item,
    import_phrases_from_file,
    next_record_index,
    normalize_word_items,
    phrase_slug,
    recording_attempt_key,
    remember_recording_attempt,
    next_recording_attempt,
    take_label,
    take_number_from_label,
)


class PhraseHelperTests(unittest.TestCase):
    def test_import_txt_phrases_skips_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phrases.txt"
            path.write_text("1357 first long phrase\n# skip me\n1358 second phrase\n", encoding="utf-8")

            phrases = import_phrases_from_file(path)

        self.assertEqual(len(phrases), 2)
        self.assertEqual(phrases[0]["type"], ITEM_TYPE_PHRASE)
        self.assertEqual(phrases[0]["phrase_id"], 1357)
        self.assertEqual(phrases[0]["file_slug"], "phrase_1357")
        self.assertEqual(phrases[1]["phrase_text"], "second phrase")

    def test_import_txt_requires_source_phrase_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phrases.txt"
            path.write_text("first long phrase\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "phrase_id is required"):
                import_phrases_from_file(path)

    def test_import_csv_phrase_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phrases.csv"
            path.write_text(
                "phrase_id,phrase_text,count,expected_duration_ms\n"
                "42,hello phrase,2,12500\n",
                encoding="utf-8",
            )

            phrase = import_phrases_from_file(path)[0]

        self.assertEqual(phrase["phrase_id"], 42)
        self.assertEqual(phrase["count"], 2)
        self.assertEqual(phrase["expected_duration_ms"], 12500)
        self.assertEqual(phrase["expected_duration_sec"], 12)
        self.assertEqual(phrase_slug(phrase), "phrase_0042")

    def test_import_json_phrase_custom_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phrases.json"
            path.write_text(
                json.dumps({"phrases": [{"id": 7, "text": "json phrase", "file_slug": "custom slug"}]}),
                encoding="utf-8",
            )

            phrase = import_phrases_from_file(path)[0]

        self.assertEqual(phrase["phrase_id"], 7)
        self.assertEqual(phrase["file_slug"], "custom_slug")

    def test_import_json_segments_are_expanded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phrases.json"
            path.write_text(
                json.dumps({"phrases": [{"id": 1357, "text": "full phrase", "segments": ["first", "second"]}]}),
                encoding="utf-8",
            )

            phrases = import_phrases_from_file(path)

        self.assertEqual([item["segment_index"] for item in phrases], [1, 2])
        self.assertEqual([item["segment_count"] for item in phrases], [2, 2])
        self.assertEqual([item["phrase_id"] for item in phrases], [1357, 1357])

    def test_word_items_stay_compatible(self) -> None:
        word = normalize_word_items([{"word_id": 5, "uzbek": "Uy"}])[0]

        self.assertEqual(word["type"], "word")
        self.assertEqual(word["word_id"], 5)

    def test_word_count_expands_to_sign_variants(self) -> None:
        words = normalize_word_items([{"word_id": 578, "uzbek": "Haykal", "count": 2}])

        self.assertEqual([word["sign_variant"] for word in words], ["a", "b"])
        self.assertEqual([word["count"] for word in words], [1, 1])

    def test_take_label_round_trip(self) -> None:
        for number in (1, 2, 26, 27, 28):
            self.assertEqual(take_number_from_label(take_label(number)), number)

    def test_daily_counter_resets_once_per_recording_day(self) -> None:
        config = {"recording_day": "20260908", "next_index": 389}

        ensure_recording_day(config, datetime(2026, 9, 8, 10, 0, 0))
        self.assertEqual(config["next_index"], 389)

        ensure_recording_day(config, datetime(2026, 9, 9, 10, 0, 0))
        self.assertEqual(config["recording_day"], "20260909")
        self.assertEqual(config["next_index"], 0)

    def test_attempt_history_keeps_variant_and_attempt_separate(self) -> None:
        attempts: dict[str, int] = {}
        remember_recording_attempt(
            attempts,
            {
                "event": "START",
                "signer": "signer_3",
                "mode": ITEM_TYPE_PHRASE,
                "word_id": 1380,
                "phrase_id": 1380,
                "phrase_text": "Yarim",
                "sign_variant": "a",
                "attempt": 1,
            },
        )

        a_key = recording_attempt_key(
            signer_id="signer_3",
            mode=ITEM_TYPE_PHRASE,
            phrase_id=1380,
            sign_variant="a",
        )
        b_key = recording_attempt_key(
            signer_id="signer_3",
            mode=ITEM_TYPE_PHRASE,
            phrase_id=1380,
            sign_variant="b",
        )

        self.assertEqual(next_recording_attempt(attempts, a_key), 2)
        self.assertEqual(next_recording_attempt(attempts, b_key), 1)

    def test_expected_duration_ms_accepts_seconds_and_milliseconds(self) -> None:
        self.assertEqual(expected_duration_ms_from_item({"expected_duration_sec": 7}), 7000)
        self.assertEqual(expected_duration_ms_from_item({"expected_duration_ms": 7500}), 7500)

    def test_actual_fps_from_existing_phone_payload(self) -> None:
        self.assertEqual(actual_fps_from_payload({"actualFps": 29.92}), 29.92)
        self.assertEqual(
            actual_fps_from_payload(
                {
                    "lastVideoMetadata": {
                        "cameraControls": {"actual_fps": "29.9174"},
                    },
                }
            ),
            29.917,
        )

    def test_next_record_index_never_drops_below_local_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            (log_dir / "recording_log_20260914.ndjson").write_text(
                json.dumps({"event": "START", "record": 404}) + "\n"
                + json.dumps({"event": "START", "record": 12}) + "\n",
                encoding="utf-8",
            )
            original = tcc.recording_log_dir
            tcc.recording_log_dir = lambda: log_dir
            try:
                index = next_record_index(
                    {"next_index": 0, "scan_remote_video_indexes": False},
                    phones=[],
                    timeout=0,
                    day_stamp="20260914",
                )
            finally:
                tcc.recording_log_dir = original

        self.assertEqual(index, 405)

    def test_two_take_item_records_a_then_b_and_retakes_selected_variant(self) -> None:
        app = object.__new__(ControllerApp)
        app.dataset_state = {"manual_back_mode": False, "retake_mode": False}
        app.recording_attempts_by_key = {}
        word = {
            "type": ITEM_TYPE_WORD,
            "word_id": 578,
            "uzbek": "Haykal",
            "count": 2,
        }

        self.assertEqual(app.variant_attempt_for_word(word, "signer_4", 0, 2), ("a", 1, False))
        self.assertEqual(app.variant_attempt_for_word(word, "signer_4", 1, 2), ("b", 1, False))

        remember_recording_attempt(
            app.recording_attempts_by_key,
            {
                "event": "START",
                "signer": "signer_4",
                "mode": ITEM_TYPE_WORD,
                "word_id": 578,
                "word": "Haykal",
                "sign_variant": "a",
                "attempt": 1,
            },
        )
        app.dataset_state = {"manual_back_mode": True, "retake_mode": False}

        self.assertEqual(app.variant_attempt_for_word(word, "signer_4", 1, 2), ("a", 2, True))

        remember_recording_attempt(
            app.recording_attempts_by_key,
            {
                "event": "START",
                "signer": "signer_4",
                "mode": ITEM_TYPE_WORD,
                "word_id": 578,
                "word": "Haykal",
                "sign_variant": "b",
                "attempt": 1,
            },
        )
        app.dataset_state = {
            "manual_back_mode": True,
            "retake_mode": True,
            "retake_sign_variant": "b",
            "retake_attempt": 1,
        }

        self.assertEqual(app.variant_attempt_for_word(word, "signer_4", 2, 2), ("b", 2, True))


if __name__ == "__main__":
    unittest.main()
