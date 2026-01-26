---
status: pending
priority: p2
issue_id: "011"
tags: [code-review, quality, backend, error-handling]
---

# Missing Error Recovery in Geocoding

## Problem Statement

Network errors in geocoding are caught but only printed - no retry logic, no fallback, no structured logging.

## Findings

**Location:** `backend/geocoding.py:54-56`

```python
except httpx.RequestError as e:
    print(f"Geocoding request failed: {e}")  # Silent failure!
return None
```

## Proposed Solutions

### Option A: Add Retry Logic (Recommended)
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def geocode_address(address: str) -> Optional[dict]:
    ...
```
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Transient failures retried automatically
- [ ] Errors logged properly (not just printed)
