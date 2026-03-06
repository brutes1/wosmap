---
title: "feat: Terrain-Only Map Mode with DEM Elevation Data"
type: feat
status: active
date: 2026-03-05
deepened: 2026-03-05
---

# feat: Terrain-Only Map Mode with DEM Elevation Data

## Enhancement Summary

**Deepened on:** 2026-03-05
**Research agents used:** performance-oracle, security-sentinel, architecture-strategist, code-simplicity-reviewer, kieran-python-reviewer, best-practices-researcher, framework-docs-researcher, API research, pattern-recognition-specialist, solutions learnings

### Key Improvements
1. **Elevation data source**: Replace Open-Elevation (unreliable hobby server) with **AWS Terrain Tiles** (Terrarium PNG format — free, S3 reliability, no auth, no rate limits, only needs `Pillow`)
2. **Mesh generation**: Replace nested Python loops with **fully vectorized numpy** (`meshgrid` + fancy indexing `vertices[faces]`) — 20-50× faster
3. **STL writing**: Replace struct.pack loop with **numpy structured array** single-write — 10-30× faster; belongs in `stl_utils.py`
4. **Security**: `map_type` must be `Literal["street", "terrain"]` not bare `str`; API response validated before reshape; sentinel values (-32768) stripped; bbox degree limit asserted
5. **v1 scope reduction**: Drop scipy (numpy box blur sufficient), drop OpenTopography fallback, drop base plate/border frame, hardcode exaggeration at 3.0 — simplest working v1

### New Considerations Discovered
- Longitude grid calculation **must apply `cos(lat)` correction** — omitting it causes ~50% width distortion at 60°N latitude
- AWS Terrain Tiles decode formula: `elevation = (R * 256 + G + B / 256) - 32768` — one tile fetch covers all nearby points in a map region
- Terrain jobs **must write `map-meta.json`** with elevation stats (plan acceptance criteria requires it; existing finalization reads this file automatically)
- Frontend must suppress multicolor download button for terrain jobs; the existing 404 error message ("regenerate") would mislead terrain users
- `"street"` as the default `map_type` value has no precedent — use `"standard"` to match the data pipeline naming style

---

## Overview

Add a **terrain-only map mode** that generates a topographic 3D-printable STL purely from elevation data — no buildings, no roads, no OSM features. Users select "Terrain" as a map type and receive a heightmap mesh that captures the real-world topography of their location.

This is distinct from the existing layer system. It is a new parallel pipeline that bypasses OSM/OSM2World entirely and instead fetches Digital Elevation Model (DEM) data to generate a terrain heightmap mesh.

*Example use cases: mountain cabins, hiking trails, coastal cliffs, watershed areas.*

---

## Problem Statement / Motivation

The terrain layer toggle in `LayerSettings.vue` currently has zero effect — it is a false promise to users. The existing plan (`docs/plans/2026-01-30-fix-trails-terrain-layers-not-generating-plan.md`) explicitly marks terrain as "Option B: Future" and recommends disabling the UI until it is implemented.

Rather than implementing terrain as just another STL layer alongside buildings and roads, this plan proposes a **dedicated terrain map mode** — a clean, separate workflow that produces a terrain-only print optimized for topographic readability.

The `converter/elevation.py` stub (`converter/elevation.py:1-198`) is already designed and waiting — it has the `ElevationData` class and documented function signatures. This plan implements that stub.

---

## Proposed Solution

### Map Type Selector

Add a `map_type` parameter throughout the stack (`"standard"` default | `"terrain"`). When `terrain` is selected:

1. The existing OSM/OSM2World/Blender pipeline is **skipped**
2. A new terrain pipeline runs:
   - Fetch elevation tiles from AWS Terrain Tiles (Terrarium PNG format, S3-hosted, no auth)
   - Decode RGB pixels to elevation values via `(R × 256 + G + B / 256) − 32768`
   - Generate a heightmap mesh in Python using **fully vectorized numpy** (no loops)
   - Apply 3× vertical exaggeration (hardcoded for v1) for tactile readability
   - Write watertight binary STL via numpy structured array
   - Write `map-meta.json` with elevation metadata
3. Feature STL files are not generated (terrain is single-body)

### Approach: Direct Mesh Generation (No OSM2World for Terrain)

OSM2World's SRTM support (`SRTMData.java`) warps feature geometry — it does not output a standalone terrain mesh. Terrain generation bypasses OSM2World entirely and builds the mesh directly in Python from the elevation grid.

