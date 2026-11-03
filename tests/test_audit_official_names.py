"""Source-derived geographical-name audit tests; no network or manual names."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import audit_official_names as audit  # noqa: E402


def feature(name="Example Lake", lon=-123.55, lat=48.45, kind="Lake"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "name": name,
            "feature_type": kind,
            "source": "BC Gazetteer",
            "source_licence": "Open Government Licence - British Columbia"
        }
    }


def collection(*items):
    return {"type": "FeatureCollection", "features": list(items)}


class NamesAuditTests(unittest.TestCase):
    def test_source_driven_region_and_type_summary(self):
        data = collection(
            feature(),
            feature("Creek Two", -123.54, 48.46, "Stream")
        )
        result = audit.audit_collection(data)
        self.assertEqual(result["feature_count"], 2)
        self.assertEqual(result["unique_names"], 2)
        self.assertEqual(result["type_counts"], {"Lake": 1, "Stream": 1})
        self.assertEqual(result["close_same_name_pairs"], 0)
        self.assertEqual(result["status"], "SOURCE_VALIDATED_NO_LABEL_PLACEMENT_CLAIM")

    def test_close_name_pairs_are_flagged_not_removed(self):
        result = audit.audit_collection(collection(
            feature("Twin Lake", -123.55, 48.45),
            feature("Twin Lake", -123.5508, 48.4501),
            feature("Twin Lake", -123.7, 48.5)
        ))
        self.assertEqual(result["feature_count"], 3)
        self.assertEqual(result["unique_names"], 1)
        self.assertEqual(result["close_same_name_pairs"], 1)
        self.assertEqual(result["close_same_name_review_samples"][0]["feature_indices"], [0, 1])

    def test_duplicate_exact_name_location_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate official"):
            audit.audit_collection(collection(feature(), feature()))

    def test_missing_name_or_wrong_source_or_licence_is_rejected(self):
        for prop, value in [
            ("name", ""),
            ("source", "Unverified"),
            ("source_licence", "unknown"),
        ]:
            with self.subTest(prop=prop):
                f = feature()
                f["properties"][prop] = value
                with self.assertRaises(ValueError):
                    audit.audit_collection(collection(f))

    def test_out_of_region_nonfinite_and_unormalized_coordinates(self):
        for xy in [[-123.55, float("nan")], [-122.99, 48.45], [None, 48.45]]:
            with self.subTest(xy=xy):
                f = feature()
                f["geometry"]["coordinates"] = xy
                with self.assertRaises(ValueError):
                    audit.audit_collection(collection(f))
        f = feature("Cafe\u0301 Lake")
        with self.assertRaisesRegex(ValueError, "NFC"):
            audit.audit_collection(collection(f))

    def test_audit_file_writes_sha_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "regional_official_names.geojson"
            out = root / "report.json"
            src.write_text(json.dumps(collection(feature()), ensure_ascii=False))
            result = audit.audit_file(src, out)
            self.assertEqual(len(result["geojson_sha256"]), 64)
            self.assertGreater(result["geojson_bytes"], 0)
            self.assertEqual(json.loads(out.read_text()), result)

    def test_invalid_geometries_fail_closed(self):
        f = feature()
        f["geometry"]["type"] = "LineString"
        with self.assertRaisesRegex(ValueError, "not a point"):
            audit.audit_collection(collection(f))


if __name__ == "__main__":
    unittest.main()
