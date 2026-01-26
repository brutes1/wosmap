---
status: pending
priority: p3
issue_id: "017"
tags: [code-review, security, backend, performance]
---

# Add Rate Limiting to API

## Problem Statement

No rate limiting on job submissions. Could overwhelm workers, Redis, or external APIs (Nominatim, Overpass).

## Findings

All endpoints accept unlimited requests per IP.

## Proposed Solutions

### Option A: slowapi (Recommended for FastAPI)
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/maps")
@limiter.limit("10/minute")
async def create_map(request: Request, ...):
    ...
```

- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Job submission rate limited per IP
- [ ] Returns 429 with Retry-After header when exceeded