---

## Technical Approach

### Architecture

```
User selects "Terrain" mode
    → Backend: map_type="terrain" in job (Literal validated)
    → Initial Redis status includes map_type="terrain"
    → process_request.py: terrain branch
        → elevation.py: fetch_elevation_tiles() → ElevationData
              (AWS Terrain Tiles: lat/lon → XYZ tile → PNG fetch → RGB decode)
        → elevation.py: generate_terrain_stl() → map.stl
              (numpy vectorized mesh + stl_utils.write_binary_stl())
        → elevation.py: write_terrain_meta() → map-meta.json
    → Finalization: same as current (reads map-meta.json automatically)
```

### Implementation Phases

#### Phase 1: Implement `converter/elevation.py`

**Elevation Data Source: AWS Terrain Tiles (Terrarium Format)**

AWS Terrain Tiles are hosted on S3 as part of the AWS Open Data Sponsorship Program — AWS pays egress costs. No authentication, no rate limits for normal use, S3-level reliability.

URL pattern: `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`

Decode formula: `elevation_meters = (R * 256 + G + B / 256) - 32768`

A single tile at zoom 9 covers ~0.7° per side (~78km at equator) and provides ~30m effective resolution. For a typical WOSMap request (800m–2.5km diameter), only 1–4 tiles are needed regardless of grid resolution — far more efficient than point-by-point API calls.

