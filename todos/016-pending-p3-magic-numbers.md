---
status: pending
priority: p3
issue_id: "016"
tags: [code-review, quality, frontend, converter]
---

# Extract Magic Numbers to Named Constants

## Problem Statement

Hardcoded values like `111320` (meters per degree) repeated without explanation.

## Findings

**Locations:**
- `frontend/src/components/MapSelector.vue:225,230` - `111320`
- `converter/osm_sources.py:138-139` - `111320`
- Various timeout values

## Proposed Solutions

### Option A: Named Constants (Recommended)
```javascript
const METERS_PER_LAT_DEGREE = 111320  // 1 degree ≈ 111.32 km
```

```python
METERS_PER_DEGREE = 111320  # Earth circumference / 360
```

- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] All magic numbers have named constants
- [ ] Constants include explanatory comments
