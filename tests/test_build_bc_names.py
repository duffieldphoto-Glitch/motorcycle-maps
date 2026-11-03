"""Regression tests for source-driven official geographical name point generation."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "scripts" / "build_bc_names.py"
spec = importlib.util.spec_from_file_location("build_bc_names", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BCNameGenerationTests(unittest.TestCase):
    def test_all_regional_rows_not_one_off_name_fixes(self):
        rows = [
            {"Official Name": "Lake Alpha", "Feature Type": "Lake",
             "Feature Type Code": "LA", "LatDD": "48.43", "LongDD": "-123.54"},
            {"Official Name": "Creek Béta", "Feature Type": "Stream",
             "Feature Type Code": "ST", "LatDD": "48.48", "LongDD": "-123.50"},
            {"Official Name": "Outside", "Feature Type": "Lake",
             "LatDD": "49.2", "LongDD": "-123.5"},
        ]
        collection, counts = mod.convert_rows(rows)
        self.assertEqual(counts["read"], 3)
        self.assertEqual(counts["in_bounds"], 2)
        self.assertEqual([f["properties"]["name"] for f in collection["features"]],
                         ["Lake Alpha", "Creek Béta"])
        self.assertEqual(collection["features"][0]["geometry"]["coordinates"],
                         [-123.54, 48.43])
        self.assertTrue(all("source_licence" in f["properties"]
                            for f in collection["features"]))

    def test_duplicates_malformed_coordinates_and_empty_names(self):
        good = {"Official Name": "Lake Alpha", "Feature Type": "Lake",
                "LatDD": "48.45", "LongDD": "-123.52"}
        rows = [
            good,
            good.copy(),
            {"Official Name": "Bad", "LatDD": "NaN", "LongDD": "-123.52"},
            {"Official Name": "", "LatDD": "48.45", "LongDD": "-123.52"}
        ]
        collection, counts = mod.convert_rows(rows)
        self.assertEqual(len(collection["features"]), 1)
        self.assertEqual(counts["duplicates"], 1)
        self.assertEqual(counts["invalid_coordinates"], 1)
        self.assertEqual(counts["empty_names"], 1)

    def test_cli_conversion_writes_geojson_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bc-gazetteer.csv"
            dest = Path(directory) / "regional_official_names.geojson"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "Official Name", "Feature Type", "Feature Type Code",
                    "LatDD", "LongDD", "Datum"
                ])
                writer.writeheader()
                writer.writerow({
                    "Official Name": "River Delta", "Feature Type": "Stream",
                    "Feature Type Code": "ST", "LatDD": "48.44",
                    "LongDD": "-123.53", "Datum": "NAD83"
                })
            report = mod.convert_file(source, dest)
            self.assertTrue(dest.is_file())
            self.assertEqual(report["counts"]["in_bounds"], 1)
            self.assertEqual(
                json.loads(dest.read_text())["features"][0]["properties"]["source_datum"],
                "NAD83"
            )
            self.assertTrue((Path(directory) / "regional_official_names.report.json").exists())

    def test_missing_required_headers_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "gaz.csv"
            src.write_text("name,lat,long\nFoo,48.4,-123.5\n")
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                mod.convert_file(src, Path(directory) / "out.geojson")

    def test_empty_region_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "gaz.csv"
            src.write_text(
                "Official Name,Feature Type,LatDD,LongDD\n"
                "Far Away,Lake,50,-120\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "No usable"):
                mod.convert_file(src, Path(directory) / "out.geojson")


if __name__ == "__main__":
    unittest.main()