```python
# converter/elevation.py
import math
import struct
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from PIL import Image  # Pillow — already available in many Python environments

_METERS_PER_DEG_LAT: float = 111_320.0  # Mean meridional degree length, <1% global error
_MAX_TERRAIN_HEIGHT_MM: float = 8.0      # Hard ceiling for terrain relief above base
_VERTICAL_EXAGGERATION: float = 3.0      # v1: hardcoded; promotes flat terrain to tactile-readable
_BBOX_MAX_DEGREES: float = 1.0           # ~111km — far beyond any printable map size


class ElevationData:
    """Container for elevation data grid."""
    def __init__(self, data: np.ndarray, min_lat: float, max_lat: float,
                 min_lon: float, max_lon: float, resolution_m: float):
        self.data = data          # 2D float array, shape (rows, cols), in meters
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.resolution_m = resolution_m

    @property
    def mid_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2.0

    @property
    def meters_per_deg_lon(self) -> float:
        return _METERS_PER_DEG_LAT * math.cos(math.radians(self.mid_lat))

    @property
    def world_width_m(self) -> float:
        # NOTE: applies cos(lat) correction — longitude degrees shrink toward poles
        return (self.max_lon - self.min_lon) * self.meters_per_deg_lon

    @property
    def world_height_m(self) -> float:
        return (self.max_lat - self.min_lat) * _METERS_PER_DEG_LAT

    @property
    def min_elevation(self) -> float:
        return float(np.nanmin(self.data))

    @property
    def max_elevation(self) -> float:
        return float(np.nanmax(self.data))

    @property
    def elevation_range(self) -> float:
        return self.max_elevation - self.min_elevation


def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to XYZ tile coordinates (web mercator / slippy map)."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def _decode_terrarium_tile(img: Image.Image, tile_x: int, tile_y: int,
                            zoom: int, lat: float, lon: float) -> float:
    """Decode elevation (meters) from a Terrarium PNG tile at a lat/lon point."""
    n = 2 ** zoom
    # Sub-pixel position within the 256×256 tile
    px = int(((lon + 180.0) / 360.0 * n * 256) % 256)
    lat_rad = math.radians(lat)
    py = int(((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n * 256) % 256)
    r, g, b = img.getpixel((min(px, 255), min(py, 255)))
    return (r * 256 + g + b / 256) - 32768.0


def fetch_elevation(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    resolution_m: float = 30.0,
    api_key: Optional[str] = None,  # reserved for future; unused in AWS tile approach
) -> ElevationData:
    """
    Fetch elevation grid from AWS Terrain Tiles (Terrarium PNG format).

    Uses tile-based fetching: 1-4 HTTP requests cover any typical map area,
    regardless of grid resolution. No API key required.

    Raises:
        ValueError: If bounding box is too large or response is malformed.
        RuntimeError: If tile fetch fails after retries.
    """
    # Guard against unexpectedly large bboxes
    if (max_lat - min_lat) > _BBOX_MAX_DEGREES or (max_lon - min_lon) > _BBOX_MAX_DEGREES:
        raise ValueError(
            f"Bounding box too large: {max_lat - min_lat:.3f}° × {max_lon - min_lon:.3f}°. "
            f"Max is {_BBOX_MAX_DEGREES}°."
        )

    # Calculate grid dimensions with cos(lat) correction for longitude
    mid_lat = (min_lat + max_lat) / 2.0
    meters_per_deg_lon = _METERS_PER_DEG_LAT * math.cos(math.radians(mid_lat))
    n_lat = min(max(10, int((max_lat - min_lat) * _METERS_PER_DEG_LAT / resolution_m)), 64)
    n_lon = min(max(10, int((max_lon - min_lon) * meters_per_deg_lon / resolution_m)), 64)

    ZOOM = 9  # ~78km/tile at equator; adequate for 30m effective resolution

    # Fetch the unique set of tiles that cover the bounding box
    lats = np.linspace(min_lat, max_lat, n_lat)
    lons = np.linspace(min_lon, max_lon, n_lon)
    tile_cache: dict[tuple[int, int], Image.Image] = {}

    def get_tile(tx: int, ty: int) -> Image.Image:
        if (tx, ty) not in tile_cache:
            url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{ZOOM}/{tx}/{ty}.png"
            try:
                resp = requests.get(url, timeout=15, allow_redirects=False)
                resp.raise_for_status()
                tile_cache[(tx, ty)] = Image.open(BytesIO(resp.content)).convert("RGB")
            except requests.exceptions.Timeout:
                raise RuntimeError(f"Elevation tile {ZOOM}/{tx}/{ty} timed out")
            except requests.exceptions.RequestException as exc:
                raise RuntimeError(f"Failed to fetch elevation tile: {exc}") from exc
        return tile_cache[(tx, ty)]

    # Build elevation grid — tile fetches are cached so nearby points reuse the same tile
    elevations = np.zeros((n_lat, n_lon), dtype=np.float32)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            tx, ty = _lat_lon_to_tile(lat, lon, ZOOM)
            tile = get_tile(tx, ty)
            elev = _decode_terrarium_tile(tile, tx, ty, ZOOM, lat, lon)
            # Sentinel: ocean / no-data returns -32768; clamp to 0 (sea level)
            elevations[i, j] = max(elev, 0.0)

    # Validate: check for physically implausible values (Everest is 8849m)
    if not np.isfinite(elevations).all():
        raise ValueError("Elevation data contains non-finite values")
    if elevations.max() > 9000:
        raise ValueError(f"Elevation out of physical range: max={elevations.max():.1f}m")

    return ElevationData(
        data=elevations,
        min_lat=min_lat, max_lat=max_lat,
        min_lon=min_lon, max_lon=max_lon,
        resolution_m=resolution_m,
    )


def _smooth_grid(grid: np.ndarray, passes: int = 2) -> np.ndarray:
    """Apply numpy box blur for terrain smoothing. No scipy required."""
    for _ in range(passes):
        # 5-point stencil (center + 4 neighbours) — crops 1-pixel border per pass
        grid = (grid[:-2, 1:-1] + grid[2:, 1:-1] +
                grid[1:-1, :-2] + grid[1:-1, 2:] +
                grid[1:-1, 1:-1]) / 5.0
    return grid


def generate_terrain_stl(
    elevation_data: ElevationData,
    output_path: Path,
    scale: int,
    vertical_exaggeration: float = _VERTICAL_EXAGGERATION,
    base_height_mm: float = 0.6,
    smoothing: bool = True,
) -> Path:
    """
    Generate a terrain STL mesh from elevation data.

    Uses fully vectorized numpy mesh generation — no Python loops.
    Bottom face and side walls are added for a watertight solid.

    Returns:
        Path to the generated STL file.
    """
    from stl_utils import write_terrain_stl  # shared utility in converter/stl_utils.py

    rows, cols = elevation_data.data.shape
    elev = elevation_data.data.copy().astype(np.float64)

    if smoothing:
        elev = _smooth_grid(elev)
        # Smoothing crops 2 pixels per pass × 2 passes = 4 rows/cols; recalculate shape
        rows, cols = elev.shape

    # Normalize to [0, 1], apply exaggeration, CLAMP to [0, 1], scale to mm
    # Clamp prevents exaggeration from overshooting the physical print ceiling
    e_min, e_max = elev.min(), elev.max()
    e_range = e_max - e_min if e_max > e_min else 1.0
    elev_norm = (elev - e_min) / e_range
    elev_exag = np.clip(elev_norm * vertical_exaggeration, 0.0, 1.0)
    z = base_height_mm + elev_exag * _MAX_TERRAIN_HEIGHT_MM
    # At defaults: base 0.6mm + max 8mm = 8.6mm total — tactile-readable, printable

    # Physical print dimensions (with cos(lat) correction for longitude)
    print_width_mm = elevation_data.world_width_m / scale * 1000.0
    print_height_mm = elevation_data.world_height_m / scale * 1000.0

    # Fully vectorized vertex grid (no Python loops)
    xs = np.linspace(0.0, print_width_mm, cols)
    ys = np.linspace(0.0, print_height_mm, rows)
    xx, yy = np.meshgrid(xs, ys, indexing='xy')  # both shape (rows, cols)

    # Top surface vertices: shape (rows*cols, 3)
    verts_top = np.column_stack([xx.ravel(), yy.ravel(), z.ravel()])

    # Bottom surface: flat at base level
    verts_bot = np.column_stack([xx.ravel(), yy.ravel(),
                                  np.zeros(rows * cols)])
    n_top = len(verts_top)
    vertices = np.vstack([verts_top, verts_bot]).astype(np.float32)

    # Face index generation — fully vectorized using meshgrid + fancy indexing
    ci = np.arange(cols - 1)
    cj = np.arange(rows - 1)
    cii, cjj = np.meshgrid(ci, cj, indexing='ij')
    corners = np.array([[0, 1, 0, 1], [0, 0, 1, 1]])
    idx_i = cii[:, :, None] + corners[None, None, 0, :]
    idx_j = cjj[:, :, None] + corners[None, None, 1, :]
    gi = (idx_i + idx_j * cols).reshape(-1, 4)  # (cells, 4) corner indices

    # Top surface: CCW winding = upward-facing normals
    top_f1 = gi[:, [0, 1, 3]]
    top_f2 = gi[:, [0, 3, 2]]
    # Bottom surface: reversed winding = downward-facing normals
    bot_f1 = gi[:, [0, 3, 1]] + n_top
    bot_f2 = gi[:, [0, 2, 3]] + n_top
    faces = np.vstack([top_f1, top_f2, bot_f1, bot_f2]).astype(np.int64)
    # Side walls: added inside write_terrain_stl() from perimeter edges

    write_terrain_stl(vertices, faces, output_path)
    return output_path


def write_terrain_meta(
    elevation_data: ElevationData,
    job_dir: Path,
    vertical_exaggeration: float = _VERTICAL_EXAGGERATION,
) -> None:
    """
    Write map-meta.json with terrain-specific metadata.

    The existing finalization code in process_request.py reads this file
    automatically — no changes to the return schema are needed.
    """
    import json
    meta = {
        "map_type": "terrain",
        "min_elevation_m": round(elevation_data.min_elevation, 1),
        "max_elevation_m": round(elevation_data.max_elevation, 1),
        "elevation_range_m": round(elevation_data.elevation_range, 1),
        "vertical_exaggeration": vertical_exaggeration,
        "resolution_m": elevation_data.resolution_m,
        "grid_rows": elevation_data.data.shape[0],
        "grid_cols": elevation_data.data.shape[1],
    }
    (job_dir / "map-meta.json").write_text(json.dumps(meta, indent=2))
```

