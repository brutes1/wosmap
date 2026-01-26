---
title: Replace osm_ms with Overture Maps Data Source
type: feat
date: 2026-01-25
---

# Replace osm_ms with Overture Maps Data Source

## Overview

The current "OSM + Microsoft Buildings" option in the UI is unimplemented - it just returns the same OSM data. This plan replaces it with **Overture Maps Foundation** data, which provides genuinely better building coverage by combining OSM, Microsoft, Google, and Esri data sources.

## Problem Statement

- The `osm_ms` data source option advertises "better coverage" but delivers identical results to the default OSM option
- Users selecting this option get no actual benefit
- Microsoft's raw building footprints require complex quadkey tile downloads
- There's no meaningful differentiation between the two options

## Proposed Solution

Replace `osm_ms` with `overture` data source using the Overture Maps Python CLI:

```bash
overturemaps download --bbox=west,south,east,north -f geojson --type=building -o buildings.geojson
```

**Why Overture Maps is better than raw Microsoft Footprints:**

1. **Combined sources**: Overture conflates OSM + Microsoft + Google + Esri data
2. **Quality filtering**: Removes ML artifacts (shipping containers, solar panels)
3. **Simple bbox API**: No need to calculate quadkey tiles
4. **Regular updates**: Monthly releases (latest: 2026-01-21.0)
5. **2.3 billion buildings** globally vs 1.4B Microsoft-only

## Technical Approach

### Files to Modify

1. **`converter/osm_sources.py`** - Add Overture download function
2. **`frontend/src/App.vue`** - Update UI label from "OSM + Microsoft Buildings" to "Overture Maps"
3. **`converter/Dockerfile`** - Install `overturemaps` Python CLI
4. **`backend/main.py`** - Update `data_source` validation (rename `osm_ms` to `overture`)

### Implementation

#### 1. Add Overture download function (`osm_sources.py`)

```python
def fetch_overture_buildings(bbox: tuple, output_dir: str) -> str:
    """
    Fetch building footprints from Overture Maps.

    Args:
        bbox: (lat_min, lon_min, lat_max, lon_max)
        output_dir: Directory to save GeoJSON

    Returns:
        Path to buildings GeoJSON file
    """
    lat_min, lon_min, lat_max, lon_max = bbox
    output_path = os.path.join(output_dir, "overture_buildings.geojson")

    # Overture bbox format: west,south,east,north (lon_min,lat_min,lon_max,lat_max)
    cmd = [
        "overturemaps", "download",
        f"--bbox={lon_min},{lat_min},{lon_max},{lat_max}",
        "-f", "geojson",
        "--type=building",
        "-o", output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise Exception(f"Overture download failed: {result.stderr}")

    return output_path
```

#### 2. Merge Overture buildings into OSM XML

```python
def merge_overture_with_osm(osm_xml: str, overture_geojson_path: str) -> str:
    """
    Merge Overture building footprints into OSM XML data.

    Overture buildings supplement OSM data - we keep OSM buildings
    and add Overture buildings that don't overlap.
    """
    import json
    from xml.etree import ElementTree as ET

    # Parse OSM XML
    root = ET.fromstring(osm_xml)

    # Load Overture GeoJSON
    with open(overture_geojson_path) as f:
        overture = json.load(f)

    # Generate synthetic OSM way IDs (negative to avoid conflicts)
    way_id = -1
    node_id = -1

    for feature in overture.get("features", []):
        if feature["geometry"]["type"] == "Polygon":
            coords = feature["geometry"]["coordinates"][0]

            # Create nodes for the building polygon
            node_refs = []
            for lon, lat in coords:
                node = ET.SubElement(root, "node", {
                    "id": str(node_id),
                    "lat": str(lat),
                    "lon": str(lon),
                    "version": "1"
                })
                node_refs.append(str(node_id))
                node_id -= 1

            # Create way for the building
            way = ET.SubElement(root, "way", {
                "id": str(way_id),
                "version": "1"
            })
            for ref in node_refs:
                ET.SubElement(way, "nd", {"ref": ref})
            ET.SubElement(way, "tag", {"k": "building", "v": "yes"})

            # Add height if available
            height = feature.get("properties", {}).get("height")
            if height:
                ET.SubElement(way, "tag", {"k": "height", "v": str(height)})

            way_id -= 1

    return ET.tostring(root, encoding="unicode")
```

#### 3. Update get_map_data function

```python
def get_map_data(
    lat: float,
    lon: float,
    diameter_meters: int,
    data_source: str = "osm",
    work_dir: str = "/tmp",
    timeout: int = 180
) -> str:
    bbox = calculate_bbox(lat, lon, diameter_meters)

    # Always fetch OSM data as base
    try:
        osm_data = fetch_osm_data(bbox, timeout)
    except Exception as e:
        print(f"Overpass API failed: {e}, trying XAPI...")
        osm_data = fetch_osm_xapi(bbox, timeout)

    # If Overture source requested, merge additional buildings
    if data_source == "overture":
        try:
            overture_path = fetch_overture_buildings(bbox, work_dir)
            osm_data = merge_overture_with_osm(osm_data, overture_path)
        except Exception as e:
            print(f"Overture fetch failed, using OSM only: {e}")

    return osm_data
```

#### 4. Update Frontend UI

```vue
<label>
  <input type="radio" v-model="dataSource" value="osm" :disabled="isProcessing" />
  OpenStreetMap (community-sourced)
</label>
<label>
  <input type="radio" v-model="dataSource" value="overture" :disabled="isProcessing" />
  Overture Maps (OSM + Microsoft + Google + Esri)
</label>
```

#### 5. Update Dockerfile

```dockerfile
RUN pip3 install --no-cache-dir \
    redis \
    requests \
    cairosvg \
    svgwrite \
    overturemaps  # Add this
```

## Acceptance Criteria

- [x] Selecting "Overture Maps" downloads actual Overture building data
- [x] Overture buildings merge with OSM roads/water/etc
- [ ] Download completes within 60 seconds for typical map areas
- [x] Fallback to OSM-only if Overture fails
- [x] Frontend label accurately describes the data source
- [x] Existing `data_source: "osm"` API calls continue to work
- [x] `data_source: "osm_ms"` accepted for backwards compatibility

## Migration

API change: `osm_ms` → `overture`

For backwards compatibility, accept both values in the API but prefer `overture`:

```python
if request.data_source in ("osm_ms", "overture"):
    data_source = "overture"
```

## Dependencies

- `overturemaps` Python package (pip installable)
- Network access to Overture's S3 bucket (no auth required)

## Risks

| Risk | Mitigation |
|------|------------|
| Overture download slower than OSM | Set 5-minute timeout, show progress |
| Overture unavailable | Graceful fallback to OSM-only |
| Building overlaps with OSM | Overture prioritizes OSM, minimal duplicates expected |

## References

- [Overture Maps Documentation](https://docs.overturemaps.org/)
- [Overture Buildings Guide](https://docs.overturemaps.org/guides/buildings/)
- [Overture Python CLI](https://github.com/OvertureMaps/data)
- [Existing TODO](todos/012-pending-p2-unimplemented-osm-ms.md)
- [Current implementation](converter/osm_sources.py:182-183)
