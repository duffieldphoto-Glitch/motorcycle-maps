# MotorcycleNavigator — Offline Maps

This repository distributes **offline map data for the MotorcycleNavigator Android app**.

## Coverage

The first map file (`my_area.pmtiles`) covers **Greater Victoria and nearby Sooke**, not yet the full southern Vancouver Island region. Map tiles are based on Protomaps/OpenStreetMap.

## Publish the next map version

1. Open [Releases](https://github.com/duffieldphoto-Glitch/motorcycle-maps/releases) and choose **Draft a new release**.
2. Create a tag such as `map-2026-11-01` (release title can be `Greater Victoria offline roads — 2026-11-01`).
3. **Attach your regional file named exactly `my_area.pmtiles`**. Do not attach a global/worldwide map.
4. Publish the release.

A GitHub Actions workflow automatically downloads the published asset, checks the PMTiles v3 header, calculates the actual byte count and SHA-256 checksum, and commits **`southern-island.json`** to the `main` branch. You do **not** have to calculate the checksum by hand.

After the workflow succeeds, the Android app should read this stable manifest URL:

`https://raw.githubusercontent.com/duffieldphoto-Glitch/motorcycle-maps/main/southern-island.json`

The manifest has the shape:

```json
{
  "version": "2026-11-01",
  "file_url": "https://github.com/duffieldphoto-Glitch/motorcycle-maps/releases/download/map-2026-11-01/my_area.pmtiles",
  "bytes": 123456,
  "sha256": "<64-character real SHA-256 digest>"
}
```

**This is only a format example.** No `southern-island.json` file is published until the release workflow generates real values from a real map file.

## Requirements and notes

- Repository and release must be **public** for unauthenticated downloads from the app.
- Regional PMTiles archives are for **offline map display**; routing, offline place search, motorized access and forestry overlays require separate datasets and development.
- Do not upload Google API keys, tokens, personal addresses or other private data.
- OpenStreetMap contributors must be credited in the app, and source licensing must be respected.
- GitHub release asset size limits apply; large map downloads may require dedicated hosting.
- If the workflow cannot push a manifest, check repository **Settings → Actions → General → Workflow permissions** and allow read/write permissions if the policy permits.

## Progress

- [x] Android can show a manually imported offline PMTiles map.
- [x] Repository configured for manifest generation on release publish.
- [ ] Upload the regional `my_area.pmtiles` as a GitHub release asset.
- [ ] Confirm workflow creates `southern-island.json`.
- [ ] Configure the Android downloader with the stable manifest URL.