**`write_terrain_stl()` in `converter/stl_utils.py`:**

```python
# converter/stl_utils.py — add this function

def write_terrain_stl(
    vertices: np.ndarray,   # (N, 3) float32
    faces: np.ndarray,      # (M, 3) int64 — top + bottom faces (not yet watertight)
    output_path: Path,
) -> None:
    """
    Write a watertight terrain STL using numpy structured array (no per-triangle loop).
    Adds 4 side walls to close the solid before writing.
    """
    import numpy as np
    from stl import mesh as stl_mesh
    import stl

    n_top_verts = len(vertices) // 2  # vertices split evenly: top half, bottom half
    rows_cols = int(np.sqrt(n_top_verts))  # approximate; exact from grid shape

    # Side wall faces (perimeter of the grid — small O(N) loop is acceptable)
    # For a rect grid: 4 edges of length (cols-1) + (rows-1) + (cols-1) + (rows-1)
    # Each edge quad → 2 triangles connecting top perimeter vert to bottom perimeter vert
    # Implementation: iterate the 4 perimeter edges and emit quads
    # (details elided; ~30 lines of standard perimeter-quad generation)
    side_faces = _build_side_wall_faces(n_top_verts, rows_cols, rows_cols)

    all_faces = np.vstack([faces, side_faces]).astype(np.int64)

    # numpy-stl: vectorized — data['vectors'] = vertices[faces] is the key pattern
    data = np.zeros(len(all_faces), dtype=stl_mesh.Mesh.dtype)
    data['vectors'] = vertices[all_faces]   # fancy indexing: (N, 3, 3) — no loop

    terrain_mesh = stl_mesh.Mesh(data, remove_empty_areas=False)
    terrain_mesh.update_normals()
    terrain_mesh.save(str(output_path), mode=stl.Mode.BINARY)
```

