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
   - **The Gazetteer is not yet converted into map tiles.** Merely fetching
     names does not make them visible in the Android app.

3. Later: evaluate Natural Resources Canada's Canadian Geographical Names
   Database plus BC road/status information, with licence and update reviews.

## GitHub workflow

Pull requests run network-free unit tests. Only \`workflow_dispatch\`
and a weekly schedule (after workflow is merged into \`main\`) execute
the staging pipeline.

The staging job downloads a pinned PMTiles command-line tool, extracts the
regional basemap, pulls the current Gazetteer CSV, and uploads all files to
a **temporary GitHub Actions artifact** for review. It never pushes a
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
- Convert the **full** regional set of suitable authoritative names (not
  individual patches) into a validated, deduplicated map layer.
- Review priority/conflict handling between OSM names, official BC Gazetteer,
  and Indigenous place names, including correct character handling.
- Decide whether names become an extra PMTiles vector layer or a separate
  versioned offline package; prefer one atomic map update if practical.
- Ensure water polygons, style filters, symbol fonts and collision rules are
  compatible. Check a variety of known features in the pilot area.
- Verify rendering, coverage, offline mode, data licences, source credits, file
  size and download fallback on a physical Android device.
- Only then release a new map asset, allowing the existing release workflow
  to publish an integrity-checked manifest.

**Access note:** Geographic data and road connectivity do not establish
motorcycle access, forestry road permissions, gates or traffic direction.
