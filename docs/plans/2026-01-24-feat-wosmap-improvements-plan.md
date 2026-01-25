---
title: "feat: WOSMap Improvements - Square Preview, Rename, Better Filenames"
type: feat
date: 2026-01-24
---

# WOSMap Improvements

## Overview

Three improvements to the tactile map generator:
1. Change the coverage preview from a circle to a square (matching the actual printed map shape)
2. Rename the application from "Tactile Map Generator" to "WOSMap"
3. Improve output file naming to use city name and date instead of UUIDs

## Problem Statement / Motivation

1. **Circle vs Square**: The current circle preview doesn't accurately represent the final printed map, which is square. This can confuse users about what area will be included.

2. **Naming**: "Tactile Map Generator" is generic. "WOSMap" is more distinctive and memorable.

3. **File naming**: UUID-based filenames like `tactile_map_abc123.stl` are not user-friendly. Users want to know which city/location the file represents when looking at their downloads folder.

## Proposed Solution

### 1. Square Preview Overlay

Replace `L.circle` with `L.rectangle` in MapSelector.vue to show a square coverage area:

```javascript
// Calculate bounds for a square centered on the point
const halfSide = coverageRadius  // same calculation, just used for square
const bounds = [
  [lat - metersToLat(halfSide), lng - metersToLng(halfSide, lat)],
  [lat + metersToLat(halfSide), lng + metersToLng(halfSide, lat)]
]
L.rectangle(bounds, { color: '#4a90d9', ... })
```

### 2. Rename to WOSMap

Update all user-facing text and identifiers:
- Frontend header/title
- Package.json name
- API service name
- Docker container names (optional)

### 3. Smart File Naming

Use reverse geocoding to get location name, combined with date:

**Format**: `wosmap_[city]_[YYYY-MM-DD].stl`

**Examples**:
- `wosmap_paris_2026-01-24.stl`
- `wosmap_san-francisco_2026-01-24.stl`
- `wosmap_tokyo_2026-01-24.stl`

Fallback to coordinates if geocoding fails: `wosmap_48.858_2.294_2026-01-24.stl`

## Technical Approach

### Square Preview (MapSelector.vue)

The challenge with squares on a map is that 1 meter of latitude != 1 meter of longitude (except at equator). Need to convert meters to degrees:

```javascript
// Meters to degrees latitude (constant everywhere)
function metersToLatDegrees(meters) {
  return meters / 111320  // 1 degree lat ≈ 111.32 km
}

// Meters to degrees longitude (varies by latitude)
function metersToLngDegrees(meters, lat) {
  return meters / (111320 * Math.cos(lat * Math.PI / 180))
}
```

### Reverse Geocoding

Nominatim supports reverse geocoding. Add to backend:

```python
async def reverse_geocode(lat: float, lon: float) -> str:
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    # Returns city/town/village name
```

Store location name in job metadata and use for filename.

## Acceptance Criteria

- [x] Map preview shows a SQUARE overlay instead of circle
- [x] Square accurately represents the coverage area matching printed map dimensions
- [x] App header says "WOSMap" instead of "Tactile Map Generator"
- [x] Package.json name updated to "wosmap"
- [x] Downloaded files use format: `wosmap_[city]_[date].stl`
- [x] Fallback filename works when reverse geocoding fails
- [ ] All tests pass

## Implementation Phases

### Phase 1: Square Preview
- Update MapSelector.vue to use L.rectangle
- Add meter-to-degree conversion functions
- Test at various latitudes to ensure accuracy

### Phase 2: Rename to WOSMap
- Update App.vue header and subtitle
- Update package.json name
- Update API title in main.py
- Update any other user-facing text

### Phase 3: Smart File Naming
- Add reverse geocoding function to backend
- Store location name in job metadata during creation
- Update download endpoint to use location-based filename
- Add frontend display of resolved location name (optional enhancement)

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components/MapSelector.vue` | Modify | Change circle to rectangle |
| `frontend/src/App.vue` | Modify | Update title to WOSMap |
| `frontend/package.json` | Modify | Update name field |
| `backend/main.py` | Modify | Update API title, add reverse geocoding |
| `backend/geocoding.py` | Modify | Add reverse_geocode function |

## Dependencies & Risks

**Dependencies:**
- Nominatim reverse geocoding API (same as already used for forward geocoding)

**Risks:**
- Rate limiting on Nominatim: Mitigated by caching location name in job metadata
- Rectangle math accuracy: Need to test at extreme latitudes

## References

- Current MapSelector.vue: Uses L.circle at line 231
- Leaflet L.rectangle docs: https://leafletjs.com/reference.html#rectangle
- Nominatim reverse geocoding: https://nominatim.org/release-docs/develop/api/Reverse/
