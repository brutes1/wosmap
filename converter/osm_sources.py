"""
Map data sources for tactile map generation.
Fetches geographic data from OpenStreetMap and optionally Microsoft Building Footprints.
"""

import requests
import time
from typing import Optional


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def fetch_osm_data(bbox: tuple, timeout: int = 180) -> str:
    """
    Fetch OSM data via Overpass API.

    Args:
        bbox: Tuple of (lat_min, lon_min, lat_max, lon_max)
        timeout: Request timeout in seconds

    Returns:
        OSM XML data as string
    """
    lat_min, lon_min, lat_max, lon_max = bbox

    # Overpass uses (south, west, north, east) = (lat_min, lon_min, lat_max, lon_max)
    query = f"""
    [out:xml][timeout:{timeout}];
    (
      way["building"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["highway"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["railway"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["waterway"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["natural"="water"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["landuse"="grass"]({lat_min},{lon_min},{lat_max},{lon_max});
      relation["building"]({lat_min},{lon_min},{lat_max},{lon_max});
      relation["natural"="water"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out body;
    >;
    out skel qt;
    """

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
                # Add bounds element if not present (needed by OSM2World)
                if "<bounds" not in osm_data:
                    bounds = f'  <bounds minlat="{lat_min}" minlon="{lon_min}" maxlat="{lat_max}" maxlon="{lon_max}"/>\n'
                    osm_data = osm_data.replace("</osm>", bounds + "</osm>")
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


def get_map_data(
    lat: float,
    lon: float,
    diameter_meters: int,
    data_source: str = "osm",
    timeout: int = 180
) -> str:
    """
    Get map data for a location.

    Args:
        lat: Center latitude
        lon: Center longitude
        diameter_meters: Diameter of area in meters
        data_source: "osm" or "osm_ms" (with Microsoft buildings)
        timeout: Request timeout

    Returns:
        OSM XML data
    """
    bbox = calculate_bbox(lat, lon, diameter_meters)

    try:
        osm_data = fetch_osm_data(bbox, timeout)
    except Exception as e:
        print(f"Overpass API failed: {e}, trying XAPI...")
        osm_data = fetch_osm_xapi(bbox, timeout)

    # TODO: If data_source == "osm_ms", merge Microsoft building footprints
    # This would require downloading quadkey-indexed files from Microsoft's dataset

    return osm_data
