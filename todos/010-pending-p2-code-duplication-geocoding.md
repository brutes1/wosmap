---
status: pending
priority: p2
issue_id: "010"
tags: [code-review, quality, backend]
---

# Significant Code Duplication in Geocoding Module

## Problem Statement

83 lines of code duplicated between async and sync versions of geocoding functions.

## Findings

**Location:** `backend/geocoding.py`

- Lines 15-57: `geocode_address()` (async)
- Lines 60-97: `geocode_address_sync()` (nearly identical)
- Lines 110-161: `reverse_geocode()` (async)
- Lines 164-208: `reverse_geocode_sync()` (nearly identical)

## Proposed Solutions

### Option A: Sync Wrapper (Recommended)
```python
def geocode_address_sync(address: str) -> Optional[dict]:
    import asyncio
    return asyncio.run(geocode_address(address))
```
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] No duplicated geocoding logic
- [ ] Both sync and async interfaces available
