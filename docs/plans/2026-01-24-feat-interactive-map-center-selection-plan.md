---
title: "feat: Interactive Map Center Selection with Area Preview"
type: feat
date: 2026-01-24
---

# Interactive Map Center Selection with Area Preview

## Overview

Add an interactive map preview to the frontend that allows users to visually select the center point for their tactile map before generating the STL. The map will display a circle/rectangle showing the exact coverage area based on current scale and size settings.

## Problem Statement / Motivation

Currently, users must either:
1. Enter a text address and hope geocoding centers on the right spot
2. Manually look up GPS coordinates and enter them by hand

Neither approach lets users see what area will be included in their tactile map. This leads to trial-and-error regeneration when the center isn't quite right.

**User story:** As a user, I want to visually select the center of my map and see the coverage area so I can generate the correct map on the first try.

## Proposed Solution

Add a Leaflet.js map component to the frontend that:
1. Shows an interactive OpenStreetMap tile layer
2. Allows clicking/dragging to set the center point
3. Displays a circle overlay showing the coverage area based on scale/size settings
4. Updates the circle dynamically as scale/size inputs change

### UI Flow

```
┌─────────────────────────────────────────────────┐
│  Location                                       │
├─────────────────────────────────────────────────┤
│  [Search address: ___________________] [Search] │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │
│  │         ┌───────────────┐               │   │
│  │         │               │               │   │
│  │         │    (circle)   │ ← Coverage    │   │
│  │         │      ⊕        │   area        │   │
│  │         │               │               │   │
│  │         └───────────────┘               │   │
│  │                                         │   │
│  │  Click to set center or drag marker     │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Center: 48.8584, 2.2945  [Reset]              │
└─────────────────────────────────────────────────┘
```

## Technical Approach

### Dependencies

Add to `frontend/package.json`:
```json
{
  "dependencies": {
    "leaflet": "^1.9.4",
    "vue": "^3.4.0"
  }
}
```

### Component Structure

Create a new `MapSelector.vue` component:

```
frontend/src/
├── App.vue              # Import MapSelector
├── components/
│   └── MapSelector.vue  # New interactive map component
└── main.js
```

### MapSelector.vue Responsibilities

1. **Initialize Leaflet map** with OpenStreetMap tiles
2. **Handle click events** to set center marker
3. **Draw circle overlay** calculated from:
   - `diameter = sizeCm * scale / 100` (converts cm at scale to meters)
4. **Emit center updates** to parent via `v-model` or events
5. **Geocode search** - optional address search that pans map to location

### Integration with App.vue

```vue
<MapSelector
  v-model:latitude="latitude"
  v-model:longitude="longitude"
  :scale="scale"
  :size-cm="sizeCm"
  :disabled="isProcessing"
/>
```

### Circle Radius Calculation

The coverage area diameter in meters:
```javascript
// sizeCm is the print size (e.g., 23cm)
// scale is the map scale (e.g., 3463 means 1:3463)
// At 1:3463 scale, 23cm print = 23 * 3463 / 100 = 797m diameter
const diameterMeters = (sizeCm * scale) / 100;
const radiusMeters = diameterMeters / 2;
```

This matches the backend calculation in `converter/osm_sources.py:calculate_bbox()`.

## Acceptance Criteria

- [x] Map displays on page load, centered on a default location (or user's geolocation if permitted)
- [x] Clicking on map sets the center point and places a marker
- [x] Circle overlay shows coverage area matching scale/size settings
- [x] Circle updates immediately when scale or size inputs change
- [x] Address search geocodes and pans map to result
- [x] Latitude/longitude values update and can be sent to backend
- [x] Map is disabled during processing (non-interactive)
- [x] Works on mobile (touch events)

## Implementation Phases

### Phase 1: Basic Map with Marker
- Add Leaflet dependency
- Create MapSelector component with tile layer
- Click-to-place marker functionality
- Two-way binding for lat/lon

### Phase 2: Coverage Circle
- Calculate diameter from scale/size
- Draw Leaflet circle on marker position
- Update circle when settings change

### Phase 3: Address Search
- Add search input above map
- Use Nominatim geocoding (already used by backend)
- Pan map and set marker on search result

### Phase 4: Polish
- Default to geolocation if permitted
- Add "Reset" button to clear marker
- Styling to match existing UI
- Mobile responsiveness

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `frontend/package.json` | Modify | Add leaflet dependency |
| `frontend/src/components/MapSelector.vue` | Create | New map component |
| `frontend/src/App.vue` | Modify | Replace location input with MapSelector |
| `frontend/src/style.css` | Modify | Add Leaflet CSS import, map container styles |

## Dependencies & Risks

**Dependencies:**
- Leaflet.js (well-maintained, no other dependencies)
- OpenStreetMap tile server (public, free, no API key needed)

**Risks:**
- **Tile server rate limits**: OSM has usage policy, but for local use this is fine
- **Bundle size**: Leaflet adds ~40KB gzipped, acceptable for this use case
- **Offline use**: Tiles require internet; could add tile caching later if needed

## Success Metrics

- Users can select map center visually in < 10 seconds
- Reduced regeneration rate (fewer "wrong center" retries)
- Circle accurately represents final STL coverage area

## References

- [Leaflet.js Documentation](https://leafletjs.com/reference.html)
- [Nominatim Search API](https://nominatim.org/release-docs/develop/api/Search/)
- Existing geocoding: `backend/geocoding.py`
- Existing bbox calculation: `converter/osm_sources.py:123` (`calculate_bbox()`)
