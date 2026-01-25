"""
Geocoding service using Nominatim (OpenStreetMap's geocoder).
"""

import re
import httpx
from typing import Optional


NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "WOSMap/1.0"


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
                NOMINATIM_SEARCH_URL,
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
            NOMINATIM_SEARCH_URL,
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


def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    # Lowercase and replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Get location name from coordinates using reverse geocoding.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Location name (city/town/village) or None if not found
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # City-level detail
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                NOMINATIM_REVERSE_URL,
                params=params,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                address = result.get("address", {})

                # Try to get the most specific locality name
                location = (
                    address.get("city") or
                    address.get("town") or
                    address.get("village") or
                    address.get("municipality") or
                    address.get("county") or
                    address.get("state")
                )

                if location:
                    return slugify(location)

        except httpx.RequestError as e:
            print(f"Reverse geocoding request failed: {e}")

    return None


def reverse_geocode_sync(lat: float, lon: float) -> Optional[str]:
    """
    Synchronous version of reverse_geocode.
    """
    import requests

    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params=params,
            headers=headers,
            timeout=10.0
        )

        if response.status_code == 200:
            result = response.json()
            address = result.get("address", {})

            location = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("municipality") or
                address.get("county") or
                address.get("state")
            )

            if location:
                return slugify(location)

    except Exception as e:
        print(f"Reverse geocoding request failed: {e}")

    return None
