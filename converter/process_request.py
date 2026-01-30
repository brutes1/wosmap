"""
Process a map generation request.
Adapted from touch-mapper's process-request.py for local Docker execution.
"""

import os
import json
import subprocess
import math
from pathlib import Path
from typing import Optional

from osm_sources import get_map_data, calculate_bbox


def calculate_diameter_from_scale_and_size(scale: int, size_cm: float) -> int:
    """
    Calculate the map diameter in meters from scale and print size.

    For scale 1:3463 and size 23cm:
    - Print size = 230mm
    - Real world size = 230mm * 3463 = 796490mm = 796.5m
    """
    size_mm = size_cm * 10
    diameter_m = (size_mm * scale) / 1000
    return int(diameter_m)


def process_map_request(job: dict, work_dir: str = "/data/maps", status_callback=None) -> dict:
    """
    Process a map generation request.

    Args:
        job: Job dictionary with keys:
            - id: Unique job ID
            - latitude: Center latitude
            - longitude: Center longitude
            - scale: Map scale (default 3463)
            - size_cm: Print size in cm (default 23)
            - include_buildings: Whether to include buildings
            - data_source: "osm" or "overture"
        work_dir: Working directory for output files
        status_callback: Optional callback(stage, message) for progress updates

    Returns:
        Result dictionary with status and output file paths
    """
    def update_stage(stage: str, message: str = None):
        """Update processing stage via callback and print."""
        if status_callback:
            status_callback(stage, message)
        print(f"Stage: {stage}" + (f" - {message}" if message else ""))

    job_id = job["id"]
    lat = job["latitude"]
    lon = job["longitude"]
    scale = job.get("scale", 3463)
    size_cm = job.get("size_cm", 23.0)
    include_buildings = job.get("include_buildings", True)
    data_source = job.get("data_source", "osm")
    location_name = job.get("location_name", "map")
    layers = job.get("layers", {
        "buildings": True,
        "roads": True,
        "water": True,
        "rivers": False,
        "parks": False,
        "trails": False,
        "terrain": False,
    })

    # Create job directory
    job_dir = Path(work_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Calculate diameter from scale and size
    diameter = calculate_diameter_from_scale_and_size(scale, size_cm)

    # Calculate bounding box
    bbox = calculate_bbox(lat, lon, diameter)
    effective_area = {
        "latMin": bbox[0],
        "lonMin": bbox[1],
        "latMax": bbox[2],
        "lonMax": bbox[3],
    }

    print(f"Processing job {job_id}")
    print(f"  Location: {lat}, {lon}")
    print(f"  Scale: 1:{scale}, Size: {size_cm}cm, Diameter: {diameter}m")
    print(f"  Bounding box: {bbox}")
    print(f"  Layers: {layers}")

    # Step 1: Fetch OSM data
    update_stage("fetching_osm", "Fetching map data from OpenStreetMap...")
    osm_path = job_dir / "map.osm"
    try:
        # If using Overture, update stage before fetching
        if data_source in ("overture", "osm_ms"):
            osm_data = get_map_data(lat, lon, diameter, "osm", work_dir=str(job_dir), layers=layers)
            osm_path.write_text(osm_data)
            update_stage("fetching_overture", "Fetching building data from Overture Maps...")
            osm_data = get_map_data(lat, lon, diameter, data_source, work_dir=str(job_dir), layers=layers)
            osm_path.write_text(osm_data)
        else:
            osm_data = get_map_data(lat, lon, diameter, data_source, work_dir=str(job_dir), layers=layers)
            osm_path.write_text(osm_data)
        print(f"  Saved OSM data to {osm_path} ({len(osm_data)} bytes)")
    except Exception as e:
        raise Exception(f"Failed to fetch map data: {e}")

    # Step 2: Run osm-to-tactile.py (which calls OSM2World + Blender)
    update_stage("converting", "Converting to 3D model (OSM2World)...")
    converter_dir = Path(__file__).parent

    args = [
        "python3", str(converter_dir / "osm-to-tactile.py"),
        "--scale", str(scale),
        "--diameter", str(diameter),
        "--size", str(size_cm),
        str(osm_path)
    ]

    if not include_buildings:
        args.insert(-1, "--exclude-buildings")

    env = os.environ.copy()
    env["TOUCH_MAPPER_SCALE"] = str(scale)
    env["TOUCH_MAPPER_EXTRUDER_WIDTH"] = "0.5"
    env["TOUCH_MAPPER_EXCLUDE_BUILDINGS"] = "false" if include_buildings else "true"

    try:
        result = subprocess.run(
            args,
            cwd=str(converter_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            print(f"osm-to-tactile.py stderr: {result.stderr}")
            raise Exception(f"Conversion failed: {result.stderr[:500]}")

        print(result.stdout)
    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out after 10 minutes")

    # Step 3: Finalize and collect metadata
    update_stage("finalizing", "Computing file metadata...")

    stl_path = job_dir / "map.stl"
    if not stl_path.exists():
        raise Exception(f"STL file not generated at {stl_path}")

    # Collect output files
    output_files = {
        "stl": str(stl_path),
    }

    # Optional output files
    for ext in ["svg", "blend", "stl-ways", "stl-rest"]:
        file_path = job_dir / f"map.{ext.replace('-', '.')}"
        if file_path.exists():
            output_files[ext] = str(file_path)

    # Collect feature-specific STL files for multi-color 3MF
    feature_stls = {}
    for feature_type in ["buildings", "roads", "water", "parks", "rails", "base"]:
        feature_path = job_dir / f"map.{feature_type}.stl"
        if feature_path.exists():
            feature_stls[feature_type] = str(feature_path)
            output_files[f"stl_{feature_type}"] = str(feature_path)

    if feature_stls:
        output_files["feature_stls"] = feature_stls

    # Read metadata if available
    meta_path = job_dir / "map-meta.json"
    metadata = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text())

    # Get STL file info
    from stl_utils import get_stl_info
    from datetime import datetime

    stl_info = get_stl_info(str(stl_path))
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"wosmap_{location_name}_{date_str}.stl"

    return {
        "status": "completed",
        "job_id": job_id,
        "files": output_files,
        "file_info": {
            "filename": filename,
            **stl_info
        },
        "metadata": metadata,
        "effective_area": effective_area,
    }


if __name__ == "__main__":
    # Test mode
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--scale", type=int, default=3463)
    parser.add_argument("--size", type=float, default=23.0)
    parser.add_argument("--work-dir", default="./test_output")
    args = parser.parse_args()

    job = {
        "id": "test",
        "latitude": args.lat,
        "longitude": args.lon,
        "scale": args.scale,
        "size_cm": args.size,
        "include_buildings": True,
        "data_source": "osm",
    }

    result = process_map_request(job, args.work_dir)
    print(json.dumps(result, indent=2))
