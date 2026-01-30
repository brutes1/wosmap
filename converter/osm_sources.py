"""
Map data sources for tactile map generation.
Fetches geographic data from OpenStreetMap and optionally Overture Maps.
"""

import json
import os
import re
import subprocess
import requests
import time
from typing import Optional
from xml.etree import ElementTree as ET


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Default layer configuration
DEFAULT_LAYERS = {
    "buildings": True,
    "roads": True,
    "water": True,
    "rivers": False,
    "parks": False,
    "trails": False,
    "terrain": False,
}


def build_overpass_query(bbox: tuple, layers: dict, timeout: int = 180) -> str:
    """
    Build Overpass query based on selected layers.

    Args:
        bbox: Tuple of (lat_min, lon_min, lat_max, lon_max)
        layers: Dictionary of layer_id -> enabled (bool)
        timeout: Query timeout in seconds

    Returns:
        Overpass QL query string
    """
    lat_min, lon_min, lat_max, lon_max = bbox

    queries = []

    if layers.get("buildings", True):
        queries.extend([
            'way["building"]',
            'relation["building"]',
        ])

    if layers.get("roads", True):
        queries.extend([
            'way["highway"]',
            'way["railway"]',
        ])

    if layers.get("water", True):
        queries.extend([
            'way["natural"="water"]',
            'relation["natural"="water"]',
            'way["landuse"="grass"]',
        ])

    if layers.get("rivers", False):
        queries.extend([
            'way["waterway"~"river|stream|canal|ditch"]',
            'relation["waterway"]',
        ])

    if layers.get("parks", False):
        queries.extend([
            'way["leisure"="park"]',
            'way["landuse"="forest"]',
            'way["landuse"="recreation_ground"]',
            'way["boundary"="protected_area"]',
            'relation["leisure"="park"]',
            'relation["landuse"="forest"]',
        ])

    if layers.get("trails", False):
        queries.extend([
            'way["highway"="path"]',
            'way["highway"="footway"]',
            'way["highway"="track"]',
            'way["highway"="bridleway"]',
            'way["highway"="cycleway"]',
        ])

    # If no layers selected, at least get basic features
    if not queries:
        queries = ['way["highway"]']

    query_str = ";\n      ".join(queries)

    return f"""
    [out:xml][timeout:{timeout}][bbox:{lat_min},{lon_min},{lat_max},{lon_max}];
    (
      {query_str};
    );
    out meta;
    >;
    out meta qt;
    """