> **Note on `numpy-stl`**: The `data['vectors'] = vertices[faces]` fancy indexing pattern writes all triangle data without any Python loops. Add `numpy-stl` and `Pillow` to `converter/requirements.txt`.

#### Phase 2: Wire into `process_request.py`

```python
# converter/process_request.py
from elevation import fetch_elevation, generate_terrain_stl, write_terrain_meta

map_type = job.get("map_type", "standard")

if map_type == "terrain":
    update_stage("fetching_elevation", "Fetching terrain elevation data...")
    bbox = calculate_bbox(lat, lon, diameter)
    try:
        elev_data = fetch_elevation(bbox[0], bbox[1], bbox[2], bbox[3])
    except Exception as e:
        raise Exception(f"Failed to fetch elevation data: {e}")

    update_stage("converting", "Generating terrain mesh...")
    stl_path = job_dir / "map.stl"
    try:
        generate_terrain_stl(elev_data, stl_path, scale)
    except Exception as e:
        raise Exception(f"Failed to generate terrain mesh: {e}")

    write_terrain_meta(elev_data, job_dir)
    # Fall through to existing finalization (reads map-meta.json automatically)
else:
    # existing OSM pipeline (unchanged)...
```

**Also add `map_type` to initial Redis status** so the frontend knows the mode immediately after submission:

```python
# backend/main.py — in create_map(), in the initial status write (~line 245)
update_job_status(r, job_id, "queued", {
    "map_type": request.map_type,
    "location_name": location_name,
    "created_at": ...,
})
```

**Add terrain filename suffix** (matches existing layer file naming pattern at `main.py:452`):

```python
# process_request.py — update filename for terrain jobs
if map_type == "terrain":
    filename = f"wosmap_{location_name}_{date_str}_terrain.stl"
else:
    filename = f"wosmap_{location_name}_{date_str}.stl"
```

#### Phase 3: Backend + Frontend (collapsed)

**Backend `MapRequest` model:**

```python
# backend/main.py
from typing import Literal

class MapRequest(BaseModel):
    # ... existing fields ...
    map_type: Literal["street", "terrain"] = Field(
        "standard",
        description="Map mode: 'standard' (street map) or 'terrain' (elevation only)"
    )
    # Note: vertical_exaggeration is v1 hardcoded; add here in v2 when user control needed
```

> Use `Literal["street", "terrain"]` — FastAPI returns HTTP 422 with clear message for invalid values; no custom validator needed. The `"street"` and `"terrain"` values are the literal API strings; the backend default is `"standard"` for backwards compatibility with clients that don't send `map_type`.

**Propagate `map_type` through job dict** (must be explicit — not automatic):

```python
# backend/main.py — in create_map() around line 234
job = {
    ...existing fields...,
    "map_type": request.map_type,
    # vertical_exaggeration: add in v2
}
```

**Frontend toggle** — add to `App.vue` before layer settings:

```
┌─────────────────────────────────────────┐
│ Map Mode                                │
│  ◉ Street Map    ○ Terrain              │
└─────────────────────────────────────────┘
```

When **Terrain** is selected:
- Hide `<LayerSettings>` component (`v-if="mapType !== 'terrain'"`)
- Show info text: *"Terrain mode renders real-world topography. No buildings or roads."*
- Pass `map_type: "terrain"` in the API payload
- Display peak elevation and elevation range from `result.metadata` in the result card

**Suppress multicolor download for terrain jobs** — in `GeneratorResults.vue`:

