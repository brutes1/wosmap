---
title: "Leaflet.js Square Coverage Preview with Latitude-Aware Calculations"
category: feature-implementation
tags:
  - leaflet
  - vue
  - maps
  - geodesy
  - frontend
components:
  - MapSelector.vue
  - frontend
date: 2026-01-24
---

# Leaflet.js Square Coverage Preview with Latitude-Aware Calculations

## Problem

When building an interactive map for selecting a print area, using `L.circle` to show coverage doesn't accurately represent the final output when the printed map is actually square/rectangular. Users see a circle but get a square print, causing confusion about what area will be included.

## Solution

Replace `L.circle` with `L.rectangle` and implement proper meter-to-degree conversion that accounts for latitude variation.

### Key Insight

1 degree of latitude is always ~111.32 km, but 1 degree of longitude varies by latitude:
- At equator: ~111.32 km
- At 45°: ~78.85 km
- At 60°: ~55.66 km

### Implementation

```javascript
// Convert meters to latitude degrees (constant everywhere on Earth)
metersToLatDegrees(meters) {
  return meters / 111320  // 1 degree lat ≈ 111.32 km
}

// Convert meters to longitude degrees (varies by latitude)
metersToLngDegrees(meters, lat) {
  return meters / (111320 * Math.cos(lat * Math.PI / 180))
}

updateRectangle() {
  if (!this.hasMarker || !this.map) return

  // Remove existing rectangle
  if (this.rectangle) {
    this.map.removeLayer(this.rectangle)
  }

  // Calculate bounds for a square centered on the marker
  const halfSide = this.coverageHalfSide  // in meters
  const latOffset = this.metersToLatDegrees(halfSide)
  const lngOffset = this.metersToLngDegrees(halfSide, this.latitude)

  const bounds = [
    [this.latitude - latOffset, this.longitude - lngOffset],  // SW corner
    [this.latitude + latOffset, this.longitude + lngOffset]   // NE corner
  ]

  // Create rectangle showing coverage area
  this.rectangle = L.rectangle(bounds, {
    color: '#4a90d9',
    fillColor: '#4a90d9',
    fillOpacity: 0.15,
    weight: 2,
  }).addTo(this.map)
}
```

### Coverage Calculation

For a tactile map with configurable scale and print size:

```javascript
// Coverage half-side in meters
coverageHalfSide() {
  // sizeCm * scale / 100 converts cm at scale to meters
  // e.g., 23cm at 1:3463 = 23 * 3463 / 100 = 797m diameter
  const sideMeters = (this.sizeCm * this.scale) / 100
  return sideMeters / 2
}
```

## Verification

1. Set a marker at different latitudes (equator, mid-latitudes, high latitudes)
2. The rectangle should appear visually square on the map
3. Changing scale/size should update the rectangle immediately
4. Rectangle bounds should match the actual data extraction area

## Key Files

- `frontend/src/components/MapSelector.vue` - Vue component with Leaflet integration

## Related

- [Leaflet L.rectangle documentation](https://leafletjs.com/reference.html#rectangle)
- Geographic coordinate systems and projections
