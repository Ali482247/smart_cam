import json
import tempfile
import unittest
from pathlib import Path

from datetime import datetime

from three_cam_controller import (
    ITEM_TYPE_PHRASE,
    ensure_recording_day,
    import_phrases_from_file,
    normalize_word_items,
    phrase_slug,
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
                "phrase_id,phrase_text,count,expected_duration_sec\n"
                "42,hello phrase,2,12\n",
                encoding="utf-8",
            )

            phrase = import_phrases_from_file(path)[0]

        self.assertEqual(phrase["phrase_id"], 42)
        self.assertEqual(phrase["count"], 2)
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

    def test_daily_counter_resets_once_per_recording_day(self) -> None:
        config = {"recording_day": "20260908", "next_index": 389}

        ensure_recording_day(config, datetime(2026, 9, 8, 10, 0, 0))
        self.assertEqual(config["next_index"], 389)

        ensure_recording_day(config, datetime(2026, 9, 9, 10, 0, 0))
        self.assertEqual(config["recording_day"], "20260909")
        self.assertEqual(config["next_index"], 0)


if __name__ == "__main__":
    unittest.main()
