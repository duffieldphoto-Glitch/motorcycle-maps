"""Network-free tests for adding official BC names as a PMTiles vector layer."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import merge_official_names as stage  # noqa: E402


def fake_pmtiles(path: Path):
    path.write_bytes(b"PMTiles\x03" + bytes(256))


def make_names(path):
    path.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-123.55, 48.45]},
            "properties": {
                "name": "Synthetic Reservoir",
                "feature_type": "Lake", "source": "BC Gazetteer"
            }
        }]
    }))


class CombinedMapTests(unittest.TestCase):
    def test_merged_output_preserves_base_and_adds_official_names(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            base, names, outdir = p / "base.pmtiles", p / "names.geojson", p / "out"
            fake_pmtiles(base)
            make_names(names)
            commands = []

            def run(*args):
                commands.append(args)
                if args[0] == "tippecanoe":
                    fake_pmtiles(Path(args[args.index("-o") + 1]))
                if args[0] == "tile-join":
                    fake_pmtiles(Path(args[args.index("-o") + 1]))
                if args[0] == "pmtiles" and args[1] == "show":
                    base_layers = ["roads", "water", "places"]
                    extra = ["official_names"]
                    if "official_names.pmtiles" in args[2]:
                        layer_ids = extra
                    elif "my_area_with_official_names" in args[2]:
                        layer_ids = base_layers + extra
                    else:
                        layer_ids = base_layers
                    return json.dumps({
                        "vector_layers": [{"id": id_} for id_ in layer_ids]
                    })
                return ""

            with patch.object(stage, "run", side_effect=run):
                result = stage.stage_combined(base, names, outdir)
            self.assertEqual(result["status"], "STAGED_NOT_PUBLISHED")
            self.assertEqual(result["official_name_feature_count"], 1)
            self.assertIn("official_names", result["layers"])
            self.assertTrue((outdir / "my_area_with_official_names.pmtiles").exists())
            self.assertEqual(
                json.loads((outdir / "combined-map.report.json").read_text()),
                result
            )
            self.assertEqual([command[0] for command in commands[:2]],
                             ["tippecanoe", "pmtiles"])
            self.assertTrue(any(cmd[0] == "tile-join" for cmd in commands))
            self.assertIn("--no-feature-limit", commands[0])

    def test_rejects_invalid_and_empty_name_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            base, names = p / "base.pmtiles", p / "names.json"
            fake_pmtiles(base)
            names.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
            with self.assertRaisesRegex(ValueError, "named regional"):
                stage.stage_combined(base, names, p)
            names.write_text(json.dumps({"type": "FeatureCollection", "features": [
                {"geometry": {"type": "Point", "coordinates": [-123.5, 48.4]},
                 "properties": {"source": "BC Gazetteer"}}
            ]}))
            with self.assertRaisesRegex(ValueError, "Missing official"):
                stage.stage_combined(base, names, p)

    def test_rejects_corrupt_map_header(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            base, names = p / "base.pmtiles", p / "names.json"
            base.write_bytes(b"bad data" * 40)
            make_names(names)
            with self.assertRaisesRegex(ValueError, "Invalid PMTiles"):
                stage.stage_combined(base, names, p)

    def test_combine_rejects_missing_core_layer(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            base, names = p / "base.pmtiles", p / "names.json"
            fake_pmtiles(base)
            make_names(names)

            def run(*args):
                if args[0] in ("tippecanoe", "tile-join"):
                    fake_pmtiles(Path(args[args.index("-o") + 1]))
                    return ""
                if args[1] == "show":
                    layers = ["official_names"] if "official_names" in args[2] else [
                        "roads", "water", "official_names"
                    ]
                    return json.dumps({"vector_layers": [{"id": n} for n in layers]})
                return ""

            with patch.object(stage, "run", side_effect=run):
                with self.assertRaisesRegex(ValueError, "places"):
                    stage.stage_combined(base, names, p)


if __name__ == "__main__":
    unittest.main()
