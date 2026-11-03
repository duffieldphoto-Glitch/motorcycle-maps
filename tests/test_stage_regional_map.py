"""Unit tests for the offline map staging process (no internet required)."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage_regional_map.py"
spec = importlib.util.spec_from_file_location("stage_regional_map", SCRIPT)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageRegionalMapTests(unittest.TestCase):
    def test_source_url_is_protomaps_and_date_is_valid(self):
        self.assertEqual(
            stage.source_url("20261101"),
            "https://build.protomaps.com/20261101.pmtiles",
        )
        for invalid in ["2026-11-01", "../20261101", "20261301", "20260230", "x"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    stage.source_url(invalid)

    def test_future_source_date_is_rejected(self):
        later = (datetime.now(timezone.utc).date() + timedelta(days=4)).strftime("%Y%m%d")
        with self.assertRaises(ValueError):
            stage.source_url(later)

    def test_latest_selects_recent_available_source(self):
        visited = []
        def source_exists(url):
            visited.append(url)
            return len(visited) == 2

        with patch.object(stage, "available", side_effect=source_exists):
            day, url = stage.select_build("latest")
        self.assertEqual(len(visited), 2)
        self.assertEqual(url, stage.source_url(day))

    def test_latest_fails_closed_when_no_source(self):
        with patch.object(stage, "available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "No reachable"):
                stage.select_build("latest")

    def test_metadata_checks_required_layers(self):
        valid = {"vector_layers": [{"id": n} for n in ("roads", "water", "places")]}
        stage.inspect_metadata(json.dumps(valid))
        with self.assertRaisesRegex(ValueError, "places"):
            stage.inspect_metadata('{"vector_layers":[{"id":"roads"},{"id":"water"}]}')
        with self.assertRaises(ValueError):
            stage.inspect_metadata("not JSON")

    def test_stage_creates_verified_artifact_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder) / "staged"
            performed = []
            def fake_run(cli, *args):
                performed.append((cli, args))
                if args[0] == "extract":
                    Path(args[2]).write_bytes(b"PMTiles\x03" + bytes(256))
                    return ""
                if args[0] == "show":
                    return json.dumps({"vector_layers": [
                        {"id": "roads"}, {"id": "water"}, {"id": "places"}
                    ]})
                return ""

            with patch.object(stage, "run", side_effect=fake_run):
                result = stage.stage("20261101", output_dir, "pmtiles")
            self.assertEqual(result["status"], "STAGED_NOT_PUBLISHED")
            self.assertEqual(result["source_date"], "20261101")
            self.assertEqual(result["bbox"], list(stage.PILOT_BBOX))
            self.assertEqual(result["maxzoom"], 14)
            self.assertEqual(len(result["sha256"]), 64)
            self.assertTrue((output_dir / "my_area.pmtiles").exists())
            self.assertEqual(json.loads((output_dir / "build-info.json").read_text()), result)
            self.assertEqual([v[1][0] for v in performed], ["extract", "verify", "show"])
            self.assertIn("--maxzoom=14", performed[0][1])

    def test_stage_rejects_corrupt_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            def fake_run(cli, *args):
                if args[0] == "extract":
                    Path(args[2]).write_bytes(b"NOTPMTL3" + bytes(256))
                return ""
            with patch.object(stage, "run", side_effect=fake_run):
                with self.assertRaisesRegex(RuntimeError, "not PMTiles"):
                    stage.stage("20261101", Path(folder), "pmtiles")


if __name__ == "__main__":
    unittest.main()
