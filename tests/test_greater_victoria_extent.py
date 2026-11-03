"""Ensure the proposed offline map and BC Gazetteer use matching geographic coverage.

The sample locations are test fixtures only, never per-street map-generation
exceptions. All geographic data continues to come from maintained upstream
sources.
"""
import importlib.util
from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name):
    path = SCRIPTS / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegionalExtentTests(unittest.TestCase):
    def test_basemap_and_official_names_share_exact_extent(self):
        base = load_script("stage_regional_map")
        names = load_script("build_bc_names")
        self.assertEqual(base.PILOT_BBOX, names.PILOT_BBOX)

    def test_required_communities_fit_with_buffer(self):
        # Approximate centres verify coverage only, NOT legal jurisdiction
        # boundaries; geographic boundary QA is required before publication.
        west, south, east, north = load_script("stage_regional_map").PILOT_BBOX
        centres = {
            "Sooke": (-123.727, 48.375),
            "Langford": (-123.505, 48.449),
            "Colwood": (-123.488, 48.424),
            "View Royal": (-123.433, 48.451),
            "Saanich": (-123.382, 48.485),
            "Central Saanich": (-123.406, 48.568),
            "Victoria": (-123.366, 48.428),
            "Sidney": (-123.398, 48.650),
            "North Saanich": (-123.459, 48.658),
            "Highlands": (-123.513, 48.521),
            "Metchosin": (-123.547, 48.381),
            "Esquimalt": (-123.413, 48.430),
            "Oak Bay": (-123.310, 48.429),
        }
        for name, (lon, lat) in centres.items():
            with self.subTest(place=name):
                self.assertLess(west + 0.01, lon)
                self.assertLess(lon, east - 0.01)
                self.assertLess(south + 0.01, lat)
                self.assertLess(lat, north - 0.01)

    def test_extent_has_nonzero_area_and_remains_regional(self):
        west, south, east, north = load_script("stage_regional_map").PILOT_BBOX
        self.assertLess(west, east)
        self.assertLess(south, north)
        self.assertLess(east - west, 1.5)
        self.assertLess(north - south, 1.0)


if __name__ == "__main__":
    unittest.main()
