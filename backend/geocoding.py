"""
Geocoding service using Nominatim (OpenStreetMap's geocoder).
"""

import httpx
from typing import Optional


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TactileMapGenerator/1.0"


async def geocode_address(address: str) -> Optional[dict]:
    """
    Convert an address to latitude/longitude coordinates.

    Args:
        address: Human-readable address string

    Returns:
        Dictionary with 'lat', 'lon', and 'display_name' or None if not found
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                if results:
                    result = results[0]
                    return {
                        "lat": float(result["lat"]),
                        "lon": float(result["lon"]),
                        "display_name": result.get("display_name", address),
                    }

        except httpx.RequestError as e:
            print(f"Geocoding request failed: {e}")

    return None


def geocode_address_sync(address: str) -> Optional[dict]:
    """
    Synchronous version of geocode_address.
    """
    import requests

    params = {
        "q": address,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=10.0
        )

        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "display_name": result.get("display_name", address),
                }

    except Exception as e:
        print(f"Geocoding request failed: {e}")

    return None
