# Step 7 — Combined offline PMTiles validation

GitHub Actions real network/source run:
https://github.com/duffieldphoto-Glitch/motorcycle-maps/actions/runs/41561332132

**Result:** Success on 2026-11-03 UTC. Both tests and staged-map jobs passed.
This is a disposable artifact for review, **not** a published update.

## Regional combined package

- Base: latest available Protomaps/OSM daily regional extract.
- Official names: generated from the complete current BC Gazetteer CSV, not
  a list of manually entered landmarks or coordinates.
- Pilot bbox: `[-123.859863, 48.274054, -123.263168, 48.700478]`.
- Name point features: **771**.
- Process: `tippecanoe` generates layer `official_names` in vector PMTiles;
  `tile-join` combines *overlapping vector layers* into a single PMTiles v3
  regional package. The `pmtiles merge` operation is not used because it
  is for disjoint spatial archives, not overlaying layers.
- Combined staging file: `my_area_with_official_names.pmtiles`.
- Combined size: **7,862,101 bytes**.
- SHA-256: `8a6b81f493491c4cae6d3408f2ed424fab1d0d24a5121bb71aef8575b771d711`.
- All verified vector layers: `boundaries`, `buildings`, `earth`,
  `landcover`, `landuse`, **`official_names`**, `places`, `pois`,
  `roads`, `water`.
- Attribution in tile metadata: © OpenStreetMap contributors; Protomaps;
  Contains information licensed under the Open Government Licence -
  British Columbia.
- Archived source and generated-name reports remain attached to this
  *temporary* GitHub Actions artifact for reproducibility.

## What has NOT happened

The Android map style does not yet draw `official_names`. The
`southern-island.json` manifest, existing PMTiles release, and Android
map files have not been updated.

Before testing on a phone:

1. Add an **experimental** MapLibre symbol style for the new vector layer
   with collision management, preferably behind a controlled toggle.
2. Audit feature-type categories, OSM duplicate names, priorities,
   Indigenous naming and international characters.
3. Validate source data quality, feature placement, and screenshot examples
   in Greater Victoria. A point is a name location, not necessarily the
   ideal cartographic anchor for an irregular lake or mountain.
4. Compare Humpback Reservoir and other known locations *as regression
   checks*, not hard-coded labels. Distinguish absent OSM properties from
   style label collisions.
5. Repeat offline/airplane-mode and checksum rollback testing on Samsung.
6. Seek creator approval before any release or main-branch merge.

A previous trial using a manually entered Humpback Reservoir GeoJSON
label was explicitly rejected and has been removed from the app branch.
All map names in this package are derived from official source records.
