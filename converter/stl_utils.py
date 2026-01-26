"""
STL file utilities for extracting metadata.
"""

import struct
from pathlib import Path


def get_stl_info(stl_path: str) -> dict:
    """
    Parse STL file and extract metadata.
    Handles binary STL format (most common from Blender).

    Args:
        stl_path: Path to STL file

    Returns:
        Dictionary with file metadata
    """
    path = Path(stl_path)
    size_bytes = path.stat().st_size

    # Check if ASCII or binary STL
    with open(stl_path, 'rb') as f:
        header = f.read(80)
        # ASCII STL starts with "solid" but binary can too, so check further
        is_ascii = header.startswith(b'solid') and b'\x00' not in header

    if is_ascii:
        return _parse_ascii_stl(stl_path, size_bytes)
    else:
        return _parse_binary_stl(stl_path, size_bytes)


def _parse_binary_stl(stl_path: str, size_bytes: int) -> dict:
    """Parse binary STL format."""
    with open(stl_path, 'rb') as f:
        # Skip 80-byte header
        f.read(80)

        # Read triangle count (4 bytes, little-endian unsigned int)
        triangle_count = struct.unpack('<I', f.read(4))[0]

        # Initialize bounding box
        min_coords = [float('inf')] * 3
        max_coords = [float('-inf')] * 3

        # Each triangle: 12 bytes normal + 36 bytes vertices + 2 bytes attribute
        for _ in range(triangle_count):
            f.read(12)  # Skip normal vector

            # Read 3 vertices (each is 3 floats = 12 bytes)
            for _ in range(3):
                x, y, z = struct.unpack('<fff', f.read(12))
                coords = [x, y, z]
                for i in range(3):
                    min_coords[i] = min(min_coords[i], coords[i])
                    max_coords[i] = max(max_coords[i], coords[i])

            f.read(2)  # Skip attribute byte count

    return _build_result(size_bytes, triangle_count, min_coords, max_coords)


def _parse_ascii_stl(stl_path: str, size_bytes: int) -> dict:
    """Parse ASCII STL format."""
    triangle_count = 0
    min_coords = [float('inf')] * 3
    max_coords = [float('-inf')] * 3

    with open(stl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('facet'):
                triangle_count += 1
            elif line.startswith('vertex'):
                parts = line.split()
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    coords = [x, y, z]
                    for i in range(3):
                        min_coords[i] = min(min_coords[i], coords[i])
                        max_coords[i] = max(max_coords[i], coords[i])

    return _build_result(size_bytes, triangle_count, min_coords, max_coords)


def _build_result(size_bytes: int, triangle_count: int, min_coords: list, max_coords: list) -> dict:
    """Build the result dictionary from parsed data."""
    # Handle empty files
    if triangle_count == 0 or min_coords[0] == float('inf'):
        return {
            "size_bytes": size_bytes,
            "size_human": format_bytes(size_bytes),
            "triangles": 0,
            "vertices": 0,
            "dimensions": {"x_mm": 0, "y_mm": 0, "z_mm": 0},
            "bounding_box": {"min": [0, 0, 0], "max": [0, 0, 0]}
        }

    dimensions = [max_coords[i] - min_coords[i] for i in range(3)]

    return {
        "size_bytes": size_bytes,
        "size_human": format_bytes(size_bytes),
        "triangles": triangle_count,
        "vertices": triangle_count * 3,
        "dimensions": {
            "x_mm": round(dimensions[0], 1),
            "y_mm": round(dimensions[1], 1),
            "z_mm": round(dimensions[2], 1),
        },
        "bounding_box": {
            "min": [round(v, 2) for v in min_coords],
            "max": [round(v, 2) for v in max_coords],
        }
    }


def format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
