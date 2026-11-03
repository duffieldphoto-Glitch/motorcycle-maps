# Step 7 — First end-to-end source staging verification

Verified GitHub Actions run:
https://github.com/duffieldphoto-Glitch/motorcycle-maps/actions/runs/41559617342

Date: 2026-11-03 UTC. The staging and unit-test jobs both passed.

## Regional Protomaps package

- Upstream: https://build.protomaps.com/20261102.pmtiles
- Area: Greater Victoria/Sooke bbox [-123.859863, 48.274054, -123.263168, 48.700478].
- Maximum zoom: 14.
- PMTiles v3 file: 7,629,389 bytes.
- SHA-256: b7949f6e52cd879d80269b08408431a5d23b151246eda0519f4c36d2ebceffec.
- Validation: successful CLI extraction, PMTiles verify, required layer metadata, header, size and checksum.

## BC official geographical names

- Metadata obtained automatically from BC Data Catalogue.
- Current resource last modified: 2026-08-12.
- Original Gazetteer CSV: 4,813,588 bytes.
- SHA-256: 52f848c205d6449cc4d5d07eb3c544c11ed30f39d14de42cd548ccbbc32e8ffd.
- Full Gazetteer entries processed: 41,061.
- Located within Greater Victoria/Sooke pilot bounds: **771**.
- Duplicates and invalid coordinates reported by the converter: 0.
- Output: \`regional_official_names.geojson\` and audit report.
- Input format uses official dataset headers \`Official Name\`,
  \`Feature Type\`, \`Feature Type Code\`, \`LatDD\`, \`LongDD\` and
  \`Datum\`. Names retain UTF-8 text and source/licence attribution.

## Scope

**These are staging artifacts, not published map updates.** Existing
\`southern-island.json\` and the Android app have not been changed by Step 7.
The names are not yet rendered. Label collision, OSM/BC name duplication,
official name precedence, Indigenous name policy, source-date freshness,
license credits, and offline device performance still require integration
and review.

After this test the workflow was returned to safe defaults: unit tests on
pull requests; regional builds only via manual dispatch or weekly schedule
once the workflow is approved and merged.
