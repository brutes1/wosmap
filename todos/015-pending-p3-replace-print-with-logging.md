---
status: pending
priority: p3
issue_id: "015"
tags: [code-review, quality, backend, converter, logging]
---

# Replace Print Statements with Proper Logging

## Problem Statement

Using `print()` instead of proper logging module throughout backend and converter. No log levels, harder to control in production.

## Findings

**Locations:**
- `converter/osm_sources.py:53,76,80,84,112,117`
- `backend/geocoding.py:54,94`
- `converter/worker.py` (various)

## Proposed Solutions

### Option A: Python Logging Module (Recommended)
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Fetching OSM data from {endpoint}...")
logger.error(f"Request failed: {e}")
```

- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] No print() for operational output
- [ ] Configurable log levels
- [ ] Structured logging format
