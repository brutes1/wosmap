---
title: "Nominatim Reverse Geocoding for User-Friendly Filenames"
category: feature-implementation
tags:
  - nominatim
  - geocoding
  - openstreetmap
  - python
  - fastapi
components:
  - backend/geocoding.py
  - backend/main.py
date: 2026-01-24
---

# Nominatim Reverse Geocoding for User-Friendly Filenames

## Problem

Generated files with UUID-based names like `tactile_map_e046e701-2666-4368.stl` are not user-friendly. When users look at their downloads folder, they can't tell which file corresponds to which location without opening it.

## Solution

Use Nominatim's reverse geocoding API to get the city/town name from coordinates, then generate filenames like `wosmap_paris_2026-01-24.stl`.

### Implementation

#### 1. Reverse Geocoding Function

```python
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Get location name from coordinates."""
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # City-level detail
    }

    headers = {"User-Agent": "WOSMap/1.0"}

    async with httpx.AsyncClient() as client:
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

    return None
```

#### 2. Slugify Helper

```python
def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')
```

#### 3. Store in Job Metadata

```python
# During job creation
location_name = await reverse_geocode(lat, lon)
if location_name is None:
    location_name = f"{lat:.3f}_{lon:.3f}"  # Fallback

job = {
    "id": job_id,
    "location_name": location_name,
    # ... other fields
}
```

#### 4. Generate Filename on Download

```python
# In download endpoint
location_name = data.get("location_name", "map")
date_str = data.get("created_at", "").split("T")[0]
filename = f"wosmap_{location_name}_{date_str}.{file_type}"
```

## Output Examples

| Coordinates | Location Name | Filename |
|-------------|---------------|----------|
| 48.8584, 2.2945 | paris | wosmap_paris_2026-01-24.stl |
| 37.7749, -122.4194 | san-francisco | wosmap_san-francisco_2026-01-24.stl |
| 35.6762, 139.6503 | tokyo | wosmap_tokyo_2026-01-24.stl |
| 0.0, 0.0 | 0.000_0.000 | wosmap_0.000_0.000_2026-01-24.stl |

## Nominatim Usage Notes

- **User-Agent required**: Nominatim requires a valid User-Agent header
- **Rate limiting**: 1 request/second for free tier
- **Zoom levels**: 10 = city, 14 = suburb, 18 = building
- **Caching**: Store location_name in job metadata to avoid repeat lookups

## Key Files

- `backend/geocoding.py` - Geocoding functions
- `backend/main.py` - Job creation and download endpoints

## Related

- [Nominatim Reverse API](https://nominatim.org/release-docs/develop/api/Reverse/)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
