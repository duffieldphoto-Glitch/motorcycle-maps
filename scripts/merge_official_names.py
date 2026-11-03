#!/usr/bin/env python3
"""Build a merged *staged* offline basemap with an official BC names vector layer.

All names come from the current regional Gazetteer conversion. Nothing is
hard-coded for particular landmarks. Do NOT publish without device review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from stage_regional_map import inspect_metadata, MAX_REGIONAL_BYTES, PMTILES_MAGIC

EXTRA_LAYER = "official_names"
NAME_ATTRIBUTION = "Contains information licensed under the Open Government Licence - British Columbia"
COMBINED_ATTRIBUTION = "© OpenStreetMap contributors; Protomaps; " + NAME_ATTRIBUTION
REQUIRED_LAYERS = {"roads", "water", "places", EXTRA_LAYER}
MAX_COMBINED_BYTES = MAX_REGIONAL_BYTES + 10 * 1024 * 1024


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr.strip())
    return result.stdout


def assert_pmtiles(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 127:
        raise ValueError(f"Missing or empty PMTiles archive: {path}")
    with path.open("rb") as stream:
        if stream.read(8) != PMTILES_MAGIC:
            raise ValueError(f"Invalid PMTiles v3 header: {path}")


def metadata_layers(metadata: dict) -> set[str]:
    return {layer.get("id") for layer in metadata.get("vector_layers", [])
            if isinstance(layer, dict)}


def stage_combined(
    base: Path,
    names_geojson: Path,
    output_dir: Path,
    tippecanoe: str = "tippecanoe",
    tile_join: str = "tile-join",
    pmtiles: str = "pmtiles",
) -> dict:
    assert_pmtiles(base)
    with names_geojson.open("r", encoding="utf-8") as stream:
        source = json.load(stream)
    if source.get("type") != "FeatureCollection" or not source.get("features"):
        raise ValueError("Official source GeoJSON must contain named regional points")
    for feature in source["features"]:
        if feature.get("geometry", {}).get("type") != "Point":
            raise ValueError("Only geographical point features allowed")
        props = feature.get("properties", {})
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            raise ValueError("Missing official geographical name")

    output_dir.mkdir(parents=True, exist_ok=True)
    official_tiles = output_dir / "official_names.pmtiles"
    combined = output_dir / "my_area_with_official_names.pmtiles"
    for stale in (official_tiles, combined):
        if stale.exists():
            stale.unlink()

    # Small thematic point layer; one cohesive map archive after tile-join.
    # Start z10 and avoid dropping all source records at high zoom.
    run(
        tippecanoe, "-f", "-Z10", "-z14", "-r1",
        "--no-feature-limit", "--no-tile-size-limit",
        "-l", EXTRA_LAYER, "-A", NAME_ATTRIBUTION,
        "-o", str(official_tiles),
        str(names_geojson)
    )
    assert_pmtiles(official_tiles)
    run(pmtiles, "verify", str(official_tiles))
    extra_meta = json.loads(run(pmtiles, "show", str(official_tiles), "--metadata"))
    if EXTRA_LAYER not in metadata_layers(extra_meta):
        raise ValueError("Generated official_names vector layer missing")

    # Tippecanoe tile-join combines *overlapping vector tile layers*.
    # go-pmtiles 'merge' only joins disjoint tile spatial coverage.
    run(
        tile_join, "-f", "-A", COMBINED_ATTRIBUTION,
        "-o", str(combined),
        str(base), str(official_tiles)
    )
    assert_pmtiles(combined)
    if combined.stat().st_size > MAX_COMBINED_BYTES:
        raise ValueError("Merged regional offline map unexpectedly large")
    run(pmtiles, "verify", str(combined))
    combined_meta = json.loads(run(pmtiles, "show", str(combined), "--metadata"))
    # Verify both original Protomaps data and new authoritative names survived.
    layers = metadata_layers(combined_meta)
    missing = REQUIRED_LAYERS - layers
    if missing:
        raise ValueError("Merged tiles lost map layers: " + ", ".join(sorted(missing)))
    # Also ensures the base archive independently contained its expected layers.
    base_meta = json.loads(run(pmtiles, "show", str(base), "--metadata"))
    inspect_metadata(json.dumps(base_meta))

    digest = hashlib.sha256()
    with combined.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    report = {
        "status": "STAGED_NOT_PUBLISHED",
        "base_file": base.name,
        "names_source_file": names_geojson.name,
        "official_name_feature_count": len(source["features"]),
        "name_layer": EXTRA_LAYER,
        "attribution": COMBINED_ATTRIBUTION,
        "combined_file": combined.name,
        "bytes": combined.stat().st_size,
        "sha256": digest.hexdigest(),
        "layers": sorted(layers),
        "note": "Names are not shown until Android styling and label collision tests pass."
    }
    (output_dir / "combined-map.report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="staging/my_area.pmtiles")
    ap.add_argument("--names", default="staging/regional_official_names.geojson")
    ap.add_argument("--output-dir", default="staging")
    ap.add_argument("--tippecanoe", default="tippecanoe")
    ap.add_argument("--tile-join", default="tile-join")
    ap.add_argument("--pmtiles", default="pmtiles")
    a = ap.parse_args()
    print(json.dumps(stage_combined(
        Path(a.base), Path(a.names), Path(a.output_dir),
        a.tippecanoe, a.tile_join, a.pmtiles
    ), indent=2))


if __name__ == "__main__":
    main()
