"""Network-free checks for official BC Gazetteer source discovery."""
import importlib.util
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "scripts" / "fetch_bc_gazetteer.py"
spec = importlib.util.spec_from_file_location("bc_gazetteer", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GazetteerTests(unittest.TestCase):
    def sample(self):
        return {
            "license_title": "Open Government Licence - British Columbia",
            "resources": [{
                "name": "BC_GAZETTEER (CSV)",
                "format": "CSV",
                "id": "resource-1",
                "url": "https://catalogue.data.gov.bc.ca/dataset/a/resource/b/download/names.csv",
            }]
        }

    def test_selects_single_authoritative_csv_resource(self):
        resource, licence = mod.select_csv_resource(self.sample())
        self.assertEqual(resource["id"], "resource-1")
        self.assertEqual(licence, "Open Government Licence - British Columbia")

    def test_rejects_ambiguous_csv_resource(self):
        obj = self.sample()
        obj["resources"].append(obj["resources"][0].copy())
        with self.assertRaisesRegex(ValueError, "Expected one"):
            mod.select_csv_resource(obj)

    def test_rejects_unapproved_or_unknown_licence(self):
        obj = self.sample()
        obj["license_title"] = "Restricted licence"
        with self.assertRaisesRegex(ValueError, "licence"):
            mod.select_csv_resource(obj)

    def test_rejects_external_http_and_malicious_hosts(self):
        self.assertFalse(mod.official_url("http://catalogue.data.gov.bc.ca/file.csv"))
        self.assertFalse(mod.official_url("https://catalogue.data.gov.bc.ca.evil.invalid/file.csv"))
        self.assertFalse(mod.official_url("https://example.com/file.csv"))
        self.assertTrue(mod.official_url("https://catalogue.data.gov.bc.ca/file.csv"))

    def test_utf8_csv_format_and_header(self):
        columns = mod.validate_csv(
            b"\xef\xbb\xbfNAME,LATITUDE,LONGITUDE,FEATURE_CODE\n"
            b"Some Lake,48.5,-123.5,LAKE\n"
        )
        self.assertEqual(columns, ["NAME", "LATITUDE", "LONGITUDE", "FEATURE_CODE"])
        with self.assertRaises(ValueError):
            mod.validate_csv(b"not real csv")


if __name__ == "__main__":
    unittest.main()
