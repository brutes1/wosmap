"""
Elevation data fetching and terrain mesh generation for tactile maps.

Uses AWS Terrain Tiles (Terrarium PNG format) — free, no API key required,
S3-hosted reliability. One tile fetch typically covers an entire map area.

Terrarium decode formula: elevation_meters = (R * 256 + G + B / 256) - 32768
"""

import json
import math
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from PIL import Image


# Earth's meridional degree length (mean value, accurate to <1% globally).
_METERS_PER_DEG_LAT: float = 111_320.0

# Hard physical ceiling for terrain height above base plate (mm).
# At 3× exaggeration: max output = base + 8mm = 8.6mm total — tactile-readable.
_MAX_TERRAIN_HEIGHT_MM: float = 8.0

# Default vertical exaggeration (v1: hardcoded; promotes flat terrain to tactile relief).
_VERTICAL_EXAGGERATION: float = 3.0

# Maximum bounding box extent in degrees — ~111km, far beyond any printable map.
_BBOX_MAX_DEGREES: float = 1.0

# AWS Terrain Tiles base URL (AWS Open Data Sponsorship Program — no auth required).
_TERRARIUM_BASE_URL: str = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium"

# Zoom level for tile fetching. Zoom 9 gives ~78km/tile at equator and
# ~30m effective resolution — sufficient for tactile map detail.
_TILE_ZOOM: int = 9

# Max grid size per axis (64×64 = 4,096 points, ~15,876 triangles — well within
# tactile finger resolution of ~2mm and slicer performance limits).
_MAX_GRID_SIZE: int = 64


class ElevationData:
    """Container for a 2D elevation grid covering a geographic bounding box."""

    def __init__(
        self,
        data: np.ndarray,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        resolution_m: float,
    ):
        self.data = data            # 2D float32 array (rows=lat, cols=lon), in meters
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
        """Longitude-to-meters conversion with cos(lat) correction."""
        return _METERS_PER_DEG_LAT * math.cos(math.radians(self.mid_lat))

    @property
    def world_width_m(self) -> float:
        """Real-world width of the bbox in meters (with cos(lat) correction)."""
        return (self.max_lon - self.min_lon) * self.meters_per_deg_lon

    @property
    def world_height_m(self) -> float:
        """Real-world height of the bbox in meters."""
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


# ---------------------------------------------------------------------------
# Tile helpers
# ---------------------------------------------------------------------------