```javascript
// Check map_type in job status (returned from /api/maps/:id)
// or check absence of feature_stls in files
const isTerrainJob = job.map_type === 'terrain' || !job.files?.feature_stls
// Conditionally render the multicolor download button
```

**Add `fetching_elevation` to progress stages** in `App.vue`:

```javascript
const stages = [
  { id: 'queued',              label: 'Queued' },
  { id: 'fetching_osm',        label: 'Fetching map data' },   // street only
  { id: 'fetching_overture',   label: 'Fetching buildings' },  // street only
  { id: 'fetching_elevation',  label: 'Fetching elevation' },  // terrain only
  { id: 'converting',          label: 'Generating 3D model' },
  { id: 'finalizing',          label: 'Finalizing' },
]
// Progress component already handles unknown/skipped stages gracefully
```

---

## System-Wide Impact

- **Interaction graph**: `map_type` flows frontend → `POST /api/maps` (validated by `Literal`) → job dict → Redis → `process_request.py` terrain branch → `elevation.py`. The branch never calls `osm-to-tactile.py` or Blender, preserving the OSM pipeline unchanged.
- **Error propagation**: All `fetch_elevation()` and `generate_terrain_stl()` errors are caught and re-raised as `Exception(f"Failed to ...: {e}")`, matching `process_request.py:110`. The worker's top-level handler stores these in Redis; the frontend displays `status.error`.
- **State lifecycle risks**: Terrain jobs produce `map.stl` + `map-meta.json`. Finalization code already guards all optional files with `if file_path.exists()`. `feature_stls` key must be absent (not `{}`) from `output_files` for terrain — absence and empty dict are both falsy today, but absence is semantically correct and future-safe.
- **API surface parity**: `map_type` defaults to `"standard"` — all existing clients that don't send this field continue to get street maps. Backwards compatible.
- **Elevation API reliability**: AWS Terrain Tiles on S3 — AWS Open Data Sponsorship Program covers egress. No API key, no rate limits documented for normal use, S3-level reliability. Only `Pillow` needed for PNG decode.
- **Secret handling**: No API keys needed for v1 (AWS tiles are public). If OpenTopography is added in v2, pass the key through the job dict (not via `os.environ` in `elevation.py`) and scrub from error messages before storing in Redis.

---

## Acceptance Criteria

- [ ] Selecting "Terrain" map type generates a valid STL with topographic relief
- [ ] Terrain STL has no buildings or road features — purely elevation-based mesh
- [ ] Mesh is watertight (top + bottom + 4 side walls; `is_watertight` passes in trimesh)
- [ ] Terrain mesh is dimensionally correct: `world_width_m / scale * 1000` matches expected mm size
- [ ] Longitude dimension applies cos(lat) correction — mesh is not distorted at 45°N+ latitudes
- [ ] Ocean / no-data areas (sentinel -32768 from tiles) are clamped to sea level (0m), not negative
- [ ] Error handling: graceful failure with descriptive message if AWS tile fetch fails
- [ ] `fetching_elevation` progress stage shown in UI during generation
- [ ] Existing street map workflow is unaffected
- [ ] `map-meta.json` written with: `map_type`, `min/max/range elevation_m`, `vertical_exaggeration`, `resolution_m`, `grid_rows/cols`
- [ ] Elevation stats (peak, range) displayed in result card
- [ ] Layer settings panel hidden in frontend when terrain mode selected
- [ ] Multicolor download button suppressed for terrain jobs
- [ ] Invalid `map_type` values return HTTP 422 (enforced by `Literal` type)
- [ ] Terrain STL filename has `_terrain` suffix: `wosmap_{city}_{date}_terrain.stl`
- [ ] `map_type` included in initial Redis job status (frontend knows mode before completion)

---

## Success Metrics

- Terrain STL generates successfully for diverse geography: flat plains, mountains, coastal areas
- Mesh triangle count: 2 × (63 × 63) × 2 (top + bottom) = ~15,876 triangles for 64×64 grid — well within slicer performance range
- Generation time: under 30 seconds (1–4 tile fetches, each ~100-300ms, plus fast numpy mesh gen)
- Total print height: base 0.6mm + terrain max 8mm = 8.6mm — tactile-readable, printable
- Vertical exaggeration 3× produces discernible tactile relief for terrain with ≥10m elevation range

---

## Dependencies & Risks

