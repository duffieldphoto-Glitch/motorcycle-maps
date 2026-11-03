#!/usr/bin/env python3
"""Stage the current official BC Gazetteer CSV by discovering it through DataBC.

The full provincial dataset is downloaded and provenance-recorded, but it is
NOT merged into PMTiles and NOT displayed in MotorcycleNavigator at this stage.
No individual water names or coordinates are hard-coded.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request

DATASET_API = (
    "https://catalogue.data.gov.bc.ca/api/3/action/"
    "package_show?id=bc-gazetteer"
)
ALLOWED_HOST = "catalogue.data.gov.bc.ca"
USER_AGENT = "MotorcycleNavigator-offline-map-staging/0.1"
MAX_CSV_BYTES = 30 * 1024 * 1024


def official_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
    )


def select_csv_resource(package: dict) -> tuple[dict, str]:
    if not isinstance(package, dict):
        raise ValueError("Invalid Gazetteer metadata")
    license_title = str(package.get("license_title") or "").strip()
    if (
        "open government licence" not in license_title.lower()
        or "british columbia" not in license_title.lower()
    ):
        raise ValueError("BC Gazetteer licence must be reviewed before reuse")
    resources = package.get("resources") or []
    candidates = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        name = str(resource.get("name") or "").lower()
        fmt = str(resource.get("format") or "").lower()
        url = str(resource.get("url") or "")
        if fmt == "csv" and "gazetteer" in name and official_url(url):
            candidates.append(resource)
    if len(candidates) != 1:
        raise ValueError(
            "Expected one government-hosted Gazetteer CSV, found "
            + str(len(candidates))
        )
    return candidates[0], license_title


def validate_csv(content: bytes) -> list[str]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("BC Gazetteer CSV must be UTF-8") from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader, [])
    sample = next(reader, [])
    if len(header) < 3 or len(sample) < 3:
        raise ValueError("BC Gazetteer CSV has no meaningful header/data")
    return [field.strip() for field in header]


def download_stage(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        DATASET_API, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if not official_url(response.geturl()):
            raise ValueError("Gazetteer metadata redirected to untrusted host")
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("Gazetteer metadata is too large")
    metadata = json.loads(body.decode("utf-8"))
    if metadata.get("success") is not True:
        raise ValueError("BC Data Catalogue did not return a successful response")
    resource, license_title = select_csv_resource(metadata.get("result", {}))
    url = resource["url"]
    csv_request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(csv_request, timeout=120) as response:
        if not official_url(response.geturl()):
            raise ValueError("Gazetteer CSV redirected to untrusted host")
        contents = response.read(MAX_CSV_BYTES + 1)
    if len(contents) > MAX_CSV_BYTES:
        raise ValueError("BC Gazetteer CSV exceeds staging size limit")
    header = validate_csv(contents)
    csv_file = output_dir / "bc-gazetteer.csv"
    csv_file.write_bytes(contents)

    info = {
        "source": "BC Data Catalogue / BC Gazetteer",
        "metadata_url": DATASET_API,
        "resource_id": resource.get("id"),
        "resource_url": url,
        "resource_modified": resource.get("last_modified"),
        "licence": license_title,
        "attribution": "Province of British Columbia",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
        "columns": header,
        "status": "STAGED_NOT_INTEGRATED_NOT_PUBLISHED"
    }
    (output_dir / "bc-gazetteer-info.json").write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8"
    )
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="staging")
    args = parser.parse_args()
    print(json.dumps(download_stage(Path(args.output_dir)), indent=2))


if __name__ == "__main__":
    main()
