---
status: completed
priority: p2
issue_id: "012"
tags: [code-review, quality, converter, feature]
---

# Unimplemented osm_ms Data Source Feature

## Problem Statement

The API accepts `data_source: "osm_ms"` option but Microsoft building footprints integration is not implemented.

## Resolution

Replaced `osm_ms` with Overture Maps integration, which provides better building coverage by combining OSM, Microsoft, Google, and Esri data sources.

- Frontend now shows "Overture Maps (OSM + Microsoft + Google + Esri)"
- Backend accepts both `overture` and `osm_ms` for backwards compatibility
- Converter uses `overturemaps` CLI to download building footprints
- Buildings are merged into OSM XML data

## Acceptance Criteria

- [x] Feature implemented OR option removed from API
- [x] No false advertising in UI

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | P2 quality issue |
| 2026-01-25 | Implemented Overture Maps | Better than raw Microsoft - conflated sources |
