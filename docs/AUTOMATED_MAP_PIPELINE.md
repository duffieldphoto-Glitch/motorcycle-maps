# Step 7 — Source-driven offline map staging

**Status:** Development preview only. No automatic releases, map activation,
or Android client changes are included in this pull request.

## Goal

Produce reproducible, checksum-verified map packages from maintained upstream
geographic datasets. Do **not** solve missing names by storing one-off coordinates
or individual label overrides in the Android app.

## Data feeds

1. **Protomaps OpenStreetMap basemap**, daily upstream archive:
   https://maps.protomaps.com/builds/
   - The source archive is selected automatically from the newest reachable
     build in the past seven days, or a specified YYYYMMDD date.
   - A regional extract uses bbox
     \`[-123.859863, 48.274054, -123.263168, 48.700478]\`, zoom 0–14.
   - Map files are for offline display, not proof of legal road access.
   - The staging script verifies the PMTiles v3 header, archive structure,
     expected \`roads\`, \`water\`, and \`places\` layers, maximum size, and SHA-256.
   - The hosted daily build URLs are not a permanent map API. This project
     distributes its own regional copies after verification.

2. **BC Gazetteer**, official geographical names:
   https://catalogue.data.gov.bc.ca/dataset/bc-gazetteer
   - Discover the current CSV URL dynamically with the
     \`/api/3/action/package_show?id=bc-gazetteer\` metadata endpoint.
   - Do not hard-code a dated CSV link or any named-place coordinates.
   - Require a BC government HTTPS host and Open Government Licence –
     British Columbia metadata before staging the CSV.
   - Validate UTF-8 and CSV structure; record the file checksum, version
     metadata, source URL, date, and attribution.
   - The full regional subset (771 official names in the current pilot) is
     converted automatically into vector tile layer \`official_names\`.
     A single staged PMTiles package combines this layer with Protomaps
     roads and water via Tippecanoe tile-join. Rendering still needs Android
     preview verification and does not affect the published map.

3. Later: evaluate Natural Resources Canada's Canadian Geographical Names
   Database plus BC road/status information, with licence and update reviews.

## GitHub workflow

Pull requests run network-free unit tests. Only \`workflow_dispatch\`
and a weekly schedule (after workflow is merged into \`main\`) execute
the staging pipeline.

The staging job downloads a pinned PMTiles command-line tool, extracts the
regional basemap, pulls the current Gazetteer CSV, converts regional official
names to GeoJSON and vector tiles, then builds a single combined PMTiles
archive with Tippecanoe tile-join. It verifies required original and new
vector layers and stores SHA-256 plus source credits. All outputs remain a
**temporary GitHub Actions artifact** for review. It never pushes a
new manifest or creates a public GitHub Release.

The existing published map, its manifest, and phone downloads are untouched.

### Local dry run

Requires Python 3.12+ and the \`pmtiles\` CLI v1.31.2:

\`\`\`sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/stage_regional_map.py --date latest --pmtiles-cli pmtiles
python3 scripts/fetch_bc_gazetteer.py --output-dir staging
\`\`\`

All staged files remain under \`staging/\` (not tracked by Git).

## Next integration gate

Before a new map reaches phones:

- Inspect the current regional PMTiles vector tile for a named reservoir such
  as Humpback Reservoir, distinguishing missing source data from label
  collisions or zoom filters.
- [Completed in staging] Convert the **full** regional set of authoritative
  official name points (not individual patches) into a validated vector layer;
  merge it with the basemap in a single regional PMTiles archive.
- Review priority/conflict handling between OSM names, official BC Gazetteer,
  and Indigenous place names, including correct character handling.
- [Completed in staging] Choose a **single combined PMTiles archive** so
  Android can continue using its atomic and integrity-checked map updater.
- Review the separate Android source-driven label-preview draft PR,
  checking water polygons, style filters, symbols, duplicate labels and
  collision rules across multiple named features, not only one reservoir.
- Verify rendering, coverage, offline mode, data licences, source credits, file
  size and download fallback on a physical Android device.
- Only then release a new map asset, allowing the existing release workflow
  to publish an integrity-checked manifest.

**Access note:** Geographic data and road connectivity do not establish
motorcycle access, forestry road permissions, gates or traffic direction.

## Verified combined-map staging

A fully merged preview PMTiles with 771 official name points and all original
basemap vector layers was created successfully in GitHub Actions:
https://github.com/duffieldphoto-Glitch/motorcycle-maps/actions/runs/41561332132

The enriched archive is 7,862,101 bytes. Its tile metadata credits both
OpenStreetMap contributors and the Province of British Columbia.
Detailed results: [MERGED_MAP_VALIDATION.md](MERGED_MAP_VALIDATION.md).
The preview is **not** published or installed on users' phones.
