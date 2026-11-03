#!/usr/bin/env python3
"""Audit source-driven official geographical names before combining map tiles.

This is intentionally a validator/report generator. It NEVER modifies, drops,
renames, or inserts a geographical feature. Close names are review flags, not
evidence that one official name is wrong.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import unicodedata

from build_bc_names import PILOT_BBOX

SOURCE = "BC Gazetteer"
LICENCE = "Open Government Licence - British Columbia"
MAX_REPORT_PAIRS = 40
CLOSE_NAME_METRES = 500


def distance_metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Approximate short distances in the Greater Victoria/Sooke region."""
    lat_scale = 111_195.0
    lon_scale = lat_scale * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * lon_scale, (a[1] - b[1]) * lat_scale)


def audit_collection(collection: dict, bbox=PILOT_BBOX) -> dict:
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
        raise ValueError("Expected source-driven GeoJSON FeatureCollection")
    features = collection.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Official-name collection is empty or invalid")

    types = Counter()
    grouped = defaultdict(list)
    exact = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"Feature {index} has invalid structure")
        geometry = feature.get("geometry")
        props = feature.get("properties")
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            raise ValueError(f"Feature {index} is not a point")
        if not isinstance(props, dict):
            raise ValueError(f"Feature {index} is missing properties")

        name = props.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Feature {index} has no official name")
        if unicodedata.normalize("NFC", name) != name:
            raise ValueError(f"Feature {index} name is not normalized to NFC")
        if props.get("source") != SOURCE or props.get("source_licence") != LICENCE:
            raise ValueError(f"Feature {index} has no verified BC source attribution")

        xy = geometry.get("coordinates")
        if not isinstance(xy, list) or len(xy) != 2:
            raise ValueError(f"Feature {index} has invalid point coordinates")
        if any(not isinstance(n, (int, float)) or isinstance(n, bool)
               or not math.isfinite(n) for n in xy):
            raise ValueError(f"Feature {index} has nonfinite point coordinates")
        lon, lat = xy
        if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            raise ValueError(f"Feature {index} falls outside regional map bounds")

        feature_type = str(props.get("feature_type") or "Unknown").strip()
        types[feature_type] += 1
        key = (name.casefold(), round(lon, 6), round(lat, 6))
        if key in exact:
            raise ValueError(f"Duplicate official name/coordinate at index {index}")
        exact.add(key)
        grouped[name.casefold()].append((index, (lon, lat), feature_type))

    potential = []
    total = 0
    for matching in grouped.values():
        if len(matching) < 2:
            continue
        for i in range(len(matching)):
            for j in range(i + 1, len(matching)):
                a, b = matching[i], matching[j]
                metres = distance_metres(a[1], b[1])
                if metres < CLOSE_NAME_METRES:
                    total += 1
                    if len(potential) < MAX_REPORT_PAIRS:
                        potential.append({
                            "feature_indices": [a[0], b[0]],
                            "distance_metres": round(metres, 1),
                            "feature_types": [a[2], b[2]]
                        })

    return {
        "status": "SOURCE_VALIDATED_NO_LABEL_PLACEMENT_CLAIM",
        "feature_count": len(features),
        "unique_names": len(grouped),
        "type_counts": dict(sorted(types.items())),
        "close_same_name_pairs": total,
        "close_same_name_review_samples": potential,
        "bounds": list(bbox),
        "source": SOURCE,
        "licence": LICENCE,
        "limitations": [
            "Nearby identical names may refer to legitimate separate features.",
            "This audit does not compare OSM map tile labels or detect OSM duplicates.",
            "A point coordinate is not guaranteed to be the ideal label anchor.",
            "This audit does not establish motor vehicle or motorcycle access."
        ]
    }


def audit_file(source: Path, destination: Path) -> dict:
    raw = source.read_bytes()
    collection = json.loads(raw.decode("utf-8"))
    report = audit_collection(collection)
    report["geojson_sha256"] = hashlib.sha256(raw).hexdigest()
    report["geojson_bytes"] = len(raw)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="staging/regional_official_names.geojson")
    parser.add_argument("--output", default="staging/regional_official_names.audit.json")
    args = parser.parse_args()
    result = audit_file(Path(args.source), Path(args.output))
    print(json.dumps({
        "status": result["status"],
        "feature_count": result["feature_count"],
        "unique_names": result["unique_names"],
        "close_same_name_pairs": result["close_same_name_pairs"],
        "geojson_sha256": result["geojson_sha256"]
    }, indent=2))


if __name__ == "__main__":
    main()