def fetch_osm_data(bbox: tuple, timeout: int = 180, layers: dict = None) -> str:
    """
    Fetch OSM data via Overpass API.

    Args:
        bbox: Tuple of (lat_min, lon_min, lat_max, lon_max)
        timeout: Request timeout in seconds
        layers: Dictionary of layer_id -> enabled (bool)

    Returns:
        OSM XML data as string
    """
    lat_min, lon_min, lat_max, lon_max = bbox

    # Use provided layers or defaults
    if layers is None:
        layers = DEFAULT_LAYERS

    # Build query based on selected layers
    query = build_overpass_query(bbox, layers, timeout)

    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"Fetching OSM data from {endpoint}...")
            response = requests.post(
                endpoint,
                data={"data": query},
                timeout=timeout + 30,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                osm_data = response.text
                # Add bounds element right after <osm> tag (OSM2World requires it before entities)
                if "<bounds" not in osm_data:
                    bounds = f'  <bounds minlat="{lat_min}" minlon="{lon_min}" maxlat="{lat_max}" maxlon="{lon_max}"/>\n'
                    # Insert bounds after the opening <osm ...> tag
                    import re
                    osm_data = re.sub(
                        r'(<osm[^>]*>)\s*',
                        r'\1\n' + bounds,
                        osm_data,
                        count=1
                    )
                return osm_data
            elif response.status_code == 429:
                print(f"Rate limited by {endpoint}, trying next...")
                time.sleep(2)
                continue
            else:
                print(f"Error from {endpoint}: {response.status_code}")
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"

        except requests.RequestException as e:
            print(f"Request failed for {endpoint}: {e}")
            last_error = str(e)
            continue

    raise Exception(f"All Overpass endpoints failed. Last error: {last_error}")


def fetch_osm_xapi(bbox: tuple, timeout: int = 120) -> str:
    """
    Fallback: Fetch OSM data via XAPI-style endpoint.

    Args:
        bbox: Tuple of (lat_min, lon_min, lat_max, lon_max)
        timeout: Request timeout in seconds

    Returns:
        OSM XML data as string
    """
    lat_min, lon_min, lat_max, lon_max = bbox
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"

    urls = [
        f"https://www.overpass-api.de/api/xapi?map?bbox={bbox_str}",
        f"https://api.openstreetmap.org/api/0.6/map?bbox={bbox_str}",
    ]

    for url in urls:
        try:
            print(f"Fetching OSM data from {url}...")
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.text
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            continue

    raise Exception("All XAPI endpoints failed")


def calculate_bbox(lat: float, lon: float, diameter_meters: int) -> tuple:
    """
    Calculate bounding box from center point and diameter.

    Args:
        lat: Center latitude
        lon: Center longitude
        diameter_meters: Diameter of the area in meters

    Returns:
        Tuple of (lat_min, lon_min, lat_max, lon_max)
    """
    import math

    # Approximate meters per degree
    meters_per_lat_degree = 111320
    meters_per_lon_degree = 111320 * math.cos(math.radians(lat))

    radius_meters = diameter_meters / 2

    lat_offset = radius_meters / meters_per_lat_degree
    lon_offset = radius_meters / meters_per_lon_degree

    return (
        lat - lat_offset,
        lon - lon_offset,
        lat + lat_offset,
        lon + lon_offset
    )


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

    print(f"Fetching Overture buildings: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"Overture download failed: {result.stderr}")

    if not os.path.exists(output_path):
        raise Exception("Overture download produced no output file")

    return output_path


def merge_overture_with_osm(osm_xml: str, overture_geojson_path: str) -> str:
    """
    Merge Overture building footprints into OSM XML data.

    Overture buildings supplement OSM data - we add Overture buildings
    that provide additional coverage beyond what OSM has.

    OSM XML format requires: bounds, then nodes, then ways, then relations.
    We insert Overture nodes among existing nodes, and Overture ways among existing ways.
    We also expand the bounds element to include all Overture buildings.
    """
    # Parse OSM XML
    root = ET.fromstring(osm_xml)

    # Load Overture GeoJSON
    with open(overture_geojson_path) as f:
        overture = json.load(f)

    # Find insertion points: after last node, after last way
    # OSM format: bounds -> nodes -> ways -> relations
    last_node_idx = 0
    last_way_idx = 0
    bounds_elem = None
    for i, child in enumerate(root):
        if child.tag == "bounds":
            bounds_elem = child
        elif child.tag == "node":
            last_node_idx = i + 1
        elif child.tag == "way":
            last_way_idx = i + 1

    # If no ways found, insert ways after nodes
    if last_way_idx == 0:
        last_way_idx = last_node_idx

    # Generate synthetic OSM IDs (negative to avoid conflicts with real OSM IDs)
    way_id = -1000000
    node_id = -1000000

    # Track min/max coordinates for bounds update
    all_lats = []
    all_lons = []

    # Collect all new nodes and ways first
    new_nodes = []
    new_ways = []

    buildings_added = 0
    for feature in overture.get("features", []):
        geom_type = feature.get("geometry", {}).get("type")

        if geom_type == "Polygon":
            coords = feature["geometry"]["coordinates"][0]
        elif geom_type == "MultiPolygon":
            # Take the first polygon from multipolygon
            coords = feature["geometry"]["coordinates"][0][0]
        else:
            continue

        # Create nodes for the building polygon
        node_refs = []
        for lon, lat in coords:
            node = ET.Element("node", {
                "id": str(node_id),
                "lat": str(lat),
                "lon": str(lon),
                "version": "1"
            })
            new_nodes.append(node)
            node_refs.append(str(node_id))
            node_id -= 1
            all_lats.append(lat)
            all_lons.append(lon)

        # Create way for the building
        way = ET.Element("way", {
            "id": str(way_id),
            "version": "1"
        })
        for ref in node_refs:
            ET.SubElement(way, "nd", {"ref": ref})
        ET.SubElement(way, "tag", {"k": "building", "v": "yes"})
        ET.SubElement(way, "tag", {"k": "source", "v": "Overture Maps"})

        # Add height if available
        props = feature.get("properties", {})
        height = props.get("height")
        if height:
            ET.SubElement(way, "tag", {"k": "height", "v": str(height)})

        new_ways.append(way)
        way_id -= 1
        buildings_added += 1

    # Update bounds to include Overture buildings
    if bounds_elem is not None and all_lats:
        cur_minlat = float(bounds_elem.get("minlat", 90))
        cur_maxlat = float(bounds_elem.get("maxlat", -90))
        cur_minlon = float(bounds_elem.get("minlon", 180))
        cur_maxlon = float(bounds_elem.get("maxlon", -180))

        new_minlat = min(cur_minlat, min(all_lats))
        new_maxlat = max(cur_maxlat, max(all_lats))
        new_minlon = min(cur_minlon, min(all_lons))
        new_maxlon = max(cur_maxlon, max(all_lons))

        bounds_elem.set("minlat", str(new_minlat))
        bounds_elem.set("maxlat", str(new_maxlat))
        bounds_elem.set("minlon", str(new_minlon))
        bounds_elem.set("maxlon", str(new_maxlon))

    # Insert new nodes after existing nodes (before ways)
    for i, node in enumerate(new_nodes):
        root.insert(last_node_idx + i, node)

    # Insert new ways after existing ways (accounting for the nodes we just added)
    way_insert_idx = last_way_idx + len(new_nodes)
    for i, way in enumerate(new_ways):
        root.insert(way_insert_idx + i, way)

    print(f"Added {buildings_added} buildings from Overture Maps")
    return ET.tostring(root, encoding="unicode")


def get_map_data(
    lat: float,
    lon: float,
    diameter_meters: int,
    data_source: str = "osm",
    work_dir: str = "/tmp",
    timeout: int = 180,
    layers: dict = None
) -> str:
    """
    Get map data for a location.

    Args:
        lat: Center latitude
        lon: Center longitude
        diameter_meters: Diameter of area in meters
        data_source: "osm" or "overture" (with Overture Maps buildings)
        work_dir: Working directory for temporary files
        timeout: Request timeout
        layers: Dictionary of layer_id -> enabled (bool)

    Returns:
        OSM XML data
    """
    bbox = calculate_bbox(lat, lon, diameter_meters)

    # Use provided layers or defaults
    if layers is None:
        layers = DEFAULT_LAYERS

    try:
        osm_data = fetch_osm_data(bbox, timeout, layers)
    except Exception as e:
        print(f"Overpass API failed: {e}, trying XAPI...")
        osm_data = fetch_osm_xapi(bbox, timeout)

    # If Overture source requested, merge additional buildings
    # Accept both "overture" and legacy "osm_ms" for backwards compatibility
    if data_source in ("overture", "osm_ms"):
        try:
            overture_path = fetch_overture_buildings(bbox, work_dir)
            osm_data = merge_overture_with_osm(osm_data, overture_path)
            # Clean up temp file
            if os.path.exists(overture_path):
                os.remove(overture_path)
        except Exception as e:
            print(f"Overture fetch failed, using OSM only: {e}")

    return osm_data
