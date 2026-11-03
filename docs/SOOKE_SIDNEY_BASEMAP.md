# Sooke–Sidney combined offline basemap — staged scope

**Status:** Proposed development configuration, **not built or published**.

## Required coverage

A continuous Greater Victoria and southern Vancouver Island PMTiles v3 basemap
including Sooke, Metchosin, Langford, Colwood, View Royal, Highlands,
Esquimalt, Victoria, Oak Bay, Saanich, Central Saanich, North Saanich and
Sidney (BC). Jurisdiction boundaries and surrounding coastline require
visual/geospatial quality control; checking a town-centre coordinate alone
is not a claim that every municipal boundary is included.

**Staging bounding box** (longitude/latitude; west,south,east,north):

```text
-124.05,48.26,-123.20,48.76
```

The previous extraction bbox was
`-123.859863,48.274054,-123.263168,48.700478`. This branch expands and
pads the extraction, and applies **identical** new bounds to the BC
Gazetteer official-name conversion. Continue zoom 0–14 initially; compare
file size, missing road labels, edge coverage and map legibility on Samsung
before revising zoom budget.

## Staging procedure (without publishing)

This branch is based on `feature/automated-map-staging`; its draft PR
and Step 7 map pipeline must be reviewed together. CI unit tests cover
bbox consistency and sample city centres. Once a GitHub Actions stage job
can run against this branch, generate a **new combined**
`my_area_with_official_names.pmtiles`, verify v3 header, `pmtiles verify`,
vector layers (`roads`, `water`, `places`, `official_names`), file
size, hash, source-date metadata and geospatial edges.

The current published `my_area.pmtiles` release and
`southern-island.json` manifest are unchanged. Do not overwrite the
existing package or auto-push a map update before user review.

## Gate checks before Samsung deployment

1. Verify land/marine coverage and the *actual jurisdiction boundaries*,
   not just city centres. Check Sooke western edge, Rocky Point/Liberty
   Drive, Humpback Road, Sidney and the north tip of North Saanich.
2. Check that the basemap extraction bounds and the **separately generated**
   Step 6 `road_connectivity.geojson` have compatible display coverage.
   A larger PMTiles archive alone does not extend the classifier overlay.
3. Audit official geographical labels, road names and collision behavior at
   zoom 12–14, retaining correct BC and OSM source attribution.
4. Check the highway colour/style continuity regression and ON/OFF
   behavior of each pilot without allowing restricted/uncertain tracks
   to masquerade as routable roads.
5. Import the staged combined file on the Samsung, preserving installed
   user data and downloaded offline maps; perform airplane-mode validation.
6. Obtain explicit release authorization before merging or replacing the
   public map-release asset or update manifest.

The map is a geographic display, not legal motorized access approval.