def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon (WGS84) to XYZ slippy-map tile coordinates."""
    n = 2 ** zoom
    tile_x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    tile_y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
    )
    return tile_x, tile_y


def _tile_pixel(lat: float, lon: float, zoom: int, tile_x: int, tile_y: int) -> tuple[int, int]:
    """Return (px, py) pixel offset within a 256×256 tile for a given lat/lon."""
    n = 2 ** zoom
    px = int(((lon + 180.0) / 360.0 * n * 256) % 256)
    lat_rad = math.radians(lat)
    py = int(
        (
            (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
            * 256
        )
        % 256
    )
    return min(px, 255), min(py, 255)


def _decode_terrarium_pixel(r: int, g: int, b: int) -> float:
    """Decode RGB pixel from Terrarium format to elevation in meters."""
    return (r * 256.0 + g + b / 256.0) - 32768.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_elevation(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    resolution_m: float = 30.0,
    api_key: Optional[str] = None,  # reserved for future sources; unused
) -> ElevationData:
    """
    Fetch elevation grid from AWS Terrain Tiles (Terrarium PNG format).

    Tiles are fetched and cached in memory — a typical map area requires only
    1–4 tile fetches regardless of grid resolution. No authentication required.

    Args:
        min_lat: Southern boundary (degrees, WGS84)
        min_lon: Western boundary (degrees, WGS84)
        max_lat: Northern boundary (degrees, WGS84)
        max_lon: Eastern boundary (degrees, WGS84)
        resolution_m: Desired point spacing in meters (default 30m)
        api_key: Reserved; unused in AWS tile approach

    Returns:
        ElevationData with 2D float32 elevation grid

    Raises:
        ValueError: Invalid bounding box or physically implausible values
        RuntimeError: Tile fetch network failure
    """
    if (max_lat - min_lat) > _BBOX_MAX_DEGREES or (max_lon - min_lon) > _BBOX_MAX_DEGREES:
        raise ValueError(
            f"Bounding box too large: {max_lat - min_lat:.3f}° lat × "
            f"{max_lon - min_lon:.3f}° lon. Maximum is {_BBOX_MAX_DEGREES}°."
        )

    # Grid dimensions with cos(lat) correction for longitude
    mid_lat = (min_lat + max_lat) / 2.0
    meters_per_deg_lon = _METERS_PER_DEG_LAT * math.cos(math.radians(mid_lat))
    n_lat = min(max(10, int((max_lat - min_lat) * _METERS_PER_DEG_LAT / resolution_m)), _MAX_GRID_SIZE)
    n_lon = min(max(10, int((max_lon - min_lon) * meters_per_deg_lon / resolution_m)), _MAX_GRID_SIZE)

    lats = np.linspace(min_lat, max_lat, n_lat)
    lons = np.linspace(min_lon, max_lon, n_lon)

    # In-memory tile cache: (tile_x, tile_y) → PIL Image
    tile_cache: dict[tuple[int, int], Image.Image] = {}

    def get_tile(tx: int, ty: int) -> Image.Image:
        key = (tx, ty)
        if key not in tile_cache:
            url = f"{_TERRARIUM_BASE_URL}/{_TILE_ZOOM}/{tx}/{ty}.png"
            try:
                resp = requests.get(url, timeout=15, allow_redirects=False)
                resp.raise_for_status()
            except requests.exceptions.Timeout:
                raise RuntimeError(
                    f"Elevation tile fetch timed out: {_TILE_ZOOM}/{tx}/{ty}"
                )
            except requests.exceptions.RequestException as exc:
                raise RuntimeError(
                    f"Failed to fetch elevation tile {_TILE_ZOOM}/{tx}/{ty}: {exc}"
                ) from exc
            tile_cache[key] = Image.open(BytesIO(resp.content)).convert("RGB")
        return tile_cache[key]

    # Build elevation grid — nearby points share tiles (cache hit)
    elevations = np.zeros((n_lat, n_lon), dtype=np.float32)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            tx, ty = _lat_lon_to_tile(lat, lon, _TILE_ZOOM)
            tile = get_tile(tx, ty)
            px, py = _tile_pixel(lat, lon, _TILE_ZOOM, tx, ty)
            r, g, b = tile.getpixel((px, py))
            elev = _decode_terrarium_pixel(r, g, b)
            # Sentinel: ocean / no-data returns -32768; clamp to sea level (0m)
            elevations[i, j] = max(elev, 0.0)

    # Validate physical plausibility (Everest = 8849m; Dead Sea = -430m clamped to 0)
    if not np.isfinite(elevations).all():
        raise ValueError("Elevation data contains non-finite values")
    if elevations.max() > 9000:
        raise ValueError(
            f"Elevation out of physical range: max={elevations.max():.1f}m "
            f"(expected ≤9000m)"
        )

    return ElevationData(
        data=elevations,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        resolution_m=resolution_m,
    )


def _smooth_grid(grid: np.ndarray, passes: int = 2) -> np.ndarray:
    """
    Apply a 5-point box blur for terrain smoothing.

    Uses only numpy — no scipy dependency. Each pass crops 1 pixel from each
    border. Caller must recalculate grid shape after smoothing.
    """
    g = grid.astype(np.float64)
    for _ in range(passes):
        g = (
            g[:-2, 1:-1]   # north
            + g[2:, 1:-1]  # south
            + g[1:-1, :-2] # west
            + g[1:-1, 2:]  # east
            + g[1:-1, 1:-1] # center
        ) / 5.0
    return g.astype(np.float32)


def generate_terrain_stl(
    elevation_data: ElevationData,
    output_path: Path,
    scale: int,
    vertical_exaggeration: float = _VERTICAL_EXAGGERATION,
    base_height_mm: float = 0.6,
    smoothing: bool = True,
) -> Path:
    """
    Generate a watertight terrain STL mesh from elevation data.

    Uses fully vectorized numpy mesh generation — no Python triangle loops.
    Top surface + flat bottom + 4 side walls = closed solid for 3D printing.

    Args:
        elevation_data: ElevationData from fetch_elevation()
        output_path: Destination STL file path
        scale: Map scale denominator (e.g., 3463 for 1:3463)
        vertical_exaggeration: Relief amplification (default 3.0)
        base_height_mm: Flat base plate thickness in mm
        smoothing: Apply numpy box blur to reduce SRTM noise

    Returns:
        Path to the generated STL file
    """
    from stl_utils import write_terrain_stl  # local import to avoid circular

    elev = elevation_data.data.copy().astype(np.float64)

    if smoothing:
        elev = _smooth_grid(elev)
        # smoothing crops border pixels; update shape
    rows, cols = elev.shape

    # Normalize [0, 1] → apply exaggeration → clamp → scale to mm
    # Clamp ensures exaggeration never exceeds _MAX_TERRAIN_HEIGHT_MM ceiling.
    e_min, e_max = float(elev.min()), float(elev.max())
    e_range = e_max - e_min if e_max > e_min else 1.0
    elev_norm = (elev - e_min) / e_range                          # [0.0, 1.0]
    elev_exag = np.clip(elev_norm * vertical_exaggeration, 0.0, 1.0)  # still [0, 1]
    z = base_height_mm + elev_exag * _MAX_TERRAIN_HEIGHT_MM       # mm above plate

    # Physical print dimensions using ElevationData helpers (cos(lat) corrected)
    print_width_mm = elevation_data.world_width_m / scale * 1000.0
    print_height_mm = elevation_data.world_height_m / scale * 1000.0

    # Coordinate arrays for the grid
    xs = np.linspace(0.0, print_width_mm, cols)
    ys = np.linspace(0.0, print_height_mm, rows)
    xx, yy = np.meshgrid(xs, ys, indexing='xy')  # both (rows, cols)

    # Top surface vertices: shape (rows*cols, 3) — float32 for STL
    verts_top = np.column_stack([xx.ravel(), yy.ravel(), z.ravel()]).astype(np.float32)

    # Bottom surface: flat at z=0
    verts_bot = np.column_stack([
        xx.ravel(),
        yy.ravel(),
        np.zeros(rows * cols, dtype=np.float32),
    ])
    n_top = len(verts_top)
    vertices = np.vstack([verts_top, verts_bot])  # (2*rows*cols, 3)

    # ---------------------------------------------------------------------------
    # Face index generation — fully vectorized (no per-triangle Python loop)
    # ---------------------------------------------------------------------------
    ci = np.arange(cols - 1)
    cj = np.arange(rows - 1)
    cii, cjj = np.meshgrid(ci, cj, indexing='ij')         # (cols-1, rows-1)
    corners = np.array([[0, 1, 0, 1], [0, 0, 1, 1]])
    idx_i = cii[:, :, None] + corners[None, None, 0, :]   # col offsets
    idx_j = cjj[:, :, None] + corners[None, None, 1, :]   # row offsets
    gi = (idx_i + idx_j * cols).reshape(-1, 4)             # (cells, 4) corner indices

    # Top surface: CCW winding → upward-facing normals
    top_f1 = gi[:, [0, 1, 3]]
    top_f2 = gi[:, [0, 3, 2]]
    # Bottom surface: CW winding → downward-facing normals
    bot_f1 = gi[:, [0, 3, 1]] + n_top
    bot_f2 = gi[:, [0, 2, 3]] + n_top

    # Side walls: close the 4 perimeter edges (each edge quad → 2 triangles)
    side_faces = _build_side_walls(rows, cols, n_top)

    faces = np.vstack([top_f1, top_f2, bot_f1, bot_f2, side_faces]).astype(np.int64)

    write_terrain_stl(vertices, faces, output_path)
    return output_path


def _build_side_walls(rows: int, cols: int, n_top: int) -> np.ndarray:
    """
    Generate face indices for the 4 perimeter side walls.

    Connects top-surface perimeter vertices to their matching bottom-surface
    counterparts. Winding order produces outward-facing normals.

    Returns:
        Face index array shape (n_side_tris, 3)
    """
    faces = []

    def quad(a: int, b: int) -> None:
        """Add two triangles for a vertical quad between top[a,b] and bottom[a,b]."""
        ta, tb = a, b           # top indices
        ba, bb = a + n_top, b + n_top  # bottom indices (offset)
        faces.append([ta, bb, ba])
        faces.append([ta, tb, bb])

    # South edge (row 0): left→right
    for c in range(cols - 1):
        a = c          # row 0, col c
        b = c + 1      # row 0, col c+1
        quad(a, b)

    # North edge (row rows-1): right→left (outward normal faces north)
    for c in range(cols - 1, 0, -1):
        a = (rows - 1) * cols + c      # row rows-1, col c
        b = (rows - 1) * cols + c - 1  # row rows-1, col c-1
        quad(a, b)

    # West edge (col 0): bottom→top rows
    for r in range(rows - 1, 0, -1):
        a = r * cols        # row r, col 0
        b = (r - 1) * cols  # row r-1, col 0
        quad(a, b)

    # East edge (col cols-1): top→bottom rows
    for r in range(rows - 1):
        a = r * cols + (cols - 1)        # row r, col cols-1
        b = (r + 1) * cols + (cols - 1) # row r+1, col cols-1
        quad(a, b)

    return np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)


def write_terrain_meta(
    elevation_data: ElevationData,
    job_dir: Path,
    vertical_exaggeration: float = _VERTICAL_EXAGGERATION,
) -> None:
    """
    Write map-meta.json with terrain-specific metadata.

    The existing finalization code in process_request.py reads this file
    automatically — no changes to the return schema needed.
    """
    meta = {
        "map_type": "terrain",
        "min_elevation_m": round(elevation_data.min_elevation, 1),
        "max_elevation_m": round(elevation_data.max_elevation, 1),
        "elevation_range_m": round(elevation_data.elevation_range, 1),
        "vertical_exaggeration": vertical_exaggeration,
        "resolution_m": elevation_data.resolution_m,
        "grid_rows": int(elevation_data.data.shape[0]),
        "grid_cols": int(elevation_data.data.shape[1]),
    }
    (job_dir / "map-meta.json").write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Stub retained for future OSM2World SRTM integration (not used in v1)
# ---------------------------------------------------------------------------
def configure_osm2world_srtm(srtm_dir: str) -> dict:
    """Configure OSM2World to use local SRTM .hgt files for elevation."""
    raise NotImplementedError(
        "OSM2World SRTM configuration is not yet implemented."
    )
