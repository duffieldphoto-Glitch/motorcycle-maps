#!/usr/bin/env python3
"""Generate regional offline geographical-name points from ALL current BC Gazetteer rows.

No manually curated per-location corrections. This is a staging dataset for
future vector-tile integration; it is not yet loaded by the Android app.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import unicodedata

# Match the current regional offline PMTiles package.
PILOT_BBOX = (-123.859863, 48.274054, -123.263168, 48.700478)
REQUIRED_HEADERS = {"Official Name", "Feature Type", "LatDD", "LongDD"}


def parse_coordinate(text: str, low: float, high: float) -> float | None:
    try:
        value = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    if not low <= value <= high:
        return None
    return value


def convert_rows(rows, bbox=PILOT_BBOX) -> tuple[dict, dict]:
    """Create feature collection + summary from official Gazetteer CSV rows."""
    features = []
    seen = set()
    counts = {"read": 0, "in_bounds": 0, "duplicates": 0,
              "invalid_coordinates": 0, "empty_names": 0}
    for row in rows:
        counts["read"] += 1
        name = unicodedata.normalize("NFC", (row.get("Official Name") or "").strip())
        if not name:
            counts["empty_names"] += 1
            continue
        lat = parse_coordinate(row.get("LatDD", ""), -90, 90)
        lon = parse_coordinate(row.get("LongDD", ""), -180, 180)
        if lat is None or lon is None:
            counts["invalid_coordinates"] += 1
            continue
        if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            continue
        key = (name.casefold(), round(lon, 6), round(lat, 6))
        if key in seen:
            counts["duplicates"] += 1
            continue
        seen.add(key)
        counts["in_bounds"] += 1
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": name,
                "feature_type": (row.get("Feature Type") or "").strip(),
                "feature_type_code": (row.get("Feature Type Code") or "").strip(),
                "source": "BC Gazetteer",
                "source_licence": "Open Government Licence - British Columbia",
                "source_datum": (row.get("Datum") or "").strip()
            }
        })
    collection = {"type": "FeatureCollection", "features": features}
    return collection, counts


def convert_file(input_path: Path, output_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_HEADERS - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Unexpected BC Gazetteer CSV columns: " + ", ".join(sorted(missing)))
        collection, counts = convert_rows(reader)
    if not collection["features"]:
        raise ValueError("No usable official geographical names within pilot map bounds")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8"
    )
    summary = {
        "input_csv": input_path.name,
        "output_geojson": output_path.name,
        "bbox": list(PILOT_BBOX),
        "counts": counts,
        "status": "STAGED_NOT_INTEGRATED_NOT_PUBLISHED",
        "note": "Full source-driven BC Gazetteer regional name points. Unresolved name conflicts and cartographic placement must be reviewed before rendering."
    }
    summary_path = output_path.with_name("regional_official_names.report.json")
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="staging/bc-gazetteer.csv")
    parser.add_argument("--output", default="staging/regional_official_names.geojson")
    args = parser.parse_args()
    print(json.dumps(convert_file(Path(args.input), Path(args.output)), indent=2))


if __name__ == "__main__":
    main()
