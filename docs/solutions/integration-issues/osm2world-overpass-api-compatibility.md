# OSM2World + Overpass API XML Format Compatibility

---
title: OSM2World Requires Specific Overpass API Output Format
category: integration-issues
tags:
  - osm2world
  - overpass-api
  - openstreetmap
  - xml-format
components:
  - converter/osm_sources.py
date_solved: 2026-01-24
severity: blocking
symptoms:
  - "Exception: Way does not have a version attribute as OSM 0.6 are required to have"
  - "Exception: Bound element must come before any entities"
  - "Couldn't find map bounds from OSM2World output"
root_cause: Overpass API query using 'out body' instead of 'out meta', and bounds element inserted at wrong position
---

## Problem Summary

OSM2World failed to parse OpenStreetMap data fetched from the Overpass API, even though the data appeared valid. The XML format returned by Overpass didn't meet OSM2World's strict requirements.

## Symptoms Observed

### Error 1: Missing Version Attribute
```
Exception: Way 5669669 does not have a version attribute as OSM 0.6 are required to have.
```

### Error 2: Bounds Element Position
```
Exception: Bound element must come before any entities.
```

### Error 3: Pipeline Failure
```
Couldn't find map bounds from OSM2World output
```

## Root Causes

### 1. `out body` vs `out meta`

The Overpass API `out body` output format excludes metadata attributes (version, changeset, timestamp, uid, user) that OSM2World requires for OSM 0.6 compliance.

**Body output (missing required attributes):**
```xml
<way id="5669669">
  <nd ref="42421993"/>
  <tag k="building" v="yes"/>
</way>
```

**Meta output (includes required attributes):**
```xml
<way id="5669669" version="15" changeset="12345" timestamp="2024-01-01T00:00:00Z">
  <nd ref="42421993"/>
  <tag k="building" v="yes"/>
</way>
```

### 2. Bounds Element Position

OSM2World's parser expects the `<bounds>` element immediately after the `<osm>` opening tag, before any entity elements (nodes, ways, relations).

**Wrong (bounds at end):**
```xml
<osm version="0.6">
  <way id="123">...</way>
  <bounds minlat="40.7" minlon="-74.0" maxlat="40.8" maxlon="-73.9"/>
</osm>
```

**Correct (bounds after osm tag):**
```xml
<osm version="0.6">
  <bounds minlat="40.7" minlon="-74.0" maxlat="40.8" maxlon="-73.9"/>
  <way id="123">...</way>
</osm>
```

## Solution

### Fix 1: Use `out meta` in Overpass Query

**Before:**
```python
query = f"""
[out:xml][timeout:{timeout}];
(
  way["building"]({lat_min},{lon_min},{lat_max},{lon_max});
  way["highway"]({lat_min},{lon_min},{lat_max},{lon_max});
  ...
);
out body;
>;
out skel qt;
"""
```

**After:**
```python
query = f"""
[out:xml][timeout:{timeout}][bbox:{lat_min},{lon_min},{lat_max},{lon_max}];
(
  way["building"];
  way["highway"];
  way["railway"];
  way["waterway"];
  way["natural"="water"];
  way["landuse"="grass"];
  relation["building"];
  relation["natural"="water"];
);
out meta;
>;
out meta qt;
"""
```

Key changes:
1. Use `out meta` instead of `out body` to include version/changeset attributes
2. Use `out meta qt` instead of `out skel qt` for the recurse-down output
3. Use global `[bbox:...]` in query header for efficiency

### Fix 2: Insert Bounds After Opening Tag

**Before:**
```python
if "<bounds" not in osm_data:
    bounds = f'<bounds minlat="{lat_min}" .../>\n'
    osm_data = osm_data.replace("</osm>", bounds + "</osm>")
```

**After:**
```python
if "<bounds" not in osm_data:
    bounds = f'  <bounds minlat="{lat_min}" minlon="{lon_min}" maxlat="{lat_max}" maxlon="{lon_max}"/>\n'
    import re
    osm_data = re.sub(
        r'(<osm[^>]*>)\s*',
        r'\1\n' + bounds,
        osm_data,
        count=1
    )
```

## Overpass Query Output Modes Reference

| Mode | Includes | Use Case |
|------|----------|----------|
| `out body` | Tags only | Display, analysis |
| `out skel` | IDs and geometry only | Lightweight queries |
| `out meta` | Tags + version/changeset/timestamp | OSM editors, OSM2World |
| `out tags` | Tags only, no geometry | Tag statistics |

## Prevention Strategies

### 1. Validate OSM Output Before Processing
```python
def validate_osm_for_osm2world(osm_data: str) -> bool:
    """Check if OSM data meets OSM2World requirements"""
    import re

    # Check for bounds element in correct position
    if not re.search(r'<osm[^>]*>\s*<bounds', osm_data):
        return False

    # Check for version attribute on first way
    if re.search(r'<way id="[^"]*"(?!.*version=)', osm_data):
        return False

    return True
```

### 2. Test with Known Working Query
```bash
# Test Overpass query directly
curl -d 'data=[out:xml][timeout:30][bbox:40.75,-74.0,40.76,-73.99];way["building"];out meta;>;out meta qt;' \
  https://overpass-api.de/api/interpreter | head -30
```

### 3. Log Raw API Response for Debugging
```python
if response.status_code == 200:
    osm_data = response.text
    # Save raw response for debugging
    with open('/tmp/debug_osm.xml', 'w') as f:
        f.write(osm_data[:5000])  # First 5KB for inspection
```

## Related Resources

- [Overpass API Output Formats](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Output_Format_.28out.29)
- [OSM XML Format Specification](https://wiki.openstreetmap.org/wiki/OSM_XML)
- [OSM2World Requirements](https://github.com/tordanik/OSM2World)

## Verification

```bash
# Check OSM data format in container
docker-compose exec converter head -20 /data/maps/[job-id]/map.osm

# Should see:
# <?xml version="1.0" encoding="UTF-8"?>
# <osm version="0.6" ...>
#   <bounds minlat="..." minlon="..." maxlat="..." maxlon="..."/>
#   <way id="..." version="..." changeset="...">
```
