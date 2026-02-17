---
title: Fix Trails and Terrain Layers Not Generating
type: fix
date: 2026-01-30
---

# Fix Trails and Terrain Layers Not Generating

## Overview

The trails and terrain layer options in the UI don't produce separate STL layers. Investigation reveals:
- **Trails**: Data is fetched and rendered, but merged into roads layer
- **Terrain**: Not implemented at all - requires external elevation data

## Problem Statement

When users enable "Trails & Footpaths" or "Terrain/Elevation" in the layer settings:
1. No separate STL files are generated for these features
2. Trails appear in the combined STL but can't be printed in a different color
3. Terrain/elevation has no effect whatsoever

## Root Cause Analysis

### Trails Status: Partially Working

| Stage | Status | Details |
|-------|--------|---------|
| UI Toggle | Working | `LayerSettings.vue` has trails option |
| Backend API | Working | `LayerConfig` accepts `trails: bool` |
| OSM Query | Working | Queries `highway=path\|footway\|track\|bridleway\|cycleway` |
| OSM2World | Working | `RoadModule.java` processes paths as pedestrian roads |
| Blender | Working | Renders with `ROAD_HEIGHT_PEDESTRIAN_MM = 1.5` |
| STL Export | **Missing** | No "trails" group in `export_stl_by_feature()` |

**Evidence** - `converter/obj-to-tactile.py:253-260`:
```python
feature_groups = {
    'buildings': ['Buildings'],
    'roads': ['CarRoads', 'PedestrianRoads', 'CarRoadAreas', 'PedestrianRoadAreas'],
    'rails': ['Rails'],
    'water': ['ClippedWaterAreas', 'InnerWaterAreas', 'JoinedWaterways', 'ClippedWaterways'],
    'parks': ['Forests', 'Parks', 'GrassAreas'],
    'base': ['Base', 'Borders', 'CornerInside', 'CornerTop'],
}
# No 'trails' group - trails are included in 'roads' as PedestrianRoads
```

### Terrain Status: Not Implemented

| Stage | Status | Details |
|-------|--------|---------|
| UI Toggle | Working | `LayerSettings.vue` has terrain option (marked beta) |
| Backend API | Working | `LayerConfig` accepts `terrain: bool` |
| Elevation Fetching | **Not Implemented** | No `elevation.py` file exists |
| OSM2World SRTM | Exists but disconnected | Requires `.hgt` files not provided |
| Blender Processing | **Not Implemented** | No terrain mesh handling |
| STL Export | **Not Implemented** | No terrain group |

**Evidence** - Plan described but never implemented:
- `docs/plans/2026-01-30-feat-map-layers-plan.md` describes creating `elevation.py`
- File does not exist in `converter/`
- No elevation-related code in `process_request.py`

## Proposed Solutions

### Option A: Quick Fix - Separate Trails from Roads (Recommended)

**Effort**: Low
**Impact**: Trails get their own color in multi-color prints

1. Modify OSM2World to output trails with distinct object names
2. Update `export_stl_by_feature()` to include trails group
3. Add trails to frontend layer downloads

**Changes Required**:

#### `OSM2World/src/org/osm2world/core/world/modules/RoadModule.java`
- Modify `Road` class to use "Trails" prefix instead of "PedestrianRoads" for path types

#### `converter/obj-to-tactile.py`
```python
feature_groups = {
    # ... existing ...
    'trails': ['Trails', 'Paths', 'Footways'],  # New group
}
```

#### `frontend/src/components/generator/GeneratorResults.vue`
```javascript
layers: [
  // ... existing ...
  { id: 'trails', name: 'Trails', color: '#8B4513' },  // Brown
]
```

### Option B: Full Terrain Implementation (Future)

**Effort**: High
**Impact**: Enables topographic map printing

1. Create `converter/elevation.py` to fetch DEM data
2. Integrate with OpenTopography API or local SRTM tiles
3. Generate terrain mesh in Blender
4. Export as separate layer

**Not recommended for immediate implementation** - requires significant work and external data dependencies.

### Option C: Disable Terrain UI (Interim)

**Effort**: Minimal
**Impact**: Honest UI - don't show options that don't work

1. Hide or disable terrain toggle until implemented
2. Add tooltip explaining it's coming soon

## Acceptance Criteria

### For Option A (Trails Fix):
- [x] Trails appear as separate objects in OBJ output
- [x] `map.trails.stl` file is generated
- [x] Trails download button works in UI
- [x] Trails can be imported separately in Bambu Studio

### For Option C (Terrain Disable):
- [x] Terrain toggle is hidden or disabled
- [x] No false expectations for users

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `OSM2World/.../RoadModule.java` | Modify | Distinguish trails from pedestrian roads |
| `converter/obj-to-tactile.py` | Modify | Add trails to feature_groups |
| `frontend/.../GeneratorResults.vue` | Modify | Add trails to layer downloads |
| `frontend/.../LayerSettings.vue` | Modify | Hide terrain toggle (Option C) |
| `backend/main.py` | No change | Already handles trails in LayerConfig |

## References

### Internal
- Layer settings: `frontend/src/components/settings/LayerSettings.vue`
- Feature export: `converter/obj-to-tactile.py:253-277`
- Road processing: `OSM2World/src/org/osm2world/core/world/modules/RoadModule.java:153-164`
- Original plan: `docs/plans/2026-01-30-feat-map-layers-plan.md`

### OSM Tags for Trails
- `highway=path` - Generic path
- `highway=footway` - Designated footpath
- `highway=track` - Agricultural/forestry track
- `highway=bridleway` - Horse riding path
- `highway=cycleway` - Bicycle path