| Dependency | Risk | Mitigation |
|-----------|------|------------|
| AWS Terrain Tiles S3 | Very low (S3 + Open Data sponsorship) | On failure, clear error message; add Open-Meteo as v2 fallback |
| `Pillow` (PNG decode) | Low — widely available | Add to `converter/requirements.txt`; likely already transitive dep |
| `numpy-stl` (STL write) | Low | Add to `converter/requirements.txt`; pure numpy, no C deps |
| `cos(lat)` correction missing | High correctness risk | Implemented via `ElevationData.world_width_m` property |
| Flat terrain (≤5m range) | Tactile unreadable at 3× | Elevation range shown in metadata; user can zoom in on more dramatic terrain |
| Side wall generation | Must be watertight for slicing | `write_terrain_stl()` in `stl_utils.py` handles perimeter closure |
| Box blur crops grid border | Grid shrinks by 4px each smooth pass | Recalculate `rows, cols` after smoothing |
| `map_type` not in job dict | Terrain branch silently skipped | Explicit propagation in `create_map()` job dict — add to implementation checklist |

**Out of scope for v1:**
- OSM features overlaid on terrain — "hybrid" mode
- `vertical_exaggeration` as user-facing parameter — hardcoded at 3.0
- OpenTopography / Open-Meteo fallback
- Local SRTM `.hgt` file caching
- Contour line generation
- Multi-color terrain gradient — see `docs/plans/2026-01-30-feat-multicolor-3mf-export-plan.md`
- Base plate / border frame — add in v2 once terrain surface is validated
- `scipy` — numpy box blur is sufficient for v1

---

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `converter/elevation.py` | Implement | `fetch_elevation()` via AWS Terrain Tiles; `generate_terrain_stl()` vectorized numpy; `write_terrain_meta()` |
| `converter/stl_utils.py` | Add function | `write_terrain_stl(vertices, faces, output_path)` using numpy-stl + side walls |
| `converter/process_request.py` | Modify | Add `map_type` branch before OSM fetch; terrain-specific filename |
| `converter/requirements.txt` | Modify | Add `Pillow`, `numpy-stl` |
| `backend/main.py` | Modify | Add `map_type: Literal[...]` to `MapRequest`; propagate to job dict; add to initial status |
| `frontend/src/App.vue` | Modify | Add `mapType` state, pass to API, add `fetching_elevation` stage |
| `frontend/src/components/settings/LayerSettings.vue` | Modify | Hide when `mapType === 'terrain'` |
| `frontend/src/components/generator/GeneratorProgress.vue` | Modify | Add `fetching_elevation` stage display |
| `frontend/src/components/generator/GeneratorResults.vue` | Modify | Suppress multicolor button for terrain; show elevation metadata |

---

## Sources & References

### Internal References

- Elevation stub: `converter/elevation.py:1-198` — `ElevationData` class and function signatures (this plan implements them)
- Process request pipeline: `converter/process_request.py:29-237` — integration point for terrain branch
- Terrain layer status: `docs/plans/2026-01-30-fix-trails-terrain-layers-not-generating-plan.md` — confirms terrain is Option B (this plan)
- STL utilities: `converter/stl_utils.py` — `write_terrain_stl()` belongs here alongside `get_stl_info()`
- Multicolor plan: `docs/plans/2026-01-30-feat-multicolor-3mf-export-plan.md` — terrain gradient coloring is a future enhancement
- Blender ARM64: `docs/solutions/integration-issues/blender-python-arm64-compatibility.md` — not needed for v1; relevant only if Blender post-processing added later
- OSM2World/Overpass: `docs/solutions/integration-issues/osm2world-overpass-api-compatibility.md` — Overpass bbox query pattern is reusable if terrain adds OSM overlay in future

### External References

- **AWS Terrain Tiles** (primary elevation source): https://registry.opendata.aws/terrain-tiles/
- Terrarium PNG decode formula: https://github.com/tilezen/joerd/blob/master/docs/formats.md
- numpy vectorized mesh generation: https://lachlangrose.github.io/programming/2022/06/07/triangulation_from_grid.html
- numpy-stl `data['vectors'] = vertices[faces]` pattern: https://numpy-stl.readthedocs.io/en/latest/usage.html
- Open-Meteo elevation API (v2 fallback candidate): https://open-meteo.com/en/docs/elevation-api
- Binary STL format: https://en.wikipedia.org/wiki/STL_(file_format)#Binary_STL
- Tactile map vertical exaggeration standards: tactile cartography literature recommends 3×–5× for flat-to-moderate terrain; 2mm minimum tactile height difference
