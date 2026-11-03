#!/usr/bin/env python3
"""Stage a verified regional Protomaps PMTiles extract; do not publish.

Uses an upstream daily OpenStreetMap-derived planet archive, not a live
tile service or a manually maintained list of local place names.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

# Same Greater Victoria/Sooke pilot bounds and zoom limit used in the current app.
PILOT_BBOX = (-123.859863, 48.274054, -123.263168, 48.700478)
MAX_ZOOM = 14
DEFAULT_USER_AGENT = "MotorcycleNavigator-map-staging/0.1"
REQUIRED_LAYERS = {"roads", "water", "places"}
PMTILES_MAGIC = b"PMTiles\\x03"
MAX_REGIONAL_BYTES = 200 * 1024 * 1024


def source_url(build_date: str) -> str:
    if not re.fullmatch(r"20\\d{6}", build_date):
        raise ValueError("Build date must be YYYYMMDD")
    day = date.fromisoformat(f"{build_date[:4]}-{build_date[4:6]}-{build_date[6:]}")
    if day > datetime.now(timezone.utc).date() + timedelta(days=1):
        raise ValueError("Build date is in the future")
    return f"https://build.protomaps.com/{build_date}.pmtiles"


def available(url: str) -> bool:
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": DEFAULT_USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def select_build(build_date: str, max_age_days: int = 7) -> tuple[str, str]:
    if build_date != "latest":
        return build_date, source_url(build_date)
    today = datetime.now(timezone.utc).date()
    # Protomaps retains daily archives for about one week.
    for ago in range(max_age_days + 1):
        day = (today - timedelta(days=ago)).strftime("%Y%m%d")
        url = source_url(day)
        if available(url):
            return day, url
    raise RuntimeError("No reachable Protomaps daily build in the past week; aborting")


def inspect_metadata(text: str) -> dict:
    try:
        metadata = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("PMTiles metadata is not JSON") from exc
    actual_layers = {
        entry.get("id") for entry in metadata.get("vector_layers", [])
        if isinstance(entry, dict)
    }
    missing = REQUIRED_LAYERS - actual_layers
    if missing:
        raise ValueError("Required map layers missing: " + ", ".join(sorted(missing)))
    return metadata


def run(cli: str, *args: str) -> str:
    result = subprocess.run(
        [cli, *args],
        check=True, capture_output=True, text=True,
    )
    if result.stderr:
        print(result.stderr.strip())
    return result.stdout


def stage(build_date: str, destination: Path, cli: str) -> dict:
    day, upstream = select_build(build_date)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "my_area.pmtiles"
    if output.exists():
        output.unlink()

    bbox = ",".join(str(v) for v in PILOT_BBOX)
    print(f"Staging Greater Victoria/Sooke {upstream} bbox={bbox}")
    run(cli, "extract", upstream, str(output),
        "--bbox=" + bbox, "--maxzoom=" + str(MAX_ZOOM))
    if not output.is_file() or output.stat().st_size < 127:
        raise RuntimeError("Extracted PMTiles file is empty")
    if output.stat().st_size > MAX_REGIONAL_BYTES:
        raise RuntimeError("Regional PMTiles exceeds maximum staging size")
    with output.open("rb") as f:
        if f.read(8) != PMTILES_MAGIC:
            raise RuntimeError("Extracted file is not PMTiles v3")
    run(cli, "verify", str(output))
    inspect_metadata(run(cli, "show", str(output), "--metadata"))

    digest = hashlib.sha256()
    with output.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    info = {
        "source_date": day,
        "source_url": upstream,
        "bbox": list(PILOT_BBOX),
        "maxzoom": MAX_ZOOM,
        "file": output.name,
        "bytes": output.stat().st_size,
        "sha256": digest.hexdigest(),
        "status": "STAGED_NOT_PUBLISHED",
        "build_tool": "protomaps/go-pmtiles v1.31.2"
    }
    (destination / "build-info.json").write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8"
    )
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="latest",
                        help="Protomaps daily YYYYMMDD, or 'latest' (default)")
    parser.add_argument("--output-dir", default="staging")
    parser.add_argument("--pmtiles-cli", default="pmtiles")
    args = parser.parse_args()
    print(json.dumps(stage(args.date, Path(args.output_dir), args.pmtiles_cli), indent=2))


if __name__ == "__main__":
    main()
