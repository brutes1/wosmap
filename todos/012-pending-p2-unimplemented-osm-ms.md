---
status: pending
priority: p2
issue_id: "012"
tags: [code-review, quality, converter, feature]
---

# Unimplemented osm_ms Data Source Feature

## Problem Statement

The API accepts `data_source: "osm_ms"` option but Microsoft building footprints integration is not implemented.

## Findings

**Location:** `converter/osm_sources.py:182-183`

```python
# TODO: Implement Microsoft building footprints
# For now, just return OSM data
```

## Proposed Solutions

### Option A: Implement Feature
- Integrate Microsoft Building Footprints API
- **Effort:** Large
- **Risk:** Medium

### Option B: Remove Option (Recommended for MVP)
- Remove `osm_ms` from API options
- Document as future enhancement
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Feature implemented OR option removed from API
- [ ] No false advertising in UI
